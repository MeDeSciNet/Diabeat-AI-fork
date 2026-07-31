"""Detection scoring against SIM ground truth (PRD 6.6 /v1/eval/detection).

Development instrument, not a clinical measure. Matching is greedy nearest-first
on event centres within a tolerance window, which is the standard way to score
sparse event detection and avoids the double-counting that per-sample overlap
scoring produces on short bursts.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_TOLERANCE_MS = 750


@dataclass
class Match:
    gt_index: int
    det_index: int
    onset_error_ms: float


def match_events(
    gt: list[dict], detected: list[dict], tolerance_ms: int = DEFAULT_TOLERANCE_MS
) -> tuple[list[Match], list[int], list[int]]:
    """Greedy nearest matching. Returns (matches, unmatched_gt, unmatched_detected)."""
    gt_c = np.array([0.5 * (e["t_start_ms"] + e["t_end_ms"]) for e in gt], dtype=float)
    det_c = np.array([0.5 * (e["t_start_ms"] + e["t_end_ms"]) for e in detected], dtype=float)

    pairs: list[tuple[float, int, int]] = []
    for i, t in enumerate(gt_c):
        if len(det_c) == 0:
            break
        d = np.abs(det_c - t)
        for j in np.flatnonzero(d <= tolerance_ms):
            pairs.append((float(d[j]), i, int(j)))
    pairs.sort()

    used_gt: set[int] = set()
    used_det: set[int] = set()
    matches: list[Match] = []
    for dist, i, j in pairs:
        if i in used_gt or j in used_det:
            continue
        used_gt.add(i)
        used_det.add(j)
        matches.append(
            Match(
                gt_index=i,
                det_index=j,
                onset_error_ms=float(detected[j]["t_start_ms"] - gt[i]["t_start_ms"]),
            )
        )
    unmatched_gt = [i for i in range(len(gt)) if i not in used_gt]
    unmatched_det = [j for j in range(len(detected)) if j not in used_det]
    return matches, unmatched_gt, unmatched_det


def report(
    session_id: str,
    gt: list[dict],
    detected: list[dict],
    tolerance_ms: int = DEFAULT_TOLERANCE_MS,
    scenario: str | None = None,
    detector_version: str = "unknown",
) -> dict:
    matches, missed, extra = match_events(gt, detected, tolerance_ms)
    tp, fp, fn = len(matches), len(extra), len(missed)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    errs = np.array([m.onset_error_ms for m in matches]) if matches else np.zeros(0)
    onset = {
        "mean": round(float(errs.mean()), 1) if len(errs) else 0.0,
        "sd": round(float(errs.std()), 1) if len(errs) else 0.0,
        "p50": round(float(np.percentile(np.abs(errs), 50)), 1) if len(errs) else 0.0,
        "p90": round(float(np.percentile(np.abs(errs), 90)), 1) if len(errs) else 0.0,
        "max": round(float(np.abs(errs).max()), 1) if len(errs) else 0.0,
    }

    by_stage: dict[str, dict] = {}
    matched_gt = {m.gt_index for m in matches}
    for i, e in enumerate(gt):
        stage = e.get("sleep_stage", "UNKNOWN")
        row = by_stage.setdefault(stage, {"n_ground_truth": 0, "_hit": 0})
        row["n_ground_truth"] += 1
        row["_hit"] += 1 if i in matched_gt else 0
    for row in by_stage.values():
        row["recall"] = round(row["_hit"] / row["n_ground_truth"], 4)
        del row["_hit"]

    coord_ok = sum(
        1
        for m in matches
        if detected[m.det_index].get("coordination_pattern")
        == gt[m.gt_index].get("coordination_pattern")
    )
    coordination_accuracy = round(coord_ok / len(matches), 4) if matches else None

    return {
        "session_id": session_id,
        "scenario": scenario,
        "detector_version": detector_version,
        "tolerance_ms": tolerance_ms,
        "n_ground_truth": len(gt),
        "n_detected": len(detected),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "onset_error_ms": onset,
        "by_sleep_stage": by_stage,
        "coordination_accuracy": coordination_accuracy,
    }
