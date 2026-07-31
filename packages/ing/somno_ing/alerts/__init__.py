"""Alert rules engine (PRD 6.5).

The fatigue controls in section 2.3 are not tuning knobs, they are the contract:
ICU telemetry runs at 80-99% non-actionable alarms and a nurse can face 350 a
day, so an alerting system that does not aggressively suppress itself is worse
than none. Enforced here, with tests, rather than left to rule authors:

* at most one ``attention`` plus two ``advisory`` per session, overflow folded
  into a summary line;
* every alert carries at least one action, checked when rules load;
* the same finding three nights running is downgraded to a trend note;
* a session that failed the data-quality gate produces nothing at all.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import yaml

from ..settings import get_settings

SEVERITY_RANK = {"attention": 3, "advisory": 2, "info": 1}
CAPS = {"attention": 1, "advisory": 2}
REPEAT_NIGHTS_TO_DOWNGRADE = 3

VALID_ACTIONS = {
    "ACTION_HOB30",
    "ACTION_LATERAL",
    "ACTION_ORAL_CARE",
    "ACTION_SUCTION_ASSESS",
    "ACTION_CLINICIAN_REVIEW",
}

OPERATORS = {
    "gte": lambda a, b: a >= b,
    "gt": lambda a, b: a > b,
    "lte": lambda a, b: a <= b,
    "lt": lambda a, b: a < b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "in": lambda a, b: a in b,
}


@dataclass
class Rule:
    id: str
    severity: str
    when: dict[str, dict]
    title: str
    actions: list[str]
    body: str = ""
    priority: int = 0


@dataclass
class QuietHours:
    start: str = "22:00"
    end: str = "07:00"
    enabled: bool = True
    # Wall-clock offset of the care setting. A fixed offset rather than a named
    # zone so the service does not need tzdata in the container image; a
    # deployment spanning DST changes should replace this with a real zone.
    utc_offset_hours: float = 0.0

    def next_delivery(self, at: datetime) -> datetime:
        """Push delivery to the end of quiet hours. Never suppresses, only delays."""
        if not self.enabled:
            return at
        at = at if at.tzinfo else at.replace(tzinfo=UTC)
        offset = timedelta(hours=self.utc_offset_hours)
        local = at.astimezone(UTC) + offset

        s = time.fromisoformat(self.start)
        e = time.fromisoformat(self.end)
        overnight = s > e
        now = local.time()
        inside = (now >= s or now < e) if overnight else (s <= now < e)
        if not inside:
            return at
        target_day = local.date() + timedelta(days=1) if (overnight and now >= s) else local.date()
        deliver_local = datetime.combine(target_day, e, tzinfo=UTC)
        return deliver_local - offset


@dataclass
class RuleSet:
    rules: list[Rule]
    quiet_hours: QuietHours = field(default_factory=QuietHours)

    @classmethod
    def load(cls, path: Path | None = None) -> "RuleSet":
        p = Path(path or get_settings().alert_rules)
        raw = yaml.safe_load(p.read_text()) if p.exists() else {"rules": []}
        rules = []
        for r in raw.get("rules", []):
            actions = r.get("actions", [])
            if not actions:
                raise ValueError(
                    f"rule {r['id']!r} has no actions. PRD 2.3: an alert without an "
                    "actionable step must not be produced."
                )
            bad = set(actions) - VALID_ACTIONS
            if bad:
                raise ValueError(f"rule {r['id']!r} uses unknown actions: {sorted(bad)}")
            if r["severity"] not in SEVERITY_RANK:
                raise ValueError(f"rule {r['id']!r} has unknown severity {r['severity']!r}")
            rules.append(
                Rule(
                    id=r["id"],
                    severity=r["severity"],
                    when=r.get("when", {}),
                    title=r["title"],
                    body=r.get("body", ""),
                    actions=actions,
                    priority=int(r.get("priority", 0)),
                )
            )
        qh = raw.get("quiet_hours", {})
        return cls(rules=rules, quiet_hours=QuietHours(**qh) if qh else QuietHours())


@dataclass
class EvaluatedAlert:
    rule_id: str
    severity: str
    title: str
    body: str
    recommended_actions: list[str]
    dedup_key: str
    repeat_nights: int
    context: dict
    deliver_after: datetime | None


def build_context(features: dict, risk: dict) -> dict[str, Any]:
    """Flatten features and risk into the dotted namespace rules address."""
    ctx: dict[str, Any] = dict(features)
    ctx["risk.score"] = risk.get("score")
    ctx["risk.band"] = risk.get("band")
    for k, v in (risk.get("data_quality") or {}).items():
        ctx[f"data_quality.{k}"] = v
    for name, comp in (risk.get("components") or {}).items():
        ctx[f"components.{name}.value"] = comp["value"]
        ctx[f"components.{name}.raw"] = comp.get("raw")
    ctx["hob_angle_deg"] = features.get("mean_hob_angle_deg")
    # Percent-formatted mirrors, used by the body templates.
    for key in ("supine_burden", "coordination_anomaly", "sfi_burden", "arousal_coupling"):
        if isinstance(features.get(key), (int, float)):
            ctx[f"{key}_pct"] = round(100 * float(features[key]))
    if isinstance(features.get("sfi_max_s"), (int, float)):
        ctx["sfi_max_min"] = round(features["sfi_max_s"] / 60.0, 1)
    return ctx


def _matches(rule: Rule, ctx: dict) -> bool:
    for key, cond in rule.when.items():
        value = ctx.get(key)
        if value is None:
            return False
        for op, target in cond.items():
            fn = OPERATORS.get(op)
            if fn is None:
                raise ValueError(f"rule {rule.id!r} uses unknown operator {op!r}")
            try:
                if not fn(value, target):
                    return False
            except TypeError:
                return False
    return True


def dedup_key(subject_code: str, rule_id: str) -> str:
    return hashlib.sha256(f"{subject_code}|{rule_id}".encode()).hexdigest()[:32]


def evaluate(
    subject_code: str,
    features: dict,
    risk: dict,
    ruleset: RuleSet | None = None,
    repeat_counts: dict[str, int] | None = None,
    now: datetime | None = None,
) -> tuple[list[EvaluatedAlert], str | None]:
    """Return the alerts to raise plus an optional summary of what was folded in."""
    ruleset = ruleset or RuleSet.load()
    repeat_counts = repeat_counts or {}
    now = now or datetime.now(UTC)

    # Hard stop: no score, no alerts.
    if risk.get("band") == "insufficient_data":
        return [], None

    ctx = build_context(features, risk)
    fired: list[EvaluatedAlert] = []
    for rule in ruleset.rules:
        if not _matches(rule, ctx):
            continue
        key = dedup_key(subject_code, rule.id)
        repeats = repeat_counts.get(key, 0) + 1
        severity = rule.severity
        body = _render(rule.body, ctx)
        if repeats >= REPEAT_NIGHTS_TO_DOWNGRADE:
            # Same finding, third night running: stop interrupting, start trending.
            severity = "info"
            body = (
                f"{body} This has now been the same on {repeats} consecutive nights; "
                "it is being tracked as a trend rather than repeated each morning."
            ).strip()
        fired.append(
            EvaluatedAlert(
                rule_id=rule.id,
                severity=severity,
                title=_render(rule.title, ctx),
                body=body,
                recommended_actions=list(rule.actions),
                dedup_key=key,
                repeat_nights=repeats,
                context={k: ctx.get(k) for k in rule.when},
                deliver_after=ruleset.quiet_hours.next_delivery(now),
            )
        )

    fired.sort(
        key=lambda a: (SEVERITY_RANK[a.severity], _priority(ruleset, a.rule_id)), reverse=True
    )

    kept: list[EvaluatedAlert] = []
    folded: list[EvaluatedAlert] = []
    counts = {k: 0 for k in CAPS}
    for alert in fired:
        cap = CAPS.get(alert.severity)
        if cap is None:  # 'info' is a trend note, not an interruption
            kept.append(alert)
            continue
        if counts[alert.severity] < cap:
            counts[alert.severity] += 1
            kept.append(alert)
        else:
            folded.append(alert)

    summary = None
    if folded:
        summary = "Also observed, folded into this summary: " + "; ".join(
            a.title for a in folded
        )
    return kept, summary


def _priority(ruleset: RuleSet, rule_id: str) -> int:
    for r in ruleset.rules:
        if r.id == rule_id:
            return r.priority
    return 0


def _render(template: str, ctx: dict) -> str:
    out = template
    for key, value in ctx.items():
        token = "{" + key + "}"
        if token in out:
            out = out.replace(token, str(value))
    return out


def new_alert_id() -> str:
    return str(uuid.uuid4())


def consecutive_night_key(subject_code: str, rule_id: str, night: date) -> str:
    return f"{dedup_key(subject_code, rule_id)}:{night.isoformat()}"
