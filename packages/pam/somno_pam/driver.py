"""Hardware abstraction (PRD 9.1).

``MattressDriver`` is the whole hardware surface. v1 ships only
``MockMattressDriver``; a BLE or Modbus driver implements the same five calls and
nothing above this layer changes.

The mock is not a stub - it models motion as taking real time at a real rate,
because most of the safety requirements (rate limits, interrupting a motion in
progress, refusing to move an empty bed) are meaningless against an instant
actuator.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

LateralSide = Literal["left", "right", "flat"]


@dataclass
class MattressState:
    bed_id: str
    hob_angle_deg: float = 0.0
    lateral_side: LateralSide = "flat"
    lateral_deg: float = 0.0
    occupied: bool = True
    moving: bool = False
    link_ok: bool = True


@dataclass
class CommandResult:
    ok: bool
    detail: str = ""
    final_state: MattressState | None = None


@runtime_checkable
class MattressDriver(Protocol):
    async def get_state(self) -> MattressState: ...
    async def set_hob_angle(self, deg: float, rate_deg_per_s: float) -> CommandResult: ...
    async def set_lateral_tilt(self, side: LateralSide, deg: float) -> CommandResult: ...
    async def emergency_flat(self) -> CommandResult: ...
    async def get_occupancy(self) -> bool: ...


@dataclass
class MockMattressDriver:
    """Software mattress. Ramps at the requested rate and can be interrupted."""

    bed_id: str = "BED-01"
    state: MattressState = field(default=None)  # type: ignore[assignment]
    step_s: float = 0.05
    time_scale: float = 1.0
    _task: asyncio.Task | None = field(default=None, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def __post_init__(self) -> None:
        if self.state is None:
            self.state = MattressState(bed_id=self.bed_id)

    async def get_state(self) -> MattressState:
        return MattressState(**vars(self.state))

    async def get_occupancy(self) -> bool:
        return self.state.occupied

    async def set_hob_angle(self, deg: float, rate_deg_per_s: float) -> CommandResult:
        return await self._ramp("hob", deg, rate_deg_per_s)

    async def set_lateral_tilt(self, side: LateralSide, deg: float) -> CommandResult:
        target = 0.0 if side == "flat" else deg
        self.state.lateral_side = side if target > 0 else "flat"
        return await self._ramp("lateral", target, 2.0)

    async def emergency_flat(self) -> CommandResult:
        """Highest priority. Cancels anything in progress (PAM-S5)."""
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        # Emergency flat runs at a higher rate than the comfort limit on purpose.
        await self._ramp("hob", 0.0, 6.0, emergency=True)
        self.state.lateral_side = "flat"
        await self._ramp("lateral", 0.0, 6.0, emergency=True)
        return CommandResult(True, "flat", await self.get_state())

    async def _ramp(
        self, axis: str, target: float, rate: float, emergency: bool = False
    ) -> CommandResult:
        if not emergency and self._task is not None and not self._task.done():
            return CommandResult(False, "another motion is already running")

        async def _run() -> None:
            self.state.moving = True
            try:
                while True:
                    current = (
                        self.state.hob_angle_deg if axis == "hob" else self.state.lateral_deg
                    )
                    delta = target - current
                    if abs(delta) < 1e-6:
                        break
                    step = min(abs(delta), rate * self.step_s) * (1 if delta > 0 else -1)
                    value = round(current + step, 4)
                    if axis == "hob":
                        self.state.hob_angle_deg = value
                    else:
                        self.state.lateral_deg = value
                    await asyncio.sleep(self.step_s * self.time_scale)
            finally:
                self.state.moving = False

        task = asyncio.ensure_future(_run())
        if not emergency:
            self._task = task
        try:
            await task
        except asyncio.CancelledError:
            return CommandResult(False, "motion cancelled")
        return CommandResult(True, f"{axis}={target}", await self.get_state())

    # ------------------------------------------------------------ test hooks
    def set_occupancy(self, occupied: bool) -> None:
        self.state.occupied = occupied

    def set_link(self, ok: bool) -> None:
        self.state.link_ok = ok
