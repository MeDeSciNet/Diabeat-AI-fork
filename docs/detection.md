# Detection pipeline

Four stages, each independently testable, behind one interface. Thresholds live
in `packages/ing/somno_ing/config/detector.yaml`; changing any of them requires
bumping `DETECTOR_VERSION`.

```
full-rate chunks ──► stage 1  preprocess   (during ingest, per chunk, stateful)
                        │
                        ▼  100 Hz derived series
session close ─────► stage 2  gating       (whole night)
                     stage 3  candidates   (per modality, independently)
                     stage 4  fusion       (weighted vote)
                        │
                        ▼  DetectedEvent[]
```

`SwallowDetector` (`detect/base.py`) is the seam the PRD asks for: two methods,
`process_chunk` and `finalize`. `RuleBasedDetector` implements it today; a
future `MLDetector` implements the same two methods and nothing upstream or
downstream changes.

---

## Stage 1 — preprocessing

Runs **during ingest**, chunk by chunk, with filter state carried across chunk
boundaries. Carrying state matters: a fresh filter per chunk puts a transient at
every boundary, and those transients are indistinguishable from short bursts.

| Channel | Processing | Output at 100 Hz |
|---|---|---|
| Acoustic 16 kHz | band-pass 300–3000 Hz, block RMS | `acoustic_env` |
| Acoustic 16 kHz | band-pass 60–300 Hz, block RMS | `snore_env` |
| sEMG 2 kHz | 50 Hz notch, band-pass 20–450 Hz, block RMS | `semg_env` |
| IMU 100 Hz | gravity via 0.3 Hz low-pass | `gx`, `gy`, `gz` |
| IMU 100 Hz | S-I axis minus gravity, 20 Hz low-pass | `imu_si` |
| IMU 100 Hz | dynamic acceleration magnitude | `imu_dyn` |
| IMU 100 Hz | A-P axis, stored raw | `resp_volume` |

**Why the whole night is reduced to 100 Hz.** An eight-hour recording is roughly
1.4 GB of raw waveform and about 100 MB of derived series. Nothing after stage 1
needs more than 10 ms of timing resolution, so raw retention is opt-in
(`STORE_RAW`, default off) and the derived series is what gets stored.

**Why the swallow band starts at 300 Hz.** Snoring energy is concentrated at
60–300 Hz. Splitting there means snoring can be *measured* without being
*gated*, which is what makes the soft-flag treatment in stage 2 possible.

**Respiration is filtered later, not here.** A causal 0.1–0.6 Hz Butterworth has
about **0.95 s of group delay** at a normal breathing rate — close to a quarter
of a breath. Measuring respiratory phase through that filter made the
coordination pattern barely better than a guess (0.31–0.62 accuracy against
ground truth). `finalize_resp()` band-passes the whole night zero-phase once the
session closes, which lifted the same measurement to 0.62–0.77. The raw axis is
what stage 1 stores.

**Wavelet denoising** is applied to the 100 Hz envelope rather than the 16 kHz
raw signal (`wavelet_denoise`). It costs 160× less, removes the chunk-boundary
problem entirely, and targets the signal the detector actually thresholds.
Denoising raw audio would only be worth it if a later stage looked at spectral
shape *within* a burst; none does.

---

## Stage 2 — gating

Two classes of interference, treated differently.

**Hard gates** — the window is unusable, is excluded from detection, and counts
towards `artifact_ratio`:

- *Movement*: mean dynamic acceleration over a 1.5 s window above 0.08 g.
  The window mean, not the peak, is the discriminator. Hyoid elevation puts
  about 0.05 g on the S-I axis, which is the same order as gentle repositioning;
  what differs is duration. An earlier peak-based version deleted 25% of true
  events while reporting only 1.6% of the night as artifact — the failure was
  invisible in the artifact statistic and only showed up in recall.
- *Speech*: sustained 3–6 Hz envelope modulation relative to the local envelope
  level, over a window several syllables long. A swallow puts a single transient
  into the same band; speech puts a train of them.
- *Dead channel*: reported by the device's own electrode-off detection.

**Soft flag** — the window stays in play at a raised threshold:

- *Snoring*: snore-band to swallow-band energy ratio over 20 s. See
  [open-questions.md RC-3](open-questions.md) for why hard-gating this would
  silence the population the system is for.

---

## Stage 3 — candidates

Each modality decides on its own, knowing nothing about the others. That
independence is what makes the stage-4 vote worth anything. All three score
against a rolling median/MAD baseline rather than a fixed threshold, because the
noise floor drifts across a night with posture, sweat and electrode settling.

| Modality | Method | Threshold |
|---|---|---|
| Acoustic | robust z-score of the denoised envelope | `acoustic_k` 5.0, 7.5 inside snoring |
| IMU | normalised cross-correlation against a biphasic hyoid-excursion template | `imu_ncc` 0.50 |
| sEMG | robust z-score sustained above threshold for >150 ms | `semg_k` 4.0 |

---

## Stage 4 — fusion

Candidates within ±300 ms cluster into one event. Confidence is the weighted sum
of per-modality scores (acoustic 0.4, IMU 0.3, sEMG 0.3), **normalised over the
modalities actually available at that instant**.

Two structural rules:

1. **A single modality never carries an event while a second is available**
   (`min_modalities: 2`). This is what keeps snoring — acoustic only — and a
   restless sleeper — IMU only — out of the event list.
2. **Weights re-normalise over available modalities.** A night that loses the
   sEMG electrode is judged on the two channels it still has, instead of
   silently failing every confidence check for the rest of the recording. The
   `sensor_failure` scenario tests exactly this.

---

## Measuring it

`GET /v1/eval/detection?session_id=...` scores detected events against SIM
ground truth: precision, recall, F1, onset error distribution, per-stage recall,
and coordination-pattern accuracy. Matching is greedy nearest-first on event
centres within a ±750 ms tolerance.

```bash
somno-ing bench --duration-min 180
```

Current results, seed 42:

| Scenario | F1 | Precision | Recall | Coordination | Band |
|---|---|---|---|---|---|
| healthy_adult | 0.987 | 1.000 | 0.975 | 0.69 | low |
| elderly_high_risk | 1.000 | 1.000 | 1.000 | 0.62 | moderate |
| post_stroke | 1.000 | 1.000 | 1.000 | 0.71 | elevated |
| noisy_signal | 0.949 | 1.000 | 0.903 | 0.66 | low |
| sensor_failure | 1.000 | 1.000 | 1.000 | 0.77 | low |

Milestone targets are F1 ≥ 0.85 on `healthy_adult` and ≥ 0.70 on
`noisy_signal`; both are asserted in `test_f1_meets_the_milestone_target`.

**Read these numbers correctly.** They say the detector inverts the generator.
They do not say anything about a human neck, and the first real recording should
be expected to be substantially worse. That is the honest limit of what a
synthetic ground truth can establish.
