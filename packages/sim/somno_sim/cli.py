"""somno-sim command line."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .config import available_scenarios, load_scenario
from .publisher import make_publisher
from .runner import run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="somno-sim", description="SomnoSwallow device simulator")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="render one night")
    r.add_argument("--scenario", default="healthy_adult", help="bundled name or path to YAML")
    r.add_argument("--seed", type=int, default=42)
    r.add_argument(
        "--speed",
        type=float,
        default=60.0,
        help="wall-clock pacing factor; 1 = real time, 0 = no pacing (fastest)",
    )
    r.add_argument("--device-id", default="dev-001")
    r.add_argument("--subject-code", default="SUBJ-001")
    r.add_argument("--bed-id", default=None)
    r.add_argument(
        "--mqtt",
        dest="target",
        default="none",
        help="mqtt://host:port, file:PATH, or none",
    )
    r.add_argument("--out", type=Path, default=None, help="directory for ground truth and exports")
    r.add_argument("--duration-min", type=float, default=None, help="override scenario duration")
    r.add_argument("--export-edf", action="store_true")
    r.add_argument("--save-raw", action="store_true", help="also write raw chunks as .npz")
    r.add_argument("--quiet", action="store_true")

    sub.add_parser("scenarios", help="list bundled scenarios")

    h = sub.add_parser("hash", help="print the ground-truth hash (determinism check)")
    h.add_argument("--scenario", default="healthy_adult")
    h.add_argument("--seed", type=int, default=42)
    h.add_argument("--duration-min", type=float, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "scenarios":
        for name in available_scenarios():
            cfg = load_scenario(name)
            print(f"{name:20s} {cfg.description.strip().splitlines()[0]}")
        return 0

    cfg = load_scenario(args.scenario)
    if args.duration_min is not None:
        cfg = cfg.model_copy(update={"duration_min": args.duration_min})

    if args.cmd == "hash":
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            res = run(
                cfg,
                seed=args.seed,
                device_id="dev-hash",
                publisher=make_publisher("none", "hash"),
                out_dir=Path(tmp),
                speed=0.0,
            )
            digest = hashlib.sha256(res.ground_truth_path.read_bytes()).hexdigest()
        print(json.dumps({"scenario": cfg.scenario, "seed": args.seed, "sha256": digest}))
        return 0

    out_dir = args.out
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

    publisher = make_publisher(args.target, client_id=f"sim-{args.device_id}", out_dir=out_dir)

    def progress(done: int, total: int) -> None:
        if args.quiet or done % max(1, total // 40):
            return
        pct = 100 * done / total
        print(f"\r  {pct:5.1f}%  chunk {done}/{total}", end="", file=sys.stderr, flush=True)

    try:
        res = run(
            cfg,
            seed=args.seed,
            device_id=args.device_id,
            publisher=publisher,
            out_dir=out_dir,
            speed=args.speed,
            subject_code=args.subject_code,
            bed_id=args.bed_id,
            export_edf=args.export_edf,
            save_raw=args.save_raw,
            progress=None if args.quiet else progress,
        )
    finally:
        publisher.close()

    if not args.quiet:
        print(file=sys.stderr)
    print(
        json.dumps(
            {
                "session_id": res.session_id,
                "scenario": res.scenario,
                "seed": res.seed,
                "duration_ms": res.duration_ms,
                "n_chunks": res.n_chunks,
                "n_swallows": res.n_swallows,
                "wall_seconds": round(res.wall_seconds, 2),
                "ground_truth": str(res.ground_truth_path) if res.ground_truth_path else None,
                "edf": str(res.edf_path) if res.edf_path else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
