# Handoff

Written 2026-07-31, at the point where the prototype and the pitch artifact are
both finished and pushed. Everything needed to pick this up in another
environment is either in this file or linked from it.

Branch: `claude/somnoswallow-prototype-8dxq6m`.

---

## 1. What exists

Two deliverables, both in this repository.

**The prototype** — a working monorepo built from the PRD: five subsystems, all
tests passing, `make demo` runs the whole pipeline end to end with no database,
broker, object store or browser. Structure and commands are in the
[README](../README.md); the design reasoning is in
[architecture.md](architecture.md) and [detection.md](detection.md).

**The pitch artifact** — `pitch/somnoswallow-demo.html`, a single self-contained
page with four animated models and almost no prose. See
[pitch/README.md](../pitch/README.md). Published at
<https://claude.ai/code/artifact/8b704163-01ae-4bc9-905a-66abfb335774>.

### State

- Working tree clean, everything committed and pushed.
- `make test` green: 11 test modules across SIM / ING / PAM, plus the frontend
  suite and the terminology lint.
- `make demo` prints every PRD §12 acceptance check with a pass.
- `somno-ing bench` F1 0.949–1.000 across all five scenarios.
- Pitch page verified with `node pitch/smoke.mjs`: no console errors, no
  horizontal overflow, both themes, mobile, every interaction.

### The one number that must not be over-read

Detection has **only ever been scored against synthetic signal**. F1 near 1.0 on
SIM output means the detector inverts the generator — nothing more. The first
real recording should be expected to be much worse. Everything in
[open-questions.md § Known limitations](open-questions.md) is worth re-reading
before quoting any figure from this repo.

---

## 2. The constraints that shaped everything

Three of them, from PRD §2.1, and they are not decoration — they removed
features that would otherwise be obvious. [regulatory.md](regulatory.md) has the
full accounting.

- **R1 — no real-time life-safety alerting.** Analysis is batch, after the
  session closes. There is no live path from signal to alarm anywhere in the
  code, and adding one is a regulatory decision, not an engineering one.
- **R2 — no closed-loop stimulation.** PAM suggests; a person confirms; only
  then does a bed move. There is no `autonomous` mode in the state machine.
- **R3 — research use only.** No output is a diagnosis. `make lint-terms` fails
  the build on 診斷 / 確診 / 吸入性肺炎風險 and friends in UI copy, with a small
  allowlist for the RUO notices themselves.

Plus the alert-fatigue budget from PRD §2.3: at most 1 attention + 2 advisory
per session, every alert carries at least one action, three consecutive nights
downgrades, quiet hours are honoured, and `insufficient_data` produces no alerts
at all.

Three places where the PRD contradicted itself are reconciled and documented as
RC-1 / RC-2 / RC-3 in [open-questions.md](open-questions.md). Read those first
if any of the code looks arbitrary.

---

## 3. The pitch argument, and where it landed

This took several passes and the final position is not the obvious one.

**The temptation is to sell 即時警報.** It does not survive contact with the
physiology or the regulation. The honest split is by timescale:

| Timescale | Example | What the system does |
|---|---|---|
| 秒 | a single mis-timed swallow | **nothing.** A 2 a.m. alarm cannot un-aspirate, and waking someone fragments sleep, which makes swallowing worse. |
| 分～小時 | two hours supine, no swallow in 87 minutes | **should act overnight** — reposition, prompt. This is the real intervention window. |
| 一整夜 | the night's pattern | **reports.** Trend, index, tomorrow's suggestions. |

So 即時 belongs on the *sensing* (every swallow, all night, at 10 ms
resolution), and 能救命 belongs on the *problem* (aspiration pneumonia is
cumulative over days and weeks — which is exactly why a nightly picture is
worth having), not on the device as an alarm.

**The strongest single idea is model 02: PSG co-registration.** Not a standalone
device asking a hospital to adopt something new — an extra channel on a PSG rig
they already run, that reclassifies data they already have. Some desaturations
currently scored as respiratory events may not be respiratory events. That
reframing is cheap to trial, and it is the thing an audience actually reacts to.

**The claim boundary, stated on the page itself**, in three tiers:

- *現在做得到* — per-swallow timing, swallow rate by sleep stage, longest
  swallow-free interval, whether a swallow lands on inspiration or expiration,
  and the temporal relationship to apnea / arousal / cough.
- *研究要驗證* — whether older adults show a repeatable nocturnal swallowing
  abnormality; whether long swallow-free intervals relate to residue and snore
  change; whether any of it correlates with silent aspiration risk.
- *還不能說* — that saliva entered the airway, that silent aspiration occurred,
  that pneumonia will follow.

Keep that third column. It is what makes the first two credible.

---

## 4. Known gap, not yet built

The 分～小時 tier above is **only in the demo, not in the code.** `somno_ing`
runs its analysis once, at session close. "Detected two hours supine with no
swallow → prompt a reposition, tonight" does not exist in `somno_ing`; PAM has
scheduled turning and device telemetry, and that is all.

This is the most valuable next piece of work, and it is compatible with R1 — a
sustained-state prompt about posture is not a life-safety alarm about an event.
It would need:

- a periodic (not per-event) evaluation pass during an open session;
- a state feature over a rolling window — supine duration, swallow-free
  interval — rather than a whole-night aggregate;
- routing into the existing PAM suggest-and-confirm flow, so nothing moves
  without a person;
- its own alert-budget accounting, since the §2.3 caps are per session and this
  would spend from them.

Everything else outstanding is in [open-questions.md](open-questions.md):
reference ranges (OQ-1), build-vs-integrate for the mattress (OQ-2), sEMG in v1
hardware (OQ-3), alert transport — LINE is the likely first one (OQ-4), and
retention / cross-institution sharing (OQ-5).

---

## 5. Picking this up elsewhere

```bash
git clone <repo> && git checkout claude/somnoswallow-prototype-8dxq6m
make install
make demo          # no infrastructure needed; this is the fastest proof it works
make test
```

Two environment-specific things that will not transfer:

- **`pitch/smoke.mjs` and `pitch/shots4.mjs` hard-code**
  `executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'`,
  because this container ships that build and the installed playwright expects a
  different one. Elsewhere, delete the option.
- **The artifact URL** can only be updated in place by a conversation that
  either published it or is given the URL explicitly. Otherwise republishing
  mints a new link.

If the schemas change, `make schemas` regenerates both the Pydantic and the
TypeScript types and `make schemas-check` fails the build on drift — they are
generated, never hand-edited.
