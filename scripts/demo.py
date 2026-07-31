#!/usr/bin/env python3
"""End-to-end walkthrough (PRD 12, first acceptance item).

Runs the whole chain and prints what each stage produced:

    SIM -> ING ingest -> detection -> features -> index -> alerts
        -> the exact API calls CARE and STATION make
        -> one PAM advisory, confirmed by a human actor

Two modes:
  local   (default) everything in process, SQLite + filesystem object store
  remote  --remote, against a running `docker compose up` stack over HTTP

Exit code is non-zero if any acceptance check fails, so this doubles as the CI
end-to-end gate.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

GREEN, RED, DIM, BOLD, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"

FAILURES: list[str] = []


def head(title: str) -> None:
    print(f"\n{BOLD}{title}{RESET}\n{'-' * len(title)}")


def check(label: str, ok: bool, detail: str = "") -> bool:
    mark = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
    print(f"  [{mark}] {label}" + (f" {DIM}{detail}{RESET}" if detail else ""))
    if not ok:
        FAILURES.append(label)
    return ok


def info(label: str, value) -> None:
    print(f"    {DIM}{label}:{RESET} {value}")


# ---------------------------------------------------------------------- local
def run_local(args) -> None:
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{REPO}/data/demo.db")
    os.environ.setdefault("LOCAL_STORAGE_DIR", str(REPO / "data" / "demo-objects"))
    os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")
    os.environ.setdefault("API_AUTH_REQUIRED", "false")

    from somno_ing.db import Bed, Subject, db_session, init_db
    from somno_ing.devtools import run_scenario

    init_db()
    with db_session() as db:
        if db.get(Subject, args.subject) is None:
            db.add(Subject(subject_code=args.subject))
        if db.get(Bed, args.bed) is None:
            db.add(Bed(bed_id=args.bed, ward="Ward A", subject_code=args.subject, has_pam=True))

    head(f"1. SIM -> ING  ({args.scenario}, seed {args.seed}, {args.minutes:.0f} min)")
    result = run_scenario(
        scenario=args.scenario,
        seed=args.seed,
        duration_min=args.minutes,
        subject_code=args.subject,
        bed_id=args.bed,
    )
    session_id = result["session_id"]
    analysis = result["analysis"]
    ev = result["eval"]

    info("session", session_id)
    info("ground truth swallows", ev["n_ground_truth"])
    info("detected swallows", ev["n_detected"])
    info("precision / recall / F1", f"{ev['precision']} / {ev['recall']} / {ev['f1']}")
    info("onset error p90", f"{ev['onset_error_ms']['p90']} ms")
    check("SIM produced ground truth", ev["n_ground_truth"] > 0)
    check("detection ran and matched ground truth", ev["f1"] >= 0.7, f"F1={ev['f1']}")

    head("2. Features and the overnight signal index")
    risk = analysis["risk"]
    feats = analysis["features"]
    info("band", risk["band"])
    info("score", risk["score"])
    info("coverage / artifact", f"{risk['data_quality']['signal_coverage']} / {risk['data_quality']['artifact_ratio']}")
    for name, comp in risk["components"].items():
        info(name, f"value={comp['value']} raw={comp['raw']} weight={comp['weight']}")
    info("swallows per hour", feats["swallows_per_hour"])
    info("longest swallow-free interval", f"{feats['sfi_max_s']} s")
    info("coordination patterns", feats["coordination_counts"])
    check("index carries an algorithm version", bool(risk["algorithm_version"]))
    check(
        "score is withheld when data quality fails",
        (risk["band"] == "insufficient_data") == (risk["score"] is None),
    )

    head("3. Alerts")
    alerts = analysis["alerts"]
    if not alerts:
        print(f"    {DIM}no alerts raised for this night{RESET}")
    for a in alerts:
        info(a["severity"], f"{a['title']}  -> {', '.join(a['recommended_actions'])}")
    n_attention = sum(1 for a in alerts if a["severity"] == "attention")
    n_advisory = sum(1 for a in alerts if a["severity"] == "advisory")
    check("at most 1 attention alert", n_attention <= 1, f"got {n_attention}")
    check("at most 2 advisory alerts", n_advisory <= 2, f"got {n_advisory}")
    check("every alert is actionable", all(a["recommended_actions"] for a in alerts))

    head("4. What CARE and STATION load")
    from fastapi.testclient import TestClient

    from somno_ing.api.app import app

    with TestClient(app) as client:
        session = client.get(f"/v1/sessions/{session_id}").json()
        timeline = client.get(f"/v1/sessions/{session_id}/timeline?points=900").json()
        beds = client.get("/v1/beds").json()
        queue = client.get("/v1/alerts?status=open").json()
        trend = client.get(f"/v1/subjects/{args.subject}/trend").json()
        health = client.get("/v1/system-health").json()
        notice = client.get("/health").json()["notice"]

    info("CARE  /v1/sessions/{id}", f"{session['n_events']} events, status {session['status']}")
    info("CARE  /timeline", f"{len(timeline['signal'])} points, {len(timeline['postures'])} posture segments")
    info("CARE  /trend", f"{len(trend['nights'])} nights")
    info("STATION /v1/beds", f"{len(beds)} beds, lights {[b['light'] for b in beds]}")
    info("STATION /v1/alerts", f"{len(queue)} open")
    info("STATION /v1/system-health", f"{len(health['devices'])} devices")
    check("timeline is downsampled for plotting", len(timeline["signal"]) <= 950)
    check("bed lights never use red", all(b["light"] in ("grey", "blue", "amber") for b in beds))
    check("research-use notice is served", "research use only" in notice.lower())

    head("5. PAM advisory -> human confirmation")
    asyncio.run(pam_local(args))


async def pam_local(args) -> None:
    from somno_ing.audit import record, verify_chain
    from somno_pam.controller import MattressController
    from somno_pam.driver import MockMattressDriver
    from somno_pam.safety import SafetyLimits

    driver = MockMattressDriver(bed_id=args.bed, step_s=0.05, time_scale=0.0)
    controller = MattressController(
        bed_id=args.bed,
        driver=driver,
        limits=SafetyLimits(notify_seconds=0.2, min_motion_interval_s=0.0),
        audit=lambda actor, action, detail, bed: record(actor, action, detail, bed_id=bed),
    )
    controller.set_mode("advisory_confirm", "nurse-1")

    advisory = controller.propose(
        "set_hob_angle",
        {"deg": 30.0},
        "supine for most of the recording with the head of bed below 30 degrees",
    )
    info("advisory", advisory.reason)
    state = await controller.state()
    check("proposing does not move the bed", state["hob_angle_deg"] == 0.0)

    cmd = await controller.confirm(advisory.id, "nurse-1")
    state = await controller.state()
    info("after confirmation", f"head of bed {state['hob_angle_deg']:.0f} deg")
    check("confirmed advisory ran", cmd.status == "completed")
    check("head of bed reached 30 degrees", abs(state["hob_angle_deg"] - 30.0) < 0.5)

    driver.set_occupancy(False)
    refused = await controller.submit("set_hob_angle", {"deg": 15.0}, "nurse-1")
    check(
        "an empty bed refuses all motion (PAM-S3)",
        refused.status == "rejected" and "PAM-S3" in (refused.reject_reason or ""),
        refused.reject_reason or "",
    )
    driver.set_occupancy(True)

    intact, bad = verify_chain()
    check("audit chain is intact", intact, f"first bad id {bad}" if bad else "")


# --------------------------------------------------------------------- remote
def run_remote(args) -> None:
    import httpx

    ing = args.ing_base
    pam = args.pam_base
    headers = {"Authorization": f"Bearer {args.token}"}

    head("1. Service health")
    with httpx.Client(timeout=30) as c:
        notice = c.get(f"{ing}/health").json()["notice"]
        check("ING is up", True)
        check("research-use notice is served", "research use only" in notice.lower())
        check("PAM is up", c.get(f"{pam}/health").json()["status"] == "ok")

        head("2. Latest analysed session")
        sessions = c.get(f"{ing}/v1/sessions", headers=headers, params={"subject_code": args.subject}).json()
        analysed = [s for s in sessions if s["status"] == "analyzed"]
        if not check("a session has been analysed", bool(analysed), "run `make sim-docker` first"):
            return
        sid = analysed[0]["id"]
        session = c.get(f"{ing}/v1/sessions/{sid}", headers=headers).json()
        info("session", sid)
        info("events", session["n_events"])
        info("band", (session.get("risk") or {}).get("band"))

        head("3. Dashboards")
        beds = c.get(f"{ing}/v1/beds", headers=headers).json()
        timeline = c.get(f"{ing}/v1/sessions/{sid}/timeline", headers=headers).json()
        alerts = c.get(f"{ing}/v1/alerts", headers=headers, params={"status": "open"}).json()
        info("beds", len(beds))
        info("timeline points", len(timeline["signal"]))
        info("open alerts", len(alerts))
        check("bed lights never use red", all(b["light"] in ("grey", "blue", "amber") for b in beds))
        check("at most 1 attention alert per session", sum(1 for a in alerts if a["severity"] == "attention" and a["session_id"] == sid) <= 1)

        head("4. PAM advisory -> human confirmation")
        adv = c.post(
            f"{pam}/v1/mattress/{args.bed}/advisories",
            json={"action": "set_hob_angle", "params": {"deg": 30.0}, "reason": "demo"},
        ).json()
        before = c.get(f"{pam}/v1/mattress/{args.bed}/state").json()
        check("proposing does not move the bed", before["hob_angle_deg"] == 0.0)
        confirmed = c.post(
            f"{pam}/v1/mattress/{args.bed}/advisories/{adv['id']}/confirm",
            params={"actor_id": "nurse-1"},
            timeout=180,
        ).json()
        after = c.get(f"{pam}/v1/mattress/{args.bed}/state").json()
        info("after confirmation", f"head of bed {after['hob_angle_deg']:.0f} deg")
        check("confirmed advisory ran", confirmed.get("status") == "completed")
        audit = c.get(f"{pam}/v1/mattress/{args.bed}/audit").json()
        check("audit chain is intact", audit["intact"])


def main() -> int:
    p = argparse.ArgumentParser(description="SomnoSwallow end-to-end walkthrough")
    p.add_argument("--remote", action="store_true", help="run against a docker compose stack")
    p.add_argument("--scenario", default="elderly_high_risk")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--minutes", type=float, default=180.0)
    p.add_argument("--subject", default="SUBJ-001")
    p.add_argument("--bed", default="BED-01")
    p.add_argument("--ing-base", default=os.getenv("ING_BASE", "http://localhost:8000"))
    p.add_argument("--pam-base", default=os.getenv("PAM_BASE", "http://localhost:8100"))
    p.add_argument("--token", default=os.getenv("DEV_API_TOKEN", "dev-token"))
    p.add_argument("--json", action="store_true", help="print a machine-readable summary")
    args = p.parse_args()

    print(f"{BOLD}SomnoSwallow demo{RESET}  {DIM}research use only - not a diagnosis{RESET}")
    if args.remote:
        run_remote(args)
    else:
        run_local(args)

    head("Result")
    if FAILURES:
        print(f"  {RED}{len(FAILURES)} check(s) failed:{RESET}")
        for f in FAILURES:
            print(f"    - {f}")
    else:
        print(f"  {GREEN}all checks passed{RESET}")
    if args.json:
        print(json.dumps({"failures": FAILURES, "ok": not FAILURES}))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
