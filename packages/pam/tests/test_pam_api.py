"""PAM HTTP surface (PRD 9.4)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

BED = "BED-API"


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("pam-api")
    os.environ["DATABASE_URL"] = f"sqlite:///{root}/pam.db"
    os.environ["LOCAL_STORAGE_DIR"] = str(root / "objects")
    # The real notice is 30 s and the real spacing 20 minutes; a test that
    # honoured both would take longer than the rest of the suite combined.
    os.environ["PAM_NOTIFY_SECONDS"] = "0.05"
    os.environ["PAM_MIN_INTERVAL_S"] = "0"

    from somno_ing.db import init_db, reset_engine
    from somno_ing.settings import get_settings

    get_settings.cache_clear()
    reset_engine()
    init_db()

    from somno_pam import api as pam_api

    pam_api._controllers.clear()
    # Instant ramps: the motion physics are covered in test_safety.py.
    with TestClient(pam_api.app) as c:
        pam_api.get_controller(BED).driver.time_scale = 0.0  # type: ignore[attr-defined]
        pam_api.get_controller(BED).driver.step_s = 0.05  # type: ignore[attr-defined]
        yield c
    reset_engine()


def test_health_states_the_scope(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "never delivers electrical stimulation" in body["notice"]
    assert "human confirmation" in body["notice"]


def test_openapi_says_there_is_no_autonomous_mode(client):
    spec = client.get("/openapi.json").json()
    assert "no autonomous mode" in spec["info"]["description"].lower()


def test_state_and_manual_command(client):
    state = client.get(f"/v1/mattress/{BED}/state").json()
    assert state["hob_angle_deg"] == 0.0
    assert state["mode"] == "manual"

    cmd = client.post(
        f"/v1/mattress/{BED}/command",
        json={"type": "set_hob_angle", "params": {"deg": 30.0}, "actor_id": "nurse-1"},
    )
    assert cmd.status_code == 200 and cmd.json()["status"] == "completed"
    assert client.get(f"/v1/mattress/{BED}/state").json()["hob_angle_deg"] == pytest.approx(30.0, abs=0.1)


def test_out_of_range_command_is_refused(client):
    resp = client.post(
        f"/v1/mattress/{BED}/command",
        json={"type": "set_hob_angle", "params": {"deg": 60.0}, "actor_id": "nurse-1"},
    )
    assert resp.status_code == 409
    assert "PAM-S1" in resp.json()["detail"]


def test_autonomous_mode_is_rejected(client):
    resp = client.put(
        f"/v1/mattress/{BED}/mode", json={"mode": "autonomous", "actor_id": "nurse-1"}
    )
    assert resp.status_code == 422
    assert "R2" in resp.json()["detail"]


@pytest.mark.parametrize("mode", ["manual", "scheduled", "advisory_confirm"])
def test_supported_modes(client, mode):
    resp = client.put(f"/v1/mattress/{BED}/mode", json={"mode": mode, "actor_id": "nurse-1"})
    assert resp.status_code == 200 and resp.json()["mode"] == mode


def test_advisory_confirm_flow(client):
    adv = client.post(
        f"/v1/mattress/{BED}/advisories",
        json={"action": "set_lateral_tilt", "params": {"side": "left", "deg": 20}, "reason": "supine"},
    ).json()
    assert adv["status"] == "pending"

    before = client.get(f"/v1/mattress/{BED}/state").json()["lateral_deg"]
    listed = client.get(f"/v1/mattress/{BED}/advisories").json()
    assert any(a["id"] == adv["id"] for a in listed)
    assert client.get(f"/v1/mattress/{BED}/state").json()["lateral_deg"] == before

    confirmed = client.post(
        f"/v1/mattress/{BED}/advisories/{adv['id']}/confirm", params={"actor_id": "nurse-2"}
    ).json()
    assert confirmed["status"] == "completed" and confirmed["source"] == "advisory"
    assert client.get(f"/v1/mattress/{BED}/state").json()["lateral_deg"] == pytest.approx(20.0, abs=0.1)


def test_declining_an_advisory_leaves_the_bed_alone(client):
    adv = client.post(
        f"/v1/mattress/{BED}/advisories",
        json={"action": "set_hob_angle", "params": {"deg": 45}, "reason": "test"},
    ).json()
    before = client.get(f"/v1/mattress/{BED}/state").json()["hob_angle_deg"]
    assert client.post(
        f"/v1/mattress/{BED}/advisories/{adv['id']}/decline", params={"actor_id": "nurse-1"}
    ).json()["declined"]
    assert client.get(f"/v1/mattress/{BED}/state").json()["hob_angle_deg"] == before


def test_unoccupied_bed_refuses_over_http(client):
    client.post(f"/v1/mattress/{BED}/_sim/occupancy", params={"occupied": False})
    resp = client.post(
        f"/v1/mattress/{BED}/command",
        json={"type": "set_hob_angle", "params": {"deg": 10.0}, "actor_id": "nurse-1"},
    )
    assert resp.status_code == 409 and "PAM-S3" in resp.json()["detail"]
    client.post(f"/v1/mattress/{BED}/_sim/occupancy", params={"occupied": True})


def test_link_loss_refuses_over_http(client):
    client.post(f"/v1/mattress/{BED}/_sim/link", params={"ok": False})
    resp = client.post(
        f"/v1/mattress/{BED}/command",
        json={"type": "set_hob_angle", "params": {"deg": 10.0}, "actor_id": "nurse-1"},
    )
    assert resp.status_code == 409 and "PAM-S8" in resp.json()["detail"]
    client.post(f"/v1/mattress/{BED}/_sim/link", params={"ok": True})


def test_schedule_below_the_safety_floor_is_refused(client):
    import somno_pam.api as pam_api

    controller = pam_api.get_controller(BED)
    controller.limits = type(controller.limits)(
        notify_seconds=0.05, min_motion_interval_s=20 * 60
    )
    resp = client.put(
        f"/v1/mattress/{BED}/schedule",
        json={"enabled": True, "interval_min": 5, "actor_id": "nurse-1"},
    )
    assert resp.status_code == 422 and "PAM-S6" in resp.json()["detail"]
    controller.limits = type(controller.limits)(notify_seconds=0.05, min_motion_interval_s=0.0)


def test_emergency_flat_and_audit(client):
    client.post(
        f"/v1/mattress/{BED}/command",
        json={"type": "set_hob_angle", "params": {"deg": 40.0}, "actor_id": "nurse-1"},
    )
    flat = client.post(
        f"/v1/mattress/{BED}/emergency-flat", params={"actor_id": "nurse-1"}
    ).json()
    assert flat["status"] == "completed"
    assert client.get(f"/v1/mattress/{BED}/state").json()["hob_angle_deg"] == 0.0

    audit = client.get(f"/v1/mattress/{BED}/audit").json()
    assert audit["intact"] is True
    actions = {e["action"] for e in audit["entries"]}
    assert {"pam.command", "pam.emergency_flat", "pam.advisory_confirmed", "pam.reject"} <= actions


def test_command_history_is_available(client):
    history = client.get(f"/v1/mattress/{BED}/commands").json()
    assert history
    assert {"id", "type", "status", "source"} <= set(history[0])
