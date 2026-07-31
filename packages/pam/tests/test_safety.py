"""One test per safety requirement in PRD 9.3, plus the mode restrictions."""

from __future__ import annotations

import asyncio

import pytest

from somno_pam.controller import MattressController
from somno_pam.driver import MockMattressDriver
from somno_pam.safety import (
    SafetyLimits,
    SafetyViolation,
    check_hob,
    check_interval,
    check_lateral,
    check_occupancy,
)


def make(step_s: float = 0.05, time_scale: float = 0.0, **limit_overrides):
    """Fast limits and a scaled mock clock.

    The safety logic under test is identical; only the waiting is compressed.
    ``time_scale`` scales how long a simulated ramp step takes in real time, so
    a 10-second head-of-bed movement does not cost 10 seconds of test runtime.
    """
    limits = SafetyLimits(
        notify_seconds=0.05,
        min_motion_interval_s=limit_overrides.pop("min_motion_interval_s", 0.0),
        **limit_overrides,
    )
    audit: list[tuple] = []
    driver = MockMattressDriver(bed_id="BED-T", step_s=step_s, time_scale=time_scale)
    controller = MattressController(
        bed_id="BED-T",
        driver=driver,
        limits=limits,
        audit=lambda actor, action, detail, bed: audit.append((actor, action, detail, bed)),
    )
    return controller, driver, audit


# ------------------------------------------------------------------ PAM-S1
async def test_s1_hob_angle_is_bounded():
    controller, _, audit = make()
    for bad in (-1.0, 46.0, 90.0):
        cmd = await controller.submit("set_hob_angle", {"deg": bad}, "nurse-1")
        assert cmd.status == "rejected"
        assert "PAM-S1" in cmd.reject_reason
    assert any(a[1] == "pam.reject" for a in audit)


async def test_s1_lateral_tilt_is_bounded():
    controller, _, _ = make()
    cmd = await controller.submit("set_lateral_tilt", {"side": "left", "deg": 31.0}, "nurse-1")
    assert cmd.status == "rejected" and "PAM-S1" in cmd.reject_reason


def test_s1_limits_match_the_prd():
    limits = SafetyLimits()
    assert (limits.hob_min_deg, limits.hob_max_deg) == (0.0, 45.0)
    assert limits.lateral_max_deg == 30.0
    check_hob(45.0, 2.0, limits)
    check_lateral("right", 30.0, limits)
    with pytest.raises(SafetyViolation):
        check_hob(45.1, 2.0, limits)


# ------------------------------------------------------------------ PAM-S2
async def test_s2_rate_is_capped_at_2_deg_per_second():
    controller, _, _ = make()
    cmd = await controller.submit(
        "set_hob_angle", {"deg": 30.0, "rate_deg_per_s": 5.0}, "nurse-1"
    )
    assert cmd.status == "rejected" and "PAM-S2" in cmd.reject_reason


async def test_s2_default_rate_is_within_the_limit():
    controller, driver, _ = make()
    cmd = await controller.submit("set_hob_angle", {"deg": 30.0}, "nurse-1")
    assert cmd.status == "completed"
    assert (await driver.get_state()).hob_angle_deg == pytest.approx(30.0, abs=0.01)


# ------------------------------------------------------------------ PAM-S3
async def test_s3_unoccupied_bed_refuses_every_motion():
    controller, driver, audit = make()
    driver.set_occupancy(False)
    for type_, params in (
        ("set_hob_angle", {"deg": 30.0}),
        ("set_lateral_tilt", {"side": "left", "deg": 20.0}),
    ):
        cmd = await controller.submit(type_, params, "nurse-1")
        assert cmd.status == "rejected"
        assert "PAM-S3" in cmd.reject_reason
    # The refusal itself is auditable (PRD 12: rejection must be recorded).
    rejects = [a for a in audit if a[1] == "pam.reject"]
    assert len(rejects) == 2
    assert all(r[2]["rule"] == "PAM-S3" for r in rejects)
    assert (await driver.get_state()).hob_angle_deg == 0.0


async def test_s3_bed_emptied_during_the_warning_still_refuses():
    """Occupancy is re-checked after the 30 s notice, not only before it."""
    controller, driver, _ = make()
    controller.limits = SafetyLimits(notify_seconds=0.1, min_motion_interval_s=0.0)

    async def empty_the_bed():
        await asyncio.sleep(0.02)
        driver.set_occupancy(False)

    task = asyncio.ensure_future(empty_the_bed())
    cmd = await controller.submit("set_hob_angle", {"deg": 30.0}, "nurse-1")
    await task
    assert cmd.status == "rejected" and "PAM-S3" in cmd.reject_reason


def test_s3_check_is_explicit():
    check_occupancy(True)
    with pytest.raises(SafetyViolation) as exc:
        check_occupancy(False)
    assert exc.value.rule == "PAM-S3"


# ------------------------------------------------------------------ PAM-S4
async def test_s4_motion_is_announced_before_it_starts():
    controller, _, audit = make()
    await controller.submit("set_hob_angle", {"deg": 20.0}, "nurse-1")
    notify = [a for a in audit if a[1] == "pam.notify"]
    assert notify, "no pre-motion notification recorded"
    assert notify[0][2]["notify_seconds"] == controller.limits.notify_seconds


async def test_s4_the_warning_can_be_cancelled():
    controller, driver, _ = make()
    controller.limits = SafetyLimits(notify_seconds=5.0, min_motion_interval_s=0.0)

    async def cancel_soon():
        await asyncio.sleep(0.02)
        pending = controller.commands[-1]
        assert controller.cancel(pending.id, "nurse-1")

    task = asyncio.ensure_future(cancel_soon())
    cmd = await controller.submit("set_hob_angle", {"deg": 30.0}, "nurse-1")
    await task
    assert cmd.status == "cancelled"
    assert (await driver.get_state()).hob_angle_deg == 0.0


def test_s4_default_notice_is_30_seconds():
    assert SafetyLimits().notify_seconds == 30.0


# ------------------------------------------------------------------ PAM-S5
async def test_s5_emergency_flat_ignores_the_interval_limit():
    controller, driver, _ = make(min_motion_interval_s=3600.0)
    driver.state.hob_angle_deg = 40.0
    driver.state.lateral_deg = 25.0
    cmd = await controller.submit("emergency_flat", {}, "nurse-1")
    assert cmd.status == "completed"
    state = await driver.get_state()
    assert state.hob_angle_deg == 0.0 and state.lateral_deg == 0.0


async def test_s5_emergency_flat_interrupts_a_motion_in_progress():
    # Real-time stepping here: the point is to interrupt something in flight.
    controller, driver, _ = make(step_s=0.02, time_scale=1.0)
    slow = asyncio.ensure_future(
        controller.submit("set_hob_angle", {"deg": 45.0, "rate_deg_per_s": 0.5}, "nurse-1")
    )
    await asyncio.sleep(0.15)
    emergency = await controller.submit("emergency_flat", {}, "nurse-1")
    await slow
    assert emergency.status == "completed"
    assert (await driver.get_state()).hob_angle_deg == 0.0


async def test_s5_emergency_flat_releases_a_pending_warning():
    controller, _, _ = make()
    controller.limits = SafetyLimits(notify_seconds=5.0, min_motion_interval_s=0.0)
    pending = asyncio.ensure_future(controller.submit("set_hob_angle", {"deg": 30.0}, "nurse-1"))
    await asyncio.sleep(0.02)
    await controller.submit("emergency_flat", {}, "nurse-1")
    cmd = await pending
    assert cmd.status == "cancelled"


# ------------------------------------------------------------------ PAM-S6
async def test_s6_motions_are_spaced_by_at_least_20_minutes():
    controller, _, _ = make(min_motion_interval_s=20 * 60)
    first = await controller.submit("set_hob_angle", {"deg": 20.0}, "nurse-1")
    assert first.status == "completed"
    second = await controller.submit("set_hob_angle", {"deg": 30.0}, "nurse-1")
    assert second.status == "rejected" and "PAM-S6" in second.reject_reason


def test_s6_default_interval_is_20_minutes():
    assert SafetyLimits().min_motion_interval_s == 20 * 60
    check_interval(None, SafetyLimits())
    check_interval(1200.0, SafetyLimits())
    with pytest.raises(SafetyViolation):
        check_interval(60.0, SafetyLimits())


async def test_s6_schedule_cannot_be_set_below_the_interval():
    controller, _, _ = make(min_motion_interval_s=20 * 60)
    with pytest.raises(SafetyViolation):
        controller.set_schedule(True, 5, "nurse-1")
    assert controller.set_schedule(True, 120, "nurse-1")["interval_min"] == 120


# ------------------------------------------------------------------ PAM-S7
async def test_s7_every_command_is_audited():
    controller, _, audit = make()
    await controller.submit("set_hob_angle", {"deg": 20.0}, "nurse-7")
    entries = [a for a in audit if a[1] == "pam.command"]
    assert len(entries) == 1
    actor, _, detail, bed = entries[0]
    assert actor == "nurse-7" and bed == "BED-T"
    assert detail["type"] == "set_hob_angle" and detail["params"] == {"deg": 20.0}
    assert detail["source"] == "manual" and detail["status"] == "completed"


def test_s7_audit_chain_detects_tampering(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/audit.db")
    from somno_ing import audit as audit_mod
    from somno_ing.db import AuditLogRow, db_session, init_db, reset_engine

    reset_engine()
    init_db()
    audit_mod.record("nurse-1", "pam.command", {"deg": 20})
    audit_mod.record("nurse-1", "pam.command", {"deg": 30})
    assert audit_mod.verify_chain() == (True, None)

    with db_session() as db:
        row = db.get(AuditLogRow, 1)
        row.detail = {"deg": 45}
    intact, bad = audit_mod.verify_chain()
    assert not intact and bad == 1
    reset_engine()


# ------------------------------------------------------------------ PAM-S8
async def test_s8_link_loss_holds_position():
    controller, driver, _ = make()
    controller.set_link(False)
    cmd = await controller.submit("set_hob_angle", {"deg": 30.0}, "nurse-1")
    assert cmd.status == "rejected" and "PAM-S8" in cmd.reject_reason
    assert (await driver.get_state()).hob_angle_deg == 0.0


async def test_s8_link_loss_stops_the_schedule():
    controller, _, _ = make()
    controller.set_mode("scheduled", "nurse-1")
    controller.set_schedule(True, 120, "nurse-1")
    controller.set_link(False)
    assert await controller.tick() is None


async def test_s8_state_reports_the_link():
    controller, _, _ = make()
    controller.set_link(False)
    assert (await controller.state())["link_ok"] is False


# ---------------------------------------------------------------- PRD 2.1 R2
def test_autonomous_mode_does_not_exist():
    controller, _, _ = make()
    with pytest.raises(ValueError) as exc:
        controller.set_mode("autonomous", "nurse-1")  # type: ignore[arg-type]
    assert "R2" in str(exc.value)


async def test_advisory_only_moves_after_confirmation():
    controller, driver, audit = make()
    controller.set_mode("advisory_confirm", "nurse-1")
    adv = controller.propose(
        "set_hob_angle", {"deg": 30.0}, "supine for most of the recording"
    )
    # Proposing must not move anything.
    assert (await driver.get_state()).hob_angle_deg == 0.0
    assert not [a for a in audit if a[1] == "pam.command"]

    cmd = await controller.confirm(adv.id, "nurse-9")
    assert cmd.status == "completed" and cmd.source == "advisory"
    assert (await driver.get_state()).hob_angle_deg == pytest.approx(30.0, abs=0.01)
    assert [a for a in audit if a[1] == "pam.advisory_confirmed"]


async def test_declined_advisory_cannot_be_confirmed():
    controller, _, _ = make()
    adv = controller.propose("set_hob_angle", {"deg": 30.0}, "reason")
    controller.decline(adv.id, "nurse-1")
    with pytest.raises(ValueError):
        await controller.confirm(adv.id, "nurse-1")


async def test_scheduled_mode_cycles_through_positions():
    controller, _, _ = make()
    controller.set_mode("scheduled", "nurse-1")
    controller.set_schedule(True, 120, "nurse-1")
    sides = []
    for _ in range(3):
        controller.schedule._last_fire = None
        cmd = await controller.tick()
        assert cmd is not None
        sides.append(cmd.params["side"])
    assert sides == ["left", "flat", "right"]


async def test_manual_mode_does_not_fire_the_schedule():
    controller, _, _ = make()
    controller.set_mode("manual", "nurse-1")
    assert await controller.tick() is None
