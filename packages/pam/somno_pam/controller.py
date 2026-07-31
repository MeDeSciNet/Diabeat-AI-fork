"""Mattress controller: modes, command lifecycle, audit (PRD 9.2).

Three modes ship in v1. ``autonomous`` is absent by construction, not by
omission: PRD 2.1 R2 forbids closed-loop actuation, so there is no code path
anywhere in this package that turns a detection into a motion without a human
pressing something. ``advisory_confirm`` is the closest the system gets - it
*proposes* and then waits.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Literal

from .driver import MattressDriver, MattressState
from .safety import SafetyLimits, SafetyViolation, check_hob, check_interval, check_lateral, check_link, check_occupancy

Mode = Literal["manual", "scheduled", "advisory_confirm"]
CommandSource = Literal["manual", "scheduled", "advisory", "safety"]

TURN_CYCLE: tuple[str, ...] = ("left", "flat", "right")


@dataclass
class Command:
    id: str
    bed_id: str
    type: str
    source: CommandSource
    params: dict[str, Any]
    actor_id: str | None
    status: str = "pending"
    reject_reason: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "bed_id": self.bed_id,
            "type": self.type,
            "source": self.source,
            "status": self.status,
            "actor_id": self.actor_id,
            "params": self.params,
            "reject_reason": self.reject_reason,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class Advisory:
    """A proposal awaiting human confirmation. Expires rather than lingering."""

    id: str
    bed_id: str
    action: str
    params: dict[str, Any]
    reason: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "pending"


@dataclass
class TurnSchedule:
    enabled: bool = False
    interval_min: int = 120
    cycle: list[str] = field(default_factory=lambda: list(TURN_CYCLE))
    _index: int = 0
    _last_fire: float | None = None


class MattressController:
    def __init__(
        self,
        bed_id: str,
        driver: MattressDriver,
        limits: SafetyLimits | None = None,
        audit: Callable[[str, str, dict, str | None], Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Any] | None = None,
    ) -> None:
        self.bed_id = bed_id
        self.driver = driver
        self.limits = limits or SafetyLimits()
        self.mode: Mode = "manual"
        self.schedule = TurnSchedule()
        self.commands: list[Command] = []
        self.advisories: list[Advisory] = []
        self._audit = audit or (lambda actor, action, detail, bed: None)
        self._clock = clock
        self._sleep = sleep or asyncio.sleep
        self._last_motion_at: float | None = None
        self._pending_notify: dict[str, asyncio.Event] = {}
        self.link_ok = True

    # ------------------------------------------------------------------ api
    async def state(self) -> dict:
        s: MattressState = await self.driver.get_state()
        s.link_ok = s.link_ok and self.link_ok
        pending = next((c for c in self.commands if c.status in ("pending", "notifying")), None)
        return {
            "bed_id": self.bed_id,
            "hob_angle_deg": s.hob_angle_deg,
            "lateral_side": s.lateral_side,
            "lateral_deg": s.lateral_deg,
            "occupied": s.occupied,
            "mode": self.mode,
            "moving": s.moving,
            "link_ok": s.link_ok,
            "pending_command_id": pending.id if pending else None,
            "last_motion_at": (
                datetime.now(UTC).isoformat() if self._last_motion_at is not None else None
            ),
            "schedule": {
                "enabled": self.schedule.enabled,
                "interval_min": self.schedule.interval_min,
                "cycle": self.schedule.cycle,
                "next_at": None,
            },
            "seconds_since_last_motion": (
                None
                if self._last_motion_at is None
                else round(self._clock() - self._last_motion_at, 1)
            ),
        }

    def set_mode(self, mode: Mode, actor_id: str) -> None:
        if mode not in ("manual", "scheduled", "advisory_confirm"):
            raise ValueError(
                f"unsupported mode {mode!r}. 'autonomous' is not implemented: PRD 2.1 R2 "
                "requires human confirmation before any motion."
            )
        self.mode = mode
        self.schedule.enabled = mode == "scheduled"
        self._audit(actor_id, "pam.set_mode", {"mode": mode}, self.bed_id)

    def set_schedule(self, enabled: bool, interval_min: int, actor_id: str) -> dict:
        floor = int(self.limits.min_motion_interval_s // 60)
        if interval_min < floor:
            raise SafetyViolation(
                "PAM-S6", f"turn interval must be at least {floor} minutes"
            )
        self.schedule.enabled = enabled
        self.schedule.interval_min = interval_min
        self._audit(
            actor_id,
            "pam.set_schedule",
            {"enabled": enabled, "interval_min": interval_min},
            self.bed_id,
        )
        return {"enabled": enabled, "interval_min": interval_min, "cycle": self.schedule.cycle}

    # -------------------------------------------------------------- commands
    async def submit(
        self,
        type_: str,
        params: dict[str, Any],
        actor_id: str,
        source: CommandSource = "manual",
    ) -> Command:
        cmd = Command(
            id=str(uuid.uuid4()),
            bed_id=self.bed_id,
            type=type_,
            source=source,
            params=dict(params),
            actor_id=actor_id,
        )
        self.commands.append(cmd)

        if type_ == "emergency_flat":
            return await self._run_emergency(cmd)

        try:
            await self._preflight(type_, params)
        except SafetyViolation as exc:
            return self._reject(cmd, exc)

        # PAM-S4: warn, then wait, then move. The wait is cancellable.
        cmd.status = "notifying"
        event = asyncio.Event()
        self._pending_notify[cmd.id] = event
        self._audit(
            actor_id,
            "pam.notify",
            {"command_id": cmd.id, "type": type_, "params": params,
             "notify_seconds": self.limits.notify_seconds},
            self.bed_id,
        )
        try:
            await asyncio.wait_for(event.wait(), timeout=self.limits.notify_seconds)
            cmd.status = "cancelled"
            cmd.completed_at = datetime.now(UTC)
            self._audit(actor_id, "pam.cancel", {"command_id": cmd.id}, self.bed_id)
            return cmd
        except (TimeoutError, asyncio.TimeoutError):
            pass
        finally:
            self._pending_notify.pop(cmd.id, None)

        # Re-check occupancy: the 30 s warning is long enough for a bed to empty.
        try:
            await self._preflight(type_, params)
        except SafetyViolation as exc:
            return self._reject(cmd, exc)

        cmd.status = "running"
        if type_ == "set_hob_angle":
            result = await self.driver.set_hob_angle(
                float(params["deg"]),
                float(params.get("rate_deg_per_s", self.limits.max_rate_deg_per_s)),
            )
        elif type_ == "set_lateral_tilt":
            result = await self.driver.set_lateral_tilt(
                params["side"], float(params.get("deg", 20.0))
            )
        else:
            return self._reject(cmd, SafetyViolation("PAM-S1", f"unknown command {type_!r}"))

        cmd.status = "completed" if result.ok else "failed"
        cmd.reject_reason = None if result.ok else result.detail
        cmd.completed_at = datetime.now(UTC)
        if result.ok:
            self._last_motion_at = self._clock()
        self._audit(
            actor_id,
            "pam.command",
            {
                "command_id": cmd.id,
                "type": type_,
                "params": params,
                "source": source,
                "status": cmd.status,
                "detail": result.detail,
            },
            self.bed_id,
        )
        return cmd

    def cancel(self, command_id: str, actor_id: str) -> bool:
        event = self._pending_notify.get(command_id)
        if event is None:
            return False
        event.set()
        return True

    async def _run_emergency(self, cmd: Command) -> Command:
        """PAM-S5: outranks everything, including the notify delay and the interval."""
        cmd.status = "running"
        result = await self.driver.emergency_flat()
        cmd.status = "completed" if result.ok else "failed"
        cmd.completed_at = datetime.now(UTC)
        self._last_motion_at = self._clock()
        for event in list(self._pending_notify.values()):
            event.set()
        self._audit(
            cmd.actor_id or "system",
            "pam.emergency_flat",
            {"command_id": cmd.id, "status": cmd.status},
            self.bed_id,
        )
        return cmd

    async def _preflight(self, type_: str, params: dict) -> None:
        state = await self.driver.get_state()
        state.link_ok = state.link_ok and self.link_ok
        check_link(state)
        check_occupancy(await self.driver.get_occupancy())
        since = None if self._last_motion_at is None else self._clock() - self._last_motion_at
        check_interval(since, self.limits)
        if type_ == "set_hob_angle":
            check_hob(
                float(params["deg"]),
                float(params.get("rate_deg_per_s", self.limits.max_rate_deg_per_s)),
                self.limits,
            )
        elif type_ == "set_lateral_tilt":
            check_lateral(params["side"], float(params.get("deg", 20.0)), self.limits)

    def _reject(self, cmd: Command, exc: SafetyViolation) -> Command:
        cmd.status = "rejected"
        cmd.reject_reason = str(exc)
        cmd.completed_at = datetime.now(UTC)
        self._audit(
            cmd.actor_id or "system",
            "pam.reject",
            {
                "command_id": cmd.id,
                "type": cmd.type,
                "params": cmd.params,
                "rule": exc.rule,
                "reason": exc.message,
            },
            self.bed_id,
        )
        return cmd

    # ------------------------------------------------------------- advisory
    def propose(self, action: str, params: dict, reason: str) -> Advisory:
        """Record a suggestion. Does not move anything - that needs confirm()."""
        adv = Advisory(
            id=str(uuid.uuid4()),
            bed_id=self.bed_id,
            action=action,
            params=dict(params),
            reason=reason,
        )
        self.advisories.append(adv)
        self._audit("system", "pam.advisory_proposed", {"advisory_id": adv.id, "action": action}, self.bed_id)
        return adv

    async def confirm(self, advisory_id: str, actor_id: str) -> Command:
        adv = next((a for a in self.advisories if a.id == advisory_id), None)
        if adv is None:
            raise LookupError("unknown advisory")
        if adv.status != "pending":
            raise ValueError(f"advisory already {adv.status}")
        adv.status = "confirmed"
        self._audit(actor_id, "pam.advisory_confirmed", {"advisory_id": adv.id}, self.bed_id)
        return await self.submit(adv.action, adv.params, actor_id, source="advisory")

    def decline(self, advisory_id: str, actor_id: str) -> None:
        adv = next((a for a in self.advisories if a.id == advisory_id), None)
        if adv is None:
            raise LookupError("unknown advisory")
        adv.status = "declined"
        self._audit(actor_id, "pam.advisory_declined", {"advisory_id": adv.id}, self.bed_id)

    # ------------------------------------------------------------ scheduled
    async def tick(self) -> Command | None:
        """Advance the turning schedule. Called by the scheduler loop."""
        if self.mode != "scheduled" or not self.schedule.enabled or not self.link_ok:
            return None
        now = self._clock()
        due = (
            self.schedule._last_fire is None
            or now - self.schedule._last_fire >= self.schedule.interval_min * 60
        )
        if not due:
            return None
        self.schedule._last_fire = now
        side = self.schedule.cycle[self.schedule._index % len(self.schedule.cycle)]
        self.schedule._index += 1
        return await self.submit(
            "set_lateral_tilt", {"side": side, "deg": 20.0}, "scheduler", source="scheduled"
        )

    def set_link(self, ok: bool) -> None:
        """PAM-S8: losing the link holds position and stops the schedule."""
        if ok != self.link_ok:
            self._audit("system", "pam.link", {"link_ok": ok}, self.bed_id)
        self.link_ok = ok
