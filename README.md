# SomnoSwallow

Research prototype for monitoring nocturnal swallowing: a synthetic device, an
overnight analysis service, two dashboards, and a positioning-assist mattress
controller.

> **Research use only.** Nothing here is a diagnosis, and nothing here may be
> used as the basis for a clinical or treatment decision. See
> [docs/regulatory.md](docs/regulatory.md) for what that constraint changed in
> the design.

---

## What is here

| Package | Subsystem | What it does |
|---|---|---|
| `packages/sim` | **SIM** | Generates a physiologically parameterised night of synthetic acoustic / IMU / sEMG signal, plus the ground-truth event list that everything else is scored against |
| `packages/ing` | **ING** | Ingests chunks, detects swallows in four stages, computes features, scores the overnight signal index, raises alerts |
| `packages/care-web` | **CARE** | Caregiver dashboard, mobile first |
| `packages/station-web` | **STATION** | Nursing-station dashboard, desktop and wall display |
| `packages/pam` | **PAM** | Positioning-assist mattress controller: head-of-bed and lateral tilt, suggest-and-confirm only |
| `packages/shared-schemas` | — | JSON Schema as the single source of truth, with generated Python and TypeScript types |

SIM comes first on purpose. It is both the development data source and the
acceptance standard: without a known answer, "the detector works" is not a
claim anyone can check.

---

## Quick start

```bash
make install       # Python packages + frontend dependencies
make demo          # SIM -> ING -> risk -> alerts -> dashboards -> PAM, all checks
```

`make demo` needs no database, broker, object store or browser. It runs the real
ingest and analysis code against SQLite and the local filesystem, then prints
every acceptance check from PRD section 12 with a pass or fail.

The whole stack, the way it is meant to run:

```bash
make up            # postgres/timescale, redis, mosquitto, minio, ING, PAM, both frontends
make sim-docker    # push a synthetic night through MQTT into the running stack
make demo-docker   # the same walkthrough against the live services
```

- CARE  http://localhost:5173
- STATION  http://localhost:5174
- ING API and OpenAPI docs  http://localhost:8000/docs
- PAM API  http://localhost:8100/docs

---

## Everyday commands

```bash
make test              # every suite: SIM, ING, PAM, frontend
make test-fast         # skips the slow full-pipeline scenarios
make bench             # detection metrics for all five scenarios vs ground truth
make sim               # write one night to ./out
make lint-terms        # forbidden clinical terminology in UI copy
make schemas           # regenerate types from the JSON Schemas
make schemas-check     # fail if generated types have drifted
```

Detection performance, any time:

```bash
somno-ing bench --duration-min 180
```

```
elderly_high_risk    F1=1.000 P=1.000 R=1.000 gt=  32 det=  32 band=moderate
healthy_adult        F1=0.987 P=1.000 R=0.975 gt=  40 det=  39 band=low
noisy_signal         F1=0.949 P=1.000 R=0.903 gt=  62 det=  56 band=low
post_stroke          F1=1.000 P=1.000 R=1.000 gt=  17 det=  17 band=elevated
sensor_failure       F1=1.000 P=1.000 R=1.000 gt=  48 det=  48 band=low
```

---

## How a night flows through the system

```
SIM (or a real patch)
  │  MQTT  somno/{device_id}/signal        int16 chunks, base64, 5 s each
  ▼
ING ingest ─── stage 1 preprocessing runs here, as chunks arrive
  │            only the 100 Hz derived series is kept (~100 MB, not ~1.4 GB)
  ▼
session closes ──► Celery batch analysis (never on a live path)
  │
  ├─ stage 2  gating       movement and speech hard-gated; snoring soft-flagged
  ├─ stage 3  candidates   acoustic / IMU / sEMG, independently
  ├─ stage 4  fusion       weighted vote, two modalities minimum
  ├─ features              SFI, coordination, supine burden, arousal coupling
  ├─ index                 four weighted components, or insufficient_data
  └─ alerts                at most 1 attention + 2 advisory, every one actionable
       │
       ├──► CARE      status sentence + today's suggestions
       ├──► STATION   bed grid, shift handover, alert queue, research views
       └──► PAM       a suggestion; a person confirms; only then does a bed move
```

---

## Documentation

- [docs/architecture.md](docs/architecture.md) — how the pieces fit, and why
- [docs/detection.md](docs/detection.md) — the four-stage pipeline in detail
- [docs/regulatory.md](docs/regulatory.md) — the three constraints and what they cost
- [docs/open-questions.md](docs/open-questions.md) — decisions still outstanding, including two places this implementation had to reconcile conflicting requirements
- [docs/operations.md](docs/operations.md) — running, configuring, and retuning

---

## Repository layout

```
somnoswallow/
├── docker-compose.yml
├── Makefile
├── scripts/demo.py                 end-to-end walkthrough and CI gate
├── infra/                          Dockerfiles, mosquitto, nginx
├── packages/
│   ├── shared-schemas/             JSON Schema + generated types
│   ├── sim/                        SIM
│   ├── ing/                        ING
│   ├── pam/                        PAM
│   ├── web-shared/                 shared UI, API client, i18n, terminology lint
│   ├── care-web/                   CARE
│   └── station-web/                STATION
└── docs/
```
