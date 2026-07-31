# The three constraints, and what they cost

PRD section 2 is the source of most of the architecture in this repository. This
document records what each red line actually changed, so that a future
contributor who finds one of these decisions inconvenient can see what they
would be trading away.

---

## R1 — no real-time patient monitoring

**What it means in code.** Analysis runs in a Celery task, triggered by session
close, never by chunk arrival. `somno_ing.pipeline.analyze` has no path that can
be invoked from the ingest hot loop. Alerts carry a `deliver_after` timestamp
that respects quiet hours; none of them can be marked urgent, because there is
no urgent severity.

**What it cost.**

- Stage 1 of detection still runs during ingest, but only to reduce data. It
  produces no decisions. That means an eight-hour night is analysed in one pass
  at close rather than incrementally, which is slower to first result and
  simpler to reason about.
- STATION's bed grid has three status lights and no red one
  (`somno_ing/api/beds.py`). A red light on a ward display reads as "go now",
  and a system that says "go now" is an active patient monitor.
- The nurse-call integration is a mock that always returns
  `delivered: false`. Wiring it to a real system would cross the line, and the
  interface exists only so the shape can be reviewed.

**What would change if this were relaxed.** IEC 60601-1-8 alarm-system
conformance, in full, plus the loss of the MDDS positioning. That is a different
product, not a configuration flag.

---

## R2 — no automatic electrical stimulation, no closed loop

**What it means in code.** PAM has three modes and `autonomous` is not one of
them. `MattressController.set_mode` raises on it by name, with the PRD reference
in the message, so the omission cannot be mistaken for something unimplemented.
There is no code path anywhere from a detection to a motion; `propose()` records
a suggestion and returns, and only `confirm()` — which takes an `actor_id` —
submits a command.

**What it cost.** The system cannot respond to anything it observes overnight
without waking someone up to press a button. That is the intended trade: the
known risk of transcutaneous submental stimulation during sleep is arousal and
sleep fragmentation, and the OSA literature has been moving away from
stimulate-during-sleep for exactly that reason.

**Why positioning at all, then.** Head-of-bed elevation and lateral positioning
are the highest-evidence, lowest-risk interventions in this area. If the system
is going to have an intervention layer, that is the one worth building.

---

## R3 — research use only, no diagnostic output

**What it means in code.**

- `NightlyRisk.score` is called the *overnight swallowing signal index*
  everywhere it appears. The schema says so, the API description says so, and
  the UI string is `index.name`.
- Every screen renders `RuoFooter`. It is a footer, not a dismissible banner,
  because a notice a user can close is a notice that is usually closed.
- `packages/web-shared/scripts/lint-terms.mjs` runs as the `prebuild` step of
  both frontends and fails the build on diagnostic vocabulary in either
  language. It has its own tests.
- The research-use notice is the one string allowed to contain the banned words,
  and the lint checks that those strings still read as disclaimers — so a notice
  cannot be quietly edited into an assertion while keeping its exemption.
- `test_no_shipped_rule_uses_diagnostic_language` applies the same vocabulary
  rule to the alert rules, which are the other place user-visible text is
  authored.

**What it cost.** Some wording is more laboured than it would otherwise be.
"Swallow-breathing timing pattern outside the reference range" is a worse
sentence than the one a clinician would say out loud. It is also the only one
this system is entitled to.

---

## Alert fatigue (PRD 2.3) — a constraint, not a preference

ICU telemetry runs at 80–99% non-actionable alarms, and a nurse can be exposed
to several hundred a day. An alerting system that does not aggressively suppress
itself is worse than no alerting system, because it trains people to ignore it.

Enforced in `somno_ing/alerts`, with tests:

| Rule | Where | Test |
|---|---|---|
| ≤ 1 attention + 2 advisory per session, overflow folded into a summary | `CAPS` in `alerts/__init__.py` | `test_at_most_one_attention_and_two_advisory_per_session` |
| Every alert carries ≥ 1 action | validated at rule load, not at fire time | `test_a_rule_without_actions_is_rejected_at_load` |
| Third consecutive night → downgraded to a trend note | `REPEAT_NIGHTS_TO_DOWNGRADE` | `test_third_consecutive_night_is_downgraded_to_a_trend_note` |
| Quiet hours delay, never suppress | `QuietHours.next_delivery` | `test_quiet_hours_delay_but_never_suppress` |
| `insufficient_data` produces nothing at all | first check in `evaluate()` | `test_insufficient_data_produces_no_alerts_at_all` |

The dismissal reason is mandatory (`POST /v1/alerts/{id}/dismiss`) and stored.
It is the only direct measurement of false-positive rate a research deployment
gets, and the fatigue budget above is only as good as that number.
