# Operations

## Configuration

Every service reads its configuration from the environment at first use — not at
import time, which is a distinction that matters if an entrypoint script exports
credentials before starting the process.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/somno.db` | Postgres/Timescale under compose |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker and result backend |
| `MQTT_URL` | `mqtt://localhost:1883` | ingest subscribes to `somno/+/signal` |
| `S3_ENDPOINT` | unset | unset means local filesystem object storage |
| `LOCAL_STORAGE_DIR` | `./data/objects` | used when `S3_ENDPOINT` is unset |
| `STORE_RAW` | `false` | raw waveform is ~1.4 GB per night |
| `RAW_RETENTION_DAYS` | `90` | PRD 10.2 |
| `API_AUTH_REQUIRED` | `true` | `false` only for local runs and tests |
| `DEV_API_TOKEN` | `dev-token` | placeholder for a real identity provider |
| `CELERY_TASK_ALWAYS_EAGER` | `false` | runs analysis inline; used by demo and tests |
| `PAM_NOTIFY_SECONDS` | `30` | PAM-S4 pre-motion notice |
| `PAM_MIN_INTERVAL_S` | `1200` | PAM-S6 minimum spacing between motions |

Algorithm behaviour is in three YAML files, not in code:

- `packages/ing/somno_ing/config/detector.yaml` — gating, candidate and fusion thresholds
- `packages/ing/somno_ing/config/risk.yaml` — component reference ranges and weights
- `packages/ing/somno_ing/config/alert_rules.yaml` — rules, actions, quiet hours

## Retuning

**Detection.** Edit `detector.yaml`, bump `DETECTOR_VERSION` in
`detect/rule_based.py`, then re-measure:

```bash
somno-ing bench --duration-min 180 --out out/bench.json
```

**Index.** Edit `risk.yaml` and bump `algorithm_version` in the same file.
Historical `NightlyRisk` rows are never recomputed under a new version — that is
what makes the version field load-bearing rather than decorative.

**Alerts.** Edit `alert_rules.yaml`. Rules are validated at load: a rule with no
actions, an unknown action, or an unknown severity raises rather than silently
producing an un-actionable alert.

## Roles

`caregiver`, `nurse`, `researcher`, `admin`. Researcher-only endpoints are the
ones that expose raw-adjacent data: `/v1/eval/detection`, `/v1/sessions/{id}/signal`,
`/v1/sessions/{id}/export/edf`, and the integration previews.

The token table in `api/deps.py` is a prototype placeholder. It is not a security
boundary and should not be treated as one outside a research sandbox.

## Running a night

Locally, no infrastructure:

```bash
somno-ing simulate --scenario elderly_high_risk --duration-min 180
```

Into a running stack, over MQTT:

```bash
SIM_SCENARIO=post_stroke SIM_DURATION_MIN=480 make sim-docker
```

Writing files instead of publishing:

```bash
somno-sim run --scenario healthy_adult --seed 42 --speed 0 \
  --out out/session --export-edf
```

`--speed` is a pacing factor: `1` is real time, `60` is sixty times faster,
`0` is as fast as the machine allows. A full eight-hour night at `--speed 0`
takes about 129 seconds.

## Offline import

`POST /v1/sessions/{id}/upload` accepts the newline-delimited chunk envelopes
that `somno-sim run --mqtt file:PATH` produces, standing in for a microSD import.
It goes through the same ingest and analysis path as streamed data — there is no
second code path to keep in sync.

## Data gaps

Chunks carry a sequence number. A gap is recorded on `Session.gaps` and reduces
`signal_coverage`, which feeds the `insufficient_data` rule. Coverage below 0.6
or artifact above 0.4 means no score and no alerts.

## Audit

Append-only and hash-chained. `GET /v1/audit` replays the chain and reports
whether it is intact and, if not, the first entry that fails. Nothing in the
codebase updates or deletes rows in that table.

## Troubleshooting

**No sessions appear after running SIM.** Check `docker compose logs ing-consumer`.
The consumer opens a session on the `session_start` control message; if only
signal chunks arrived it opens one implicitly rather than dropping data, but the
subject code will be `SUBJ-UNKNOWN`.

**A session sits in `analyzing`.** The Celery worker is not running or cannot
reach Redis. `docker compose logs ing-worker`.

**Every alert is `insufficient_data`.** Look at `signal_coverage` first (delivery
gaps), then `artifact_ratio` (movement and speech gating). Snoring does not count
towards either — see [open-questions.md RC-3](open-questions.md).

**The frontend build fails on wording.** That is the terminology lint doing its
job. Describe the signal and the action, not a clinical conclusion.
