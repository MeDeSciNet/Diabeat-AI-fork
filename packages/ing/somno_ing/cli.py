"""somno-ing command line."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="somno-ing", description="SomnoSwallow ingest and analysis")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-db", help="create tables (and the Timescale hypertable)")
    sub.add_parser("consume", help="run the MQTT consumer")

    s = sub.add_parser("serve", help="run the API")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--reload", action="store_true")

    a = sub.add_parser("analyze", help="re-run analysis for a stored session")
    a.add_argument("session_id")

    sim = sub.add_parser("simulate", help="run a SIM scenario through ingest, in process")
    sim.add_argument("--scenario", default="healthy_adult")
    sim.add_argument("--seed", type=int, default=42)
    sim.add_argument("--duration-min", type=float, default=None)
    sim.add_argument("--subject-code", default="SUBJ-001")
    sim.add_argument("--bed-id", default="BED-01")
    sim.add_argument("--device-id", default="dev-001")
    sim.add_argument("--out", type=Path, default=None)

    ev = sub.add_parser("eval", help="score detection against ground truth")
    ev.add_argument("session_id")
    ev.add_argument("--tolerance-ms", type=int, default=750)

    b = sub.add_parser("bench", help="run every scenario and report detection metrics")
    b.add_argument("--duration-min", type=float, default=120.0)
    b.add_argument("--seed", type=int, default=42)
    b.add_argument("--out", type=Path, default=None)

    sd = sub.add_parser("seed-demo", help="create demo beds and subjects")
    sd.add_argument("--beds", type=int, default=12)
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)

    if args.cmd == "init-db":
        from .db import init_db

        init_db()
        print("database ready")
        return 0

    if args.cmd == "consume":
        from .db import init_db
        from .ingest.consumer import IngestService

        init_db()
        IngestService().run_forever()
        return 0

    if args.cmd == "serve":
        import uvicorn

        uvicorn.run(
            "somno_ing.api.app:app", host=args.host, port=args.port, reload=args.reload
        )
        return 0

    if args.cmd == "analyze":
        from .pipeline import analyze

        print(json.dumps(analyze(args.session_id), indent=2, default=str))
        return 0

    if args.cmd == "simulate":
        from .devtools import run_scenario, write_report

        result = run_scenario(
            scenario=args.scenario,
            seed=args.seed,
            duration_min=args.duration_min,
            subject_code=args.subject_code,
            bed_id=args.bed_id,
            device_id=args.device_id,
        )
        if args.out:
            write_report(args.out, result)
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.cmd == "eval":
        from .devtools import evaluate_session

        print(json.dumps(evaluate_session(args.session_id, args.tolerance_ms), indent=2))
        return 0

    if args.cmd == "bench":
        from somno_sim.config import available_scenarios

        from .devtools import run_scenario, write_report

        rows = []
        for name in available_scenarios():
            res = run_scenario(
                scenario=name,
                seed=args.seed,
                duration_min=args.duration_min,
                subject_code=f"SUBJ-{name[:6].upper()}",
                bed_id=None,
            )
            ev = res["eval"]
            rows.append(
                {
                    "scenario": name,
                    "session_id": res["session_id"],
                    "n_ground_truth": ev["n_ground_truth"],
                    "n_detected": ev["n_detected"],
                    "precision": ev["precision"],
                    "recall": ev["recall"],
                    "f1": ev["f1"],
                    "onset_p90_ms": ev["onset_error_ms"]["p90"],
                    "coordination_accuracy": ev["coordination_accuracy"],
                    "band": res["analysis"]["risk"]["band"],
                    "score": res["analysis"]["risk"]["score"],
                    "alerts": [a["rule_id"] for a in res["analysis"]["alerts"]],
                }
            )
            print(
                f"{name:20s} F1={ev['f1']:.3f} P={ev['precision']:.3f} R={ev['recall']:.3f} "
                f"gt={ev['n_ground_truth']:4d} det={ev['n_detected']:4d} "
                f"band={rows[-1]['band']}"
            )
        if args.out:
            write_report(args.out, {"duration_min": args.duration_min, "rows": rows})
        return 0

    if args.cmd == "seed-demo":
        from .db import Bed, Subject, db_session, init_db

        init_db()
        with db_session() as db:
            for i in range(1, args.beds + 1):
                bed_id = f"BED-{i:02d}"
                code = f"SUBJ-{i:03d}"
                if db.get(Subject, code) is None:
                    db.add(Subject(subject_code=code))
                if db.get(Bed, bed_id) is None:
                    db.add(
                        Bed(
                            bed_id=bed_id,
                            ward="Ward A" if i <= args.beds // 2 else "Ward B",
                            subject_code=code,
                            has_pam=i % 2 == 1,
                        )
                    )
        print(f"seeded {args.beds} beds")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
