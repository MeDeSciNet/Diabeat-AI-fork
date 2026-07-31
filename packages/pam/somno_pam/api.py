"""PAM HTTP API (PRD 9.4)."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .controller import MattressController
from .driver import MockMattressDriver
from .safety import SafetyLimits, SafetyViolation

log = logging.getLogger(__name__)

RUO_NOTICE = (
    "Research use only. Positioning support only; this system never delivers "
    "electrical stimulation and never moves a bed without human confirmation."
)

_controllers: dict[str, MattressController] = {}
_scheduler_task: asyncio.Task | None = None


def _audit(actor_id: str, action: str, detail: dict, bed_id: str | None) -> None:
    """Write to the shared append-only audit log (PAM-S7)."""
    try:
        from somno_ing.audit import record

        record(actor_id, action, detail, bed_id=bed_id)
    except Exception:  # pragma: no cover - audit must never block a safety path
        log.exception("audit write failed for %s/%s", bed_id, action)


def get_controller(bed_id: str) -> MattressController:
    if bed_id not in _controllers:
        limits = SafetyLimits(
            notify_seconds=float(os.getenv("PAM_NOTIFY_SECONDS", "30")),
            min_motion_interval_s=float(os.getenv("PAM_MIN_INTERVAL_S", str(20 * 60))),
        )
        _controllers[bed_id] = MattressController(
            bed_id=bed_id,
            driver=MockMattressDriver(bed_id=bed_id),
            limits=limits,
            audit=_audit,
        )
    return _controllers[bed_id]


class CommandBody(BaseModel):
    type: str
    params: dict = {}
    actor_id: str
    source: str = "manual"


class ModeBody(BaseModel):
    mode: str
    actor_id: str


class ScheduleBody(BaseModel):
    enabled: bool = True
    interval_min: int = 120
    actor_id: str


class AdvisoryBody(BaseModel):
    action: str
    params: dict = {}
    reason: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler_task
    _scheduler_task = asyncio.ensure_future(_scheduler_loop())
    try:
        yield
    finally:
        if _scheduler_task:
            _scheduler_task.cancel()


async def _scheduler_loop() -> None:  # pragma: no cover - background timer
    while True:
        try:
            await asyncio.sleep(30)
            for controller in list(_controllers.values()):
                await controller.tick()
        except asyncio.CancelledError:
            return
        except Exception:
            log.exception("scheduler tick failed")


app = FastAPI(
    title="SomnoSwallow PAM",
    version="1.0.0",
    description=(
        "Positioning-assist mattress controller.\n\n"
        f"**{RUO_NOTICE}**\n\n"
        "Modes: manual, scheduled, advisory_confirm. There is no autonomous mode."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "notice": RUO_NOTICE, "beds": sorted(_controllers)}


@app.get("/v1/mattress/{bed_id}/state")
async def get_state(bed_id: str) -> dict:
    return await get_controller(bed_id).state()


@app.post("/v1/mattress/{bed_id}/command")
async def post_command(bed_id: str, body: CommandBody) -> dict:
    controller = get_controller(bed_id)
    if body.source not in ("manual", "scheduled", "advisory", "safety"):
        raise HTTPException(422, f"unknown source {body.source!r}")
    try:
        cmd = await controller.submit(body.type, body.params, body.actor_id, body.source)
    except SafetyViolation as exc:
        raise HTTPException(409, str(exc)) from None
    if cmd.status == "rejected":
        raise HTTPException(409, cmd.reject_reason or "rejected")
    return cmd.to_dict()


@app.post("/v1/mattress/{bed_id}/emergency-flat")
async def emergency_flat(bed_id: str, actor_id: str = "system") -> dict:
    controller = get_controller(bed_id)
    cmd = await controller.submit("emergency_flat", {}, actor_id, "safety")
    return cmd.to_dict()


@app.post("/v1/mattress/{bed_id}/commands/{command_id}/cancel")
async def cancel_command(bed_id: str, command_id: str, actor_id: str = "system") -> dict:
    ok = get_controller(bed_id).cancel(command_id, actor_id)
    if not ok:
        raise HTTPException(404, "no cancellable command with that id")
    return {"cancelled": True, "command_id": command_id}


@app.put("/v1/mattress/{bed_id}/mode")
async def put_mode(bed_id: str, body: ModeBody) -> dict:
    controller = get_controller(bed_id)
    try:
        controller.set_mode(body.mode, body.actor_id)  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return await controller.state()


@app.put("/v1/mattress/{bed_id}/schedule")
async def put_schedule(bed_id: str, body: ScheduleBody) -> dict:
    controller = get_controller(bed_id)
    try:
        return controller.set_schedule(body.enabled, body.interval_min, body.actor_id)
    except SafetyViolation as exc:
        raise HTTPException(422, str(exc)) from None


@app.get("/v1/mattress/{bed_id}/advisories")
async def list_advisories(bed_id: str) -> list[dict]:
    return [vars(a) | {"created_at": a.created_at.isoformat()} for a in get_controller(bed_id).advisories]


@app.post("/v1/mattress/{bed_id}/advisories")
async def create_advisory(bed_id: str, body: AdvisoryBody) -> dict:
    adv = get_controller(bed_id).propose(body.action, body.params, body.reason)
    return vars(adv) | {"created_at": adv.created_at.isoformat()}


@app.post("/v1/mattress/{bed_id}/advisories/{advisory_id}/confirm")
async def confirm_advisory(bed_id: str, advisory_id: str, actor_id: str) -> dict:
    controller = get_controller(bed_id)
    try:
        cmd = await controller.confirm(advisory_id, actor_id)
    except LookupError:
        raise HTTPException(404, "unknown advisory") from None
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    if cmd.status == "rejected":
        raise HTTPException(409, cmd.reject_reason or "rejected")
    return cmd.to_dict()


@app.post("/v1/mattress/{bed_id}/advisories/{advisory_id}/decline")
async def decline_advisory(bed_id: str, advisory_id: str, actor_id: str) -> dict:
    try:
        get_controller(bed_id).decline(advisory_id, actor_id)
    except LookupError:
        raise HTTPException(404, "unknown advisory") from None
    return {"declined": True}


@app.get("/v1/mattress/{bed_id}/audit")
async def get_audit(bed_id: str, limit: int = 200) -> dict:
    from somno_ing.audit import entries, verify_chain

    intact, bad = verify_chain()
    return {"intact": intact, "first_bad_id": bad, "entries": entries(bed_id, limit)}


@app.get("/v1/mattress/{bed_id}/commands")
async def list_commands(bed_id: str, limit: int = 100) -> list[dict]:
    return [c.to_dict() for c in get_controller(bed_id).commands[-limit:]][::-1]


# ------------------------------------------------------------- test/dev hooks
@app.post("/v1/mattress/{bed_id}/_sim/occupancy")
async def sim_occupancy(bed_id: str, occupied: bool) -> dict:
    """Mock-driver hook: toggle bed occupancy. Not present on real hardware."""
    controller = get_controller(bed_id)
    driver = controller.driver
    if not isinstance(driver, MockMattressDriver):
        raise HTTPException(400, "occupancy can only be forced on the mock driver")
    driver.set_occupancy(occupied)
    return await controller.state()


@app.post("/v1/mattress/{bed_id}/_sim/link")
async def sim_link(bed_id: str, ok: bool) -> dict:
    controller = get_controller(bed_id)
    controller.set_link(ok)
    return await controller.state()
