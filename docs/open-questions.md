# Open questions and reconciled conflicts

Two kinds of entry here. **OQ** items are the PRD's own open questions, with
whatever this implementation assumed in the meantime. **RC** items are places
where two PRD requirements could not both be satisfied and the implementation
had to pick — those are the ones worth reading first, because someone will
eventually find the resulting code and wonder why it is like that.

---

## RC-1 — the healthy_adult swallow count and the per-stage rates disagree

**The conflict.** PRD 5.1.3 gives per-stage swallow rates from the literature:
N1 7.2/hr, N2 2.0/hr, N3 0.2/hr, REM 2.7/hr. Applied to the default healthy
sleep architecture over eight hours, those integrate to roughly **17 swallows a
night**. PRD 5.3 then requires the `healthy_adult` scenario to produce
**60–140**. Nothing can satisfy both.

**What was done.** The literature rates are kept verbatim as the code defaults
in `SwallowConfig` (`packages/sim/somno_sim/config.py`), so the provenance stays
visible. A single explicit multiplier, `rate_scale`, reconciles the shape with
the count target; `healthy_adult.yaml` sets it to 6.0 and documents why in place.
Across 30 seeds this yields 80–128 swallows, comfortably inside the acceptance
band, while preserving the relative per-stage distribution the literature
describes.

**What needs deciding.** Which of the two numbers is the real requirement. If
the per-stage rates are right, the acceptance band should move. If the band is
right, the per-stage rates are being cited for something they do not measure.
Someone with access to the source papers should settle it; the multiplier is a
placeholder, not an answer.

**Second-order note.** The literature standard deviations (N1 ±3.5, N2 ±0.7,
REM ±2.2) are *between-subject*. Drawing a named scenario's nightly rate from
them swings the whole-night total by roughly ±70, which no fixed band could
contain. Scenarios therefore use within-subject spread, and the between-subject
figures remain the code defaults.

---

## RC-2 — "8 hours at speed 60 in under 3 minutes"

**The conflict.** PRD 10.1 asks for an eight-hour night at `--speed 60` in under
three minutes. But `--speed 60` *means* sixty times faster than real time, so
eight hours takes eight minutes by definition.

**What was done.** `--speed 0` was added, meaning no pacing at all — generate as
fast as the machine allows. That is the mode the performance target is measured
in, and a full 480-minute night at 16 kHz / 2 kHz / 100 Hz completes in **129
seconds**, inside the three-minute budget. `--speed 60` still does what it says
and still takes eight minutes, which is the point of a pacing factor.

---

## RC-3 — snoring as a hard gate would silence the target population

**The conflict.** PRD 6.2 stage 2 says gated segments do not participate in
detection, and lists snoring as one of the things to gate. PRD 6.4 says a night
with `artifact_ratio > 0.4` yields no score and no alerts.

Put together: a supine snorer — who snores through perhaps 70% of the night —
has 70% of their recording gated, trips the quality rule, and receives nothing.
That is exactly the person the system exists for.

**What was done.** Gating is split. Movement, speech and dead channels are
**hard gates**: the signal is unusable, those windows are excluded, and the time
counts towards `artifact_ratio`. Snoring is a **soft flag**: snore energy lives
at 60–300 Hz and the swallow burst at 300–3000 Hz, so the two separate cleanly
in the band split, and snoring windows keep participating in detection at a
raised threshold (`acoustic_k_snoring`). Snore ratio is reported separately and
does not feed the quality gate. The reasoning is in
`packages/ing/somno_ing/detect/gating.py`.

---

## OQ-1 — where do the reference ranges come from?

The four index components are min-max normalised against ranges in
`packages/ing/somno_ing/config/risk.yaml`. Those are literature-derived guesses,
not validated ranges from this system's own cohort, and the file says so.

`algorithm_version` exists precisely for this: changing a range or a weight
requires bumping it, and historical `NightlyRisk` rows are never recomputed
under a new version. The decision the PRD flags — ship on literature values, or
wait for a first cohort — can therefore be deferred without corrupting anything
already recorded.

---

## OQ-2 — build the mattress or integrate an existing bed?

Unresolved, and deliberately so. `MattressDriver` is a five-method protocol;
`MockMattressDriver` implements it in software with real ramp timing so the
safety requirements are testable. A `BLEMattressDriver` or `ModbusMattressDriver`
implements the same protocol and nothing above it changes. Both paths remain
open; the question is whether a chosen bed vendor exposes a control interface at
all.

---

## OQ-3 — is sEMG in the v1 hardware?

Software-side, this is already answered: SIM synthesises the channel, ING uses
it as one of three votes, and fusion **re-normalises over whichever modalities
are actually available at that instant**. The `sensor_failure` scenario detaches
the electrode four hours in, and detection continues on acoustic plus IMU with
no threshold penalty (`test_sensor_failure_night_still_detects_after_the_electrode_drops`).

So the hardware decision does not block software, and it does not silently
degrade the system if the answer is no.

---

## OQ-4 — how do alerts reach people?

v1 delivers in-app only. `deliver_after` is computed and stored, so a push, SMS
or LINE transport would consume it rather than reimplement quiet hours. Given
the Taiwanese long-term-care setting, LINE is the likely first addition;
`somno_ing/integrations/` is where it would go, alongside the existing mocks.

---

## OQ-5 — retention and cross-institution sharing

Legal and IRB, not engineering. What the code commits to today:

- subjects are pseudonymous codes; no name, identifier or date of birth is ever
  written to the main database;
- raw waveform retention is opt-in (`STORE_RAW`, default off) and time-bounded
  (`RAW_RETENTION_DAYS`, default 90);
- derived series and analysis results have no automatic expiry;
- the audit log is append-only and hash-chained, so a deletion anywhere in it is
  detectable by replay.

---

## Known limitations

Worth stating plainly, since a prototype that overstates itself is the failure
mode this whole document is trying to avoid.

- **Detection has only ever been scored against synthetic signal.** F1 near 1.0
  on SIM output means the detector inverts the generator, not that it works on a
  human neck. The first real recording should be expected to be much worse.
- **Coordination-pattern recovery runs at 0.62–0.77 accuracy** against ground
  truth (chance is 0.25). It is the weakest link in the chain, and it feeds a
  component worth 30% of the index. The residual error is mostly apnea-end
  estimation on the respiration proxy.
- **Respiration is inferred from a single IMU axis.** There is no airflow or
  effort channel. It is enough to recover phase; it is not a respiratory
  measurement.
- **The auth scheme is a token table in a source file.** It is a placeholder for
  a real identity provider and is marked as such in `api/deps.py`.
- **`insufficient_data` is a two-threshold rule** on coverage and artifact
  ratio. It has no notion of *which* modality was lost, only how much time was
  unusable.
