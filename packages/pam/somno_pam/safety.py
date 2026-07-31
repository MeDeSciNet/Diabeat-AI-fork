"""Safety envelope (PRD 9.3, PAM-S1 to PAM-S8).

Every limit is checked here, before a command reaches a driver, and every
rejection is a named reason so the audit log records *why* the system declined
to move a bed. Nothing in the controller bypasses this module except
``emergency_flat``, which is explicitly the one command that outranks the
comfort limits.
"""

from __future__ import annotations

from dataclasses import dataclass

from .driver import MattressState


class SafetyViolation(Exception):
    def __init__(self, rule: str, message: str) -> None:
        super().__init__(f"{rule}: {message}")
        self.rule = rule
        self.message = message


@dataclass(frozen=True)
class SafetyLimits:
    # PAM-S1
    hob_min_deg: float = 0.0
    hob_max_deg: float = 45.0
    lateral_max_deg: float = 30.0
    # PAM-S2 - slow enough not to wake or startle the occupant
    max_rate_deg_per_s: float = 2.0
    # PAM-S4
    notify_seconds: float = 30.0
    # PAM-S6
    min_motion_interval_s: float = 20 * 60


def check_hob(deg: float, rate: float, limits: SafetyLimits) -> None:
    if not (limits.hob_min_deg <= deg <= limits.hob_max_deg):
        raise SafetyViolation(
            "PAM-S1",
            f"head-of-bed angle {deg} outside {limits.hob_min_deg}-{limits.hob_max_deg} degrees",
        )
    if rate <= 0 or rate > limits.max_rate_deg_per_s:
        raise SafetyViolation(
            "PAM-S2", f"rate {rate} deg/s exceeds the {limits.max_rate_deg_per_s} deg/s limit"
        )


def check_lateral(side: str, deg: float, limits: SafetyLimits) -> None:
    if side not in ("left", "right", "flat"):
        raise SafetyViolation("PAM-S1", f"unknown lateral side {side!r}")
    if not (0.0 <= deg <= limits.lateral_max_deg):
        raise SafetyViolation(
            "PAM-S1", f"lateral tilt {deg} outside 0-{limits.lateral_max_deg} degrees"
        )


def check_occupancy(occupied: bool) -> None:
    if not occupied:
        raise SafetyViolation("PAM-S3", "bed is unoccupied; refusing to move")


def check_link(state: MattressState) -> None:
    if not state.link_ok:
        raise SafetyViolation(
            "PAM-S8", "link to the analysis service is down; holding position in the safe state"
        )


def check_interval(seconds_since_last: float | None, limits: SafetyLimits) -> None:
    if seconds_since_last is None:
        return
    if seconds_since_last < limits.min_motion_interval_s:
        wait = int(limits.min_motion_interval_s - seconds_since_last)
        raise SafetyViolation(
            "PAM-S6",
            f"only {int(seconds_since_last)} s since the last motion; {wait} s remaining before "
            "another is allowed",
        )
