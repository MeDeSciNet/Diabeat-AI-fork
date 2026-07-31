"""Alert fatigue controls (PRD 2.3). These are contractual, not advisory."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from somno_ing.alerts import (
    CAPS,
    REPEAT_NIGHTS_TO_DOWNGRADE,
    VALID_ACTIONS,
    QuietHours,
    Rule,
    RuleSet,
    build_context,
    dedup_key,
    evaluate,
)


def _features(**over) -> dict:
    base = {
        "n_events": 60,
        "sfi_burden": 0.1,
        "sfi_max_s": 400.0,
        "coordination_anomaly": 0.1,
        "supine_burden": 0.2,
        "arousal_coupling": 0.7,
        "snore_ratio": 0.05,
        "mean_hob_angle_deg": 30.0,
    }
    base.update(over)
    return base


def _risk(band="moderate", coverage=0.95, artifact=0.05) -> dict:
    return {
        "score": 50.0 if band != "insufficient_data" else None,
        "band": band,
        "components": {},
        "data_quality": {
            "signal_coverage": coverage,
            "artifact_ratio": artifact,
            "band": "ok" if band != "insufficient_data" else "insufficient_data",
        },
        "algorithm_version": "risk-v1.0.0",
    }


def _ruleset(*rules: Rule) -> RuleSet:
    return RuleSet(rules=list(rules), quiet_hours=QuietHours(enabled=False))


def _rule(rid, severity, when=None, actions=("ACTION_ORAL_CARE",), priority=0) -> Rule:
    return Rule(
        id=rid,
        severity=severity,
        when=when or {"n_events": {"gte": 0}},
        title=f"title {rid}",
        actions=list(actions),
        priority=priority,
    )


# ------------------------------------------------------------------- caps
def test_at_most_one_attention_and_two_advisory_per_session():
    rules = [_rule(f"a{i}", "attention", priority=i) for i in range(4)]
    rules += [_rule(f"b{i}", "advisory", priority=i) for i in range(5)]
    fired, summary = evaluate("SUBJ-1", _features(), _risk(), _ruleset(*rules))
    assert sum(1 for a in fired if a.severity == "attention") == CAPS["attention"] == 1
    assert sum(1 for a in fired if a.severity == "advisory") == CAPS["advisory"] == 2
    assert summary and "folded" in summary


def test_overflow_keeps_the_highest_priority_rules():
    rules = [
        _rule("low", "attention", priority=1),
        _rule("high", "attention", priority=99),
    ]
    fired, _ = evaluate("SUBJ-1", _features(), _risk(), _ruleset(*rules))
    assert [a.rule_id for a in fired] == ["high"]


def test_shipped_rules_stay_inside_the_caps(analysed_session):
    """The rules that actually ship must not be able to exceed the budget."""
    from sqlalchemy import select

    from somno_ing.db import AlertRow, db_session

    with db_session() as db:
        rows = db.scalars(
            select(AlertRow).where(AlertRow.session_id == analysed_session["session_id"])
        ).all()
    assert sum(1 for r in rows if r.severity == "attention") <= 1
    assert sum(1 for r in rows if r.severity == "advisory") <= 2


# ------------------------------------------------------------- actionability
def test_a_rule_without_actions_is_rejected_at_load(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "rules:\n  - id: bad\n    severity: advisory\n    title: t\n    actions: []\n"
    )
    with pytest.raises(ValueError, match="no actions"):
        RuleSet.load(path)


def test_unknown_actions_are_rejected_at_load(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "rules:\n  - id: bad\n    severity: advisory\n    title: t\n    actions: [ACTION_MAGIC]\n"
    )
    with pytest.raises(ValueError, match="unknown actions"):
        RuleSet.load(path)


def test_shipped_rules_are_all_actionable():
    ruleset = RuleSet.load()
    assert ruleset.rules
    for rule in ruleset.rules:
        assert rule.actions
        assert set(rule.actions) <= VALID_ACTIONS


# ------------------------------------------------------------------- dedup
def test_third_consecutive_night_is_downgraded_to_a_trend_note():
    key = dedup_key("SUBJ-1", "r1")
    rules = _ruleset(_rule("r1", "attention"))
    first, _ = evaluate("SUBJ-1", _features(), _risk(), rules, repeat_counts={})
    assert first[0].severity == "attention"

    repeated, _ = evaluate(
        "SUBJ-1", _features(), _risk(), rules, repeat_counts={key: REPEAT_NIGHTS_TO_DOWNGRADE - 1}
    )
    assert repeated[0].severity == "info"
    assert "consecutive nights" in repeated[0].body


def test_dedup_key_is_stable_and_scoped_to_the_subject():
    assert dedup_key("A", "r") == dedup_key("A", "r")
    assert dedup_key("A", "r") != dedup_key("B", "r")


# ------------------------------------------------------- data-quality gate
def test_insufficient_data_produces_no_alerts_at_all():
    rules = _ruleset(_rule("always", "attention"))
    fired, summary = evaluate("SUBJ-1", _features(), _risk(band="insufficient_data"), rules)
    assert fired == [] and summary is None


def test_insufficient_data_gate_holds_for_the_shipped_rules():
    fired, _ = evaluate(
        "SUBJ-1",
        _features(supine_burden=0.9, coordination_anomaly=0.9, sfi_burden=0.9),
        _risk(band="insufficient_data", coverage=0.2, artifact=0.6),
        RuleSet.load(),
    )
    assert fired == []


# ------------------------------------------------------------- quiet hours
@pytest.mark.parametrize(
    "at_utc,expect_delayed",
    [
        (datetime(2026, 7, 30, 15, 0, tzinfo=UTC), True),   # 23:00 Taipei
        (datetime(2026, 7, 30, 20, 0, tzinfo=UTC), True),   # 04:00 Taipei
        (datetime(2026, 7, 30, 2, 0, tzinfo=UTC), False),   # 10:00 Taipei
    ],
)
def test_quiet_hours_delay_but_never_suppress(at_utc, expect_delayed):
    qh = QuietHours(start="22:00", end="07:00", utc_offset_hours=8)
    out = qh.next_delivery(at_utc)
    assert (out > at_utc) is expect_delayed
    if expect_delayed:
        local = out.astimezone(UTC).hour + 8
        assert local % 24 == 7


def test_quiet_hours_can_be_disabled():
    at = datetime(2026, 7, 30, 20, 0, tzinfo=UTC)
    assert QuietHours(enabled=False).next_delivery(at) == at


# ------------------------------------------------------------------- rules
def test_condition_operators_gate_correctly():
    rule = _rule("r", "advisory", when={"supine_burden": {"gte": 0.6}})
    fired, _ = evaluate("S", _features(supine_burden=0.5), _risk(), _ruleset(rule))
    assert fired == []
    fired, _ = evaluate("S", _features(supine_burden=0.7), _risk(), _ruleset(rule))
    assert len(fired) == 1


def test_a_missing_context_key_never_fires_a_rule():
    rule = _rule("r", "advisory", when={"not_a_feature": {"gte": 0}})
    fired, _ = evaluate("S", _features(), _risk(), _ruleset(rule))
    assert fired == []


def test_body_templates_substitute_context_values():
    rule = Rule(
        id="r",
        severity="advisory",
        when={"supine_burden": {"gte": 0.5}},
        title="t",
        body="about {supine_burden_pct}% supine",
        actions=["ACTION_LATERAL"],
    )
    fired, _ = evaluate("S", _features(supine_burden=0.72), _risk(), _ruleset(rule))
    assert fired[0].body == "about 72% supine"


def test_context_exposes_dotted_quality_keys():
    ctx = build_context(_features(), _risk(coverage=0.81))
    assert ctx["data_quality.signal_coverage"] == 0.81
    assert ctx["risk.band"] == "moderate"


def test_no_shipped_rule_uses_diagnostic_language():
    """PRD 2.1 R3 applies to rule text as much as to the UI."""
    banned = ("diagnos", "aspiration risk", "pneumonia", "confirmed aspiration")
    for rule in RuleSet.load().rules:
        text = f"{rule.title} {rule.body}".lower()
        for word in banned:
            assert word not in text, f"rule {rule.id} uses {word!r}"
