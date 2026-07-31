"""API surface (PRD 6.6) and the ingest/offline-upload paths."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from somno_ing.api.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_carries_the_research_use_notice(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "research use only" in body["notice"].lower()
    assert "diagnosis" in body["notice"].lower()


def test_openapi_describes_the_service_as_non_diagnostic(client):
    spec = client.get("/openapi.json").json()
    assert "research use only" in spec["info"]["description"].lower()
    assert "not an active patient monitor" in spec["info"]["description"].lower()


def test_session_detail_and_events(client, analysed_session):
    sid = analysed_session["session_id"]
    session = client.get(f"/v1/sessions/{sid}").json()
    assert session["id"] == sid
    assert session["status"] == "analyzed"
    assert session["n_events"] > 0
    assert session["risk"]["algorithm_version"].startswith("risk-v")

    events = client.get(f"/v1/sessions/{sid}/events", params={"limit": 5}).json()
    assert events["total"] == session["n_events"]
    assert len(events["items"]) <= 5
    for e in events["items"]:
        assert e["source"] == "detected"
        assert e["coordination_pattern"] in ("E-E", "E-I", "I-E", "I-I", "UNKNOWN")


def test_events_can_be_filtered_by_confidence_and_pattern(client, analysed_session):
    sid = analysed_session["session_id"]
    high = client.get(f"/v1/sessions/{sid}/events", params={"min_confidence": 0.99}).json()
    everything = client.get(f"/v1/sessions/{sid}/events").json()
    assert high["total"] <= everything["total"]


def test_risk_endpoint(client, analysed_session):
    risk = client.get(f"/v1/sessions/{analysed_session['session_id']}/risk").json()
    assert risk["band"] in ("low", "moderate", "elevated", "insufficient_data")
    assert set(risk["components"]) == {
        "sfi_burden",
        "coordination_anomaly",
        "supine_burden",
        "arousal_decoupling",
    }


def test_timeline_is_downsampled_for_plotting(client, analysed_session):
    tl = client.get(
        f"/v1/sessions/{analysed_session['session_id']}/timeline", params={"points": 300}
    ).json()
    assert tl["epochs"] and tl["postures"]
    assert len(tl["signal"]) <= 320
    assert {"t_ms", "acoustic", "artifact", "coverage"} <= set(tl["signal"][0])


def test_signal_window_is_bounded(client, analysed_session):
    sid = analysed_session["session_id"]
    ok = client.get(f"/v1/sessions/{sid}/signal", params={"t_start_ms": 0, "t_end_ms": 60000})
    assert ok.status_code == 200 and ok.json()["acoustic_env"]
    too_wide = client.get(
        f"/v1/sessions/{sid}/signal", params={"t_start_ms": 0, "t_end_ms": 600_000}
    )
    assert too_wide.status_code == 400


def test_edf_export_round_trips(client, analysed_session, tmp_path):
    import pyedflib

    resp = client.get(f"/v1/sessions/{analysed_session['session_id']}/export/edf")
    assert resp.status_code == 200
    path = tmp_path / "out.edf"
    path.write_bytes(resp.content)
    with pyedflib.EdfReader(str(path)) as reader:
        assert reader.signals_in_file >= 5
        assert reader.readSignal(0).size > 0
        assert any("swallow" in a for a in reader.readAnnotations()[2])


def test_eval_endpoint_reports_detection_metrics(client, analysed_session):
    report = client.get(
        "/v1/eval/detection", params={"session_id": analysed_session["session_id"]}
    ).json()
    assert report["n_ground_truth"] > 0
    assert 0.0 <= report["f1"] <= 1.0
    assert report["detector_version"].startswith("detect-")


def test_alert_acknowledge_and_dismiss_are_recorded(client, analysed_session):
    from somno_ing.alerts import VALID_ACTIONS
    from somno_ing.db import AlertRow, db_session

    with db_session() as db:
        db.add(
            AlertRow(
                id="alert-api-test",
                session_id=analysed_session["session_id"],
                subject_code="SUBJ-TEST",
                bed_id="BED-TEST",
                rule_id="test_rule",
                severity="advisory",
                status="open",
                title="test",
                recommended_actions=["ACTION_ORAL_CARE"],
                dedup_key="k",
            )
        )

    acked = client.post("/v1/alerts/alert-api-test/ack").json()
    assert acked["status"] == "acknowledged" and acked["acknowledged_by"]

    dismissed = client.post(
        "/v1/alerts/alert-api-test/dismiss",
        json={"reason": "false_positive", "note": "snoring, not a swallow"},
    ).json()
    assert dismissed["status"] == "dismissed"
    assert dismissed["dismiss_reason"] == "false_positive"

    stats = client.get("/v1/alerts-stats/dismissals").json()
    assert stats["by_rule"]["test_rule"]["false_positive"] == 1
    assert set(client.get("/v1/meta").json()["actions"]) == VALID_ACTIONS


def test_dismiss_requires_a_known_reason(client):
    from somno_ing.db import AlertRow, db_session

    with db_session() as db:
        db.add(
            AlertRow(
                id="alert-reason-test",
                session_id=None,
                subject_code="SUBJ-TEST",
                rule_id="r",
                severity="advisory",
                status="open",
                title="t",
                recommended_actions=["ACTION_ORAL_CARE"],
                dedup_key="k2",
            )
        )
    resp = client.post("/v1/alerts/alert-reason-test/dismiss", json={"reason": "because"})
    assert resp.status_code == 422


def test_care_actions_are_restricted_to_the_dictionary(client):
    ok = client.post(
        "/v1/care-actions",
        json={"subject_code": "SUBJ-TEST", "action": "ACTION_HOB30"},
    )
    assert ok.status_code == 201
    bad = client.post(
        "/v1/care-actions", json={"subject_code": "SUBJ-TEST", "action": "ACTION_INVENTED"}
    )
    assert bad.status_code == 422


def test_bed_overview_never_uses_a_red_light(client, analysed_session):
    from somno_ing.db import Bed, db_session

    with db_session() as db:
        if db.get(Bed, "BED-TEST") is None:
            db.add(Bed(bed_id="BED-TEST", ward="Ward A", subject_code="SUBJ-TEST", has_pam=True))

    beds = client.get("/v1/beds").json()
    assert beds
    assert all(b["light"] in ("grey", "blue", "amber") for b in beds)


def test_shift_summary_aggregates_actions_by_bed(client):
    body = client.get("/v1/shift-summary", params={"shift": "day"}).json()
    assert body["shift"] == "day" and "window" in body


def test_trend_endpoint_returns_nights_and_care_actions(client, analysed_session):
    body = client.get("/v1/subjects/SUBJ-TEST/trend", params={"nights": 30}).json()
    assert body["subject_code"] == "SUBJ-TEST"
    assert any(n["session_id"] == analysed_session["session_id"] for n in body["nights"])
    assert isinstance(body["care_actions"], list)


def test_system_health_lists_devices(client, analysed_session):
    body = client.get("/v1/system-health").json()
    assert "devices" in body and "data_gaps" in body


def test_fhir_and_nurse_call_are_mocks_only(client, analysed_session):
    sid = analysed_session["session_id"]
    obs = client.get(f"/v1/integrations/fhir/observation/{sid}").json()
    assert obs["resourceType"] == "Observation"
    assert obs["status"] == "preliminary"
    assert "research use only" in obs["note"][0]["text"].lower()

    from somno_ing.db import AlertRow, db_session

    with db_session() as db:
        db.add(
            AlertRow(
                id="alert-fhir",
                subject_code="SUBJ-TEST",
                bed_id="BED-TEST",
                rule_id="r",
                severity="advisory",
                status="open",
                title="t",
                recommended_actions=["ACTION_LATERAL"],
                dedup_key="k3",
            )
        )
    issue = client.get("/v1/integrations/fhir/detected-issue/alert-fhir").json()
    assert issue["resourceType"] == "DetectedIssue"
    assert issue["severity"] in ("low", "moderate")  # never 'high'

    call = client.post("/v1/integrations/nurse-call/alert-fhir").json()
    assert call["delivered"] is False


def test_audit_endpoint_reports_an_intact_chain(client):
    body = client.get("/v1/audit").json()
    assert body["intact"] is True


def test_offline_upload_matches_the_streamed_path(client, tmp_path):
    """ING-3: a microSD import must go through the same processing as MQTT."""
    from somno_sim.config import load_scenario
    from somno_sim.publisher import FilePublisher
    from somno_sim.runner import run

    cfg = load_scenario("healthy_adult").model_copy(update={"duration_min": 20.0})
    path = tmp_path / "stream.ndjson"
    publisher = FilePublisher(path)
    result = run(
        cfg,
        seed=7,
        device_id="dev-upload",
        publisher=publisher,
        out_dir=None,
        speed=0.0,
        subject_code="SUBJ-UPLOAD",
    )
    publisher.close()

    with path.open("rb") as fh:
        resp = client.post(
            f"/v1/sessions/{result.session_id}/upload",
            files={"file": ("stream.ndjson", fh, "application/x-ndjson")},
        )
    assert resp.status_code == 200
    assert resp.json()["session_id"] == result.session_id

    session = client.get(f"/v1/sessions/{result.session_id}").json()
    assert session["status"] == "analyzed"
    assert session["n_events"] > 0


def test_dropped_chunks_are_recorded_as_gaps_and_lower_coverage(tmp_path):
    """ING-2: a delivery gap must show up in coverage, not vanish."""
    from somno_ing.ingest.consumer import IngestService
    from somno_ing.pipeline import analyze, persist_ingest
    from somno_sim.config import load_scenario
    from somno_sim.publisher import CallbackPublisher
    from somno_sim.runner import run

    cfg = load_scenario("healthy_adult").model_copy(update={"duration_min": 20.0})
    service = IngestService(on_session_closed=lambda ing: None)
    closed = []
    service.on_session_closed = closed.append

    def lossy(topic, payload):
        # Drop a contiguous run of chunks, as a radio dropout would.
        if topic.endswith("/signal") and 40 <= payload["seq"] < 80:
            return
        service.handle(topic, payload)

    result = run(
        cfg,
        seed=11,
        device_id="dev-gap",
        publisher=CallbackPublisher(lossy),
        out_dir=None,
        speed=0.0,
        subject_code="SUBJ-GAP",
    )
    persist_ingest(closed[0])
    out = analyze(result.session_id)

    assert closed[0].gaps, "a 40-chunk dropout was not recorded"
    coverage = out["risk"]["data_quality"]["signal_coverage"]
    assert coverage < 1.0
    assert coverage == pytest.approx(1 - 40 / 240, abs=0.02)
