# Training Intelligence Service --- Feature Implementation Guide

**Purpose:** Turn the product recommendations into implementable work
packages for Codex.\
**Target:** Existing Python service deployed to the user's
Kubernetes/K3s cluster with Helm.

Implement incrementally. Read existing code and tests before modifying
anything. Preserve working behaviour, add tests with each vertical
slice, and do not deploy automatically to the live cluster.

## 1. Target architecture

Keep Flask, Prometheus and Helm. Add durable storage and explicit
sync/analysis workflows.

``` text
Garmin API / Garth                 Intervals.icu API
       |                                  |
       +----------------+-----------------+
                        |
                 Sync orchestrator
          (incremental, retryable, idempotent)
                        |
                Normalisation layer
                        |
               Persistent local store
                 (SQLite + PVC initially)
                        |
                Feature calculations
             +----------+-----------+
             |                      |
       Training analytics      Recovery analytics
             |                      |
             +----------+-----------+
                        |
                Interpretation layer
             (rules, confidence, reasons)
                        |
           +------------+-------------+
           |            |             |
         REST API   Prometheus    Weekly report
```

### Deployment shape

-   Keep one long-running API Deployment.
-   Initially run scheduled sync as Helm-managed Kubernetes CronJobs,
    rather than an in-process scheduler that can run twice when web
    workers/replicas multiply.
-   CronJobs can invoke a CLI command or authenticated internal sync
    endpoint.
-   Use SQLite on a PVC for a single-instance, single-writer deployment.
    Migrate to PostgreSQL if concurrent writers, replicas or query
    complexity justify it.
-   Prometheus remains for current-state gauges, counters and service
    health; it is not the canonical activity database.
-   Store Garmin/Intervals credentials and tokens in Kubernetes Secrets
    or the existing external-secrets mechanism.
-   Prefer no Kubernetes API access for the CronJob if it only needs to
    call the service.

## 2. Work package A --- Runtime and configuration hardening

### A1. Typed configuration

Create a validated configuration module with groups for: - Garmin
credentials and token directory. - Intervals base URL, athlete/API key
and request timeout. - Database URL/path. - Sync overlap window and
backfill limits. - Athlete timezone and sport priorities. - FTP source
and activity-specific FTP provenance. - Preferred easy-ride
duration/cohort settings. - Fatigue and durability thresholds. - Logging
and notification configuration.

Validate required settings at startup. Optional integrations should be
explicitly disableable.

### A2. Module boundaries

Gradually separate Flask route handlers from business logic. Suggested
layout:

-   `app/api/` --- Flask routes and request/response schemas.
-   `app/clients/garmin.py` --- Garmin adapter.
-   `app/clients/intervals.py` --- Intervals.icu adapter.
-   `app/storage/` --- models, migrations and repositories.
-   `app/sync/` --- orchestration, checkpoints and retries.
-   `app/analytics/` --- normalisation and feature calculations.
-   `app/analysis/` --- fatigue, durability and interpretation.
-   `app/reports/` --- daily/weekly report rendering.
-   `app/metrics/` --- Prometheus definitions/population.
-   `app/config.py` --- validated configuration.

Do not do a wholesale rewrite before tests exist. Move one boundary at a
time and retain compatibility routes during migration.

### A3. API and operations

-   Use GET only for read-only endpoints; use POST for
    sync/backfill/annotation mutations.
-   Add `/health/live` and `/health/ready`.
-   Readiness should fail when required local dependencies
    (e.g. database) are unavailable. A temporary provider outage need
    not make the API unready.
-   Add structured logs with sync run ID, source, activity ID and error
    category. Never log credentials, tokens or sensitive payloads.
-   Use request timeouts and bounded retries with exponential backoff
    and jitter.
-   Distinguish auth failures, rate limits, network failures, malformed
    payloads and permanent not-found responses.
-   Bound `weeks`, `days` and activity counts accepted by endpoints.
-   Protect mutation and diagnostic endpoints with authentication or
    network policy.
-   Replace broad silent exception handling with explicit
    service-boundary error handling and partial-progress reporting.

**Acceptance:** Existing endpoints continue working; config validation
and health endpoints work; provider failures are observable; secrets
never appear in logs.

## 3. Work package B --- Persistent canonical data model

Use SQLAlchemy + Alembic or an equivalent migration-backed approach.
SQLite on a PVC is sufficient initially.

### `activities`

Suggested fields: - `source`, `source_activity_id` (unique together). -
`activity_type`, `start_time_utc`, `local_date`, `timezone`. -
`duration_seconds`, `distance_meters`, `elevation_gain_meters`. -
`average_hr`, `max_hr`, `average_power`, `normalized_power`. -
`intensity_factor`, `ftp_at_activity`, `tss`, `cadence_average`. -
`source_updated_at`, `ingested_at`. - `raw_metadata_json`,
`normalisation_version`.

Upsert by `(source, source_activity_id)`. Do not assume IDs are globally
unique across providers.

### `activity_streams` (optional initial table)

-   Activity FK, stream type, compressed payload or storage path, sample
    interval, content hash and ingestion timestamp.
-   Retain only streams needed for planned analytics.
-   Avoid duplicate copies on every analysis run. Consider compressed
    files on PVC if SQLite blobs grow too large.

### `daily_wellness`

-   `source`, `local_date`.
-   Sleep duration and documented score, resting HR, HRV with source
    semantics/units.
-   Body Battery fields, stress average/durations, optional SpO2 if
    genuinely useful.
-   `source_updated_at`, `ingested_at`, raw payload.

Unique key `(source, local_date)`. Null means missing; never coerce
missing to zero.

### `sync_runs`

-   Run ID, source, start/finish, status
    (`running/succeeded/partial/failed`).
-   Records seen/inserted/updated.
-   Checkpoint before/after.
-   Error category and summary.

### `athlete_annotations`

-   ID, timestamp, local date, category, text, created time.
-   Categories: sleep disruption, illness, work stress, travel, strength
    training, unusual life load, subjective freshness, session note.
-   Optional and private.

### `analysis_runs`

-   ID, analysis type, algorithm version, input watermark, timestamps
    and result JSON.
-   Preserve enough information to reproduce results after algorithm
    changes.

**Acceptance:** Upserts prevent duplicates; data survives pod restart;
migrations create and upgrade databases; backfill resumes; source
snapshots are retained where useful for debugging.

## 4. Work package C --- Incremental ingestion

### C1. Intervals.icu

1.  Fetch athlete/profile metadata and FTP/threshold context.
2.  Fetch activities over a configurable overlap window (e.g. recent 14
    days) to catch edits and late uploads.
3.  Upsert activity metadata by source ID.
4.  Fetch streams only for new/updated activities, respecting rate
    limits.
5.  Parse and normalise streams.
6.  Record per-activity errors and continue the batch.
7.  Advance checkpoints only after a page/window succeeds.
8.  Periodically reconcile a larger lookback for edits/deletions.

Record FTP applicable to each activity if available. Do not silently
apply today's FTP retrospectively.

### C2. Garmin

1.  Reuse the existing Garth token/authentication flow.
2.  Fetch daily wellness data over a small overlap window.
3.  Upsert by local date and source.
4.  Track last successful date and last successful API sync.
5.  Keep missing days missing, not zero.
6.  Surface expired credentials as actionable sync errors.
7.  Preserve current Garmin metrics while transitioning to canonical
    storage.

### C3. Backfill

-   Provide a CLI for bounded date-range backfill.
-   Support dry-run and resume.
-   Rate-limit and retry transient failures.
-   Store partial progress and per-record errors.
-   Do not use Prometheus TSDB blocks as primary historical storage.
-   Recompute derived analysis after ingestion, not after every
    individual record.

### C4. Scheduling

Use Helm-managed CronJobs initially: - Garmin wellness sync daily, after
likely watch sync time; allow manual trigger. - Intervals activity sync
daily or several times daily with overlap. - Analysis after successful
ingestion and optionally nightly. - Weekly report after the main sync.

Make schedules configurable. Set `concurrencyPolicy: Forbid`, resource
limits, `activeDeadlineSeconds` and bounded Job history. Ensure a single
SQLite writer.

**Acceptance:** Idempotent/resumable sync; partial failures do not abort
unrelated records; outages do not erase data or advance invalid
checkpoints; freshness is measurable.

## 5. Work package D --- Normalisation and data quality

Normalise each activity before analytics.

-   Store UTC internally; derive athlete-local dates using configured
    timezone.
-   Distinguish moving time, elapsed time and paused time.
-   Preserve source TSS/IF/NP when valid and record whether values are
    source-provided, calculated or estimated.
-   Record activity-specific FTP where available.
-   Distinguish missing HR from zero; flag likely sensor dropouts.
-   Validate HR/power ranges and reject impossible samples without
    fabricating values.
-   Normalise zone labels and detect whether percentages are fractions
    (0--1) or percentages (0--100).
-   Keep activity types distinct. Strength training and running must not
    be treated as cycling rides.
-   Mark indoor/outdoor activity and initially compare them separately.
-   Align stream arrays by timestamp, not assumed matching indexes.
-   Calculate HR drift/decoupling only when power is sufficiently
    steady; splitting an HR series in half while power changes
    materially is not valid evidence.

Add quality flags such as `hr_missing`, `power_missing`,
`power_sensor_dropout`, `duration_ambiguous`, `ftp_unknown`,
`zones_unavailable`, `not_steady_enough_for_decoupling` and
`source_value_estimated`.

Analytics must expose which quality gates excluded an activity.

## 6. Work package E --- Fatigue Checker v2

Retain the pure-function/rule-based approach, but separate:

1.  **Data sufficiency:** Is there enough comparable data?
2.  **Observed strain:** Are comparable easy efforts more costly than
    baseline?
3.  **Interpretation:** Is the pattern persistent, and what context
    coincides with it?

Do not collapse these into one opaque label.

### E1. Eligibility matched to real training

Current defaults are mismatched: 60-minute minimum easy rides, five
total rides in seven days, two qualifying easy rides, and six rides per
IF band. The athlete normally completes 45--50 minute sessions and 3--4
rides/week.

Starting configurable defaults to validate against real data: - Easy
ride minimum around 35--40 minutes. - Duration cohorts such as 35--55,
55--80 and 80+ minutes. - Compare IF/power zone and time-in-zone,
allowing carefully defined missing-zone cases. - Do not require five
rides in every 7-day window. - Build baselines over 28--42 days, with a
minimum cohort sample count. - Ensure the evaluated period is excluded
from its own baseline. - Analyse 7- and 14-day patterns when sufficient
comparable observations exist.

These are pragmatic initial values, not universal physiological
thresholds.

### E2. Strain features

For eligible rides calculate: - Mean HR and HR at comparable
power/intensity. - HR/power relationship only above a minimum power. -
Power/HR efficiency. - HR drift/decoupling only for steady efforts. -
Duration, IF, TSS and zone distribution. - Data quality and
comparability flags.

Use robust summaries (median, MAD or trimmed mean) where appropriate.
Guard against tiny sample counts and near-zero standard deviation making
z-scores unstable.

### E3. Context

Use recent 7/14/28-day load, ride count, hard sessions, resting HR/HRV,
sleep trend, Body Battery/stress if reliable, and optional annotations.

Context can affect confidence but cannot manufacture a fatigue flag when
ride evidence does not support one.

### E4. Output contract

Return stable JSON, for example:

``` json
{
  "status": "possible_recovery_mismatch",
  "confidence": "moderate",
  "data_sufficiency": {
    "eligible": true,
    "baseline_days": 35,
    "comparable_ride_count": 5,
    "excluded_reasons": []
  },
  "observations": [
    {
      "metric": "heart_rate_at_comparable_power",
      "direction": "elevated",
      "delta": 6.2,
      "unit": "bpm",
      "sample_count": 3
    }
  ],
  "context": {
    "recent_training_load": "stable",
    "sleep_trend": "below_personal_baseline",
    "resting_hr_trend": "neutral"
  },
  "reasons": [
    "Three comparable easy rides had elevated HR at similar power",
    "Sleep duration was below the athlete's recent baseline"
  ],
  "limitations": [
    "Outdoor temperature and hydration are unavailable"
  ],
  "algorithm_version": "fatigue-v2"
}
```

Statuses: `insufficient_data`, `no_clear_mismatch`,
`possible_recovery_mismatch`, `persistent_strain_pattern`.

Do not use "ill", "overtrained" or "absorbing well" as diagnoses or
unsupported conclusions.

### E5. Test scenarios

Include: - Stable 45-minute easy sessions. - A 3--4 ride week with one
longer ride. - Repeated elevated HR at comparable power. - One anomalous
ride followed by normal rides. - Missing HR/power and sensor dropouts. -
Changed FTP, indoor/outdoor differences and non-steady rides. - Poor
sleep with no ride strain signal. - High load with normal easy-ride
response. - Insufficient baseline and long training gaps. - Zero power,
empty streams, fraction/percentage zones, duplicate dates and
daylight-saving transitions.

## 7. Work package F --- Durability analytics

This is the most important new value beyond fatigue detection.

### F1. Weekly training summary

For calendar weeks and rolling 7/28/42-day windows calculate: - Ride
count by type. - Cycling time, distance, elevation and TSS. -
Mean/median ride duration and longest ride. - Duration distribution:
`<35`, `35–55`, `55–80`, `80+` minutes. - Easy/moderate/hard ride counts
when zones are reliable. - Longest gap between rides and back-to-back
ride days. - Strength sessions separately.

Do not convert strength sessions into cycling TSS without a defensible
model.

### F2. Repeatability

Create a reference cohort (initially 35--55 minute easy cycling).
Compare: - HR at similar power/IF and duration. - Session
consistency/completion. - Time until next ride and next-ride response. -
Whether back-to-back rides become easier to absorb.

The key question is: "Is the usual 45--50 minute session becoming easier
to repeat?" Do not reduce this to a single score.

### F3. Aerobic efficiency

Calculate power-to-HR or HR-to-power only across comparable steady
rides: - Initially match indoor and outdoor separately. - Match duration
and IF/power bands. - Exclude stops, intervals and sensor gaps. - Report
median trend and sample size/uncertainty. - Require multiple
observations before claiming a meaningful trend.

### F4. HR drift/decoupling

Use aligned HR/power streams only: - Select stable segments or compare
halves only when power distribution is comparable. - Account for warm-up
and pauses. - Require minimum steady duration and acceptable power
variability. - Return `not_applicable` when conditions are unsuitable. -
Validate against hand-inspected rides.

### F5. Long-ride tolerance

Track longest ride in 28/42 days, frequency of 75--90+ minute rides,
response during the ride, time until next ride and response of the next
1--2 sessions.

Do not label a long ride "too much" solely because TSS is high. Observe
what happens afterwards.

### F6. Example progression observations

-   "You completed four rides this week, including two consecutive days,
    without a higher-than-usual HR response on the second day."
-   "Your 40--55 minute easy rides have been consistent for four weeks;
    there is not enough evidence yet to assess longer-ride durability."
-   "The longest ride increased, but the next ride was delayed by three
    days, so tolerance remains uncertain."

Avoid automatic volume-increase prescriptions.

## 8. Work package G --- Daily and weekly reports

### Daily briefing

`GET /api/v1/briefing/daily`

Return sync freshness, recent recovery context, 7/28-day training
summary, fatigue status/confidence, one or two observations, data
caveats and a cautious posture: - `normal_easy_training` -
`keep_it_easy` - `recovery_priority` - `insufficient_information`

No specific workout prescription or medical advice.

### Weekly review

`GET /api/v1/reports/weekly?week_start=YYYY-MM-DD`

Return structured JSON and Markdown/text: - Completed training and
comparison with previous weeks. - Durability observations. - Recovery
context. - Improving/stable/uncertain areas. - Watch-outs. - Suggested
emphasis: consolidate, maintain or cautiously progress.

Save reports with algorithm version and input watermark.

### Report quality

Every statement must trace to data or an annotation. Include dates,
counts and comparison windows. Explain missing/excluded data. Never
infer causation from correlation.

Do not use an LLM for calculations. If later used for prose, provide
structured analysis only, require caveats to be retained, validate
output and retain deterministic fallback text.

## 9. Work package H --- Athlete annotations

Implement: - `POST /api/v1/annotations` -
`GET /api/v1/annotations?from=...&to=...` -
`DELETE /api/v1/annotations/{id}`

Example:

``` json
{
  "date": "2026-11-08",
  "category": "sleep_disruption",
  "text": "Children woke several times; legs felt heavy."
}
```

Keep this optional and low-friction. No required daily survey or mood
scoring.

## 10. Work package I --- Prometheus and Grafana

Prometheus should expose current state and operational health, not every
raw activity.

Operational metrics: -
`training_sync_last_success_timestamp_seconds{source}` -
`training_sync_last_attempt_timestamp_seconds{source}` -
`training_sync_records_total{source,result}` -
`training_sync_errors_total{source,error_type}` -
`training_sync_duration_seconds{source}` -
`training_analysis_last_success_timestamp_seconds` -
`training_analysis_duration_seconds` -
`training_data_freshness_seconds{source}`

Current analysis gauges: - `training_rides_7d`, `training_rides_28d` -
`training_cycling_hours_7d`, `training_cycling_hours_28d` -
`training_tss_7d` - `training_longest_ride_seconds_28d` -
`training_fatigue_status` - `training_fatigue_data_sufficient` -
`training_comparable_easy_rides` - `training_aerobic_efficiency_trend`
only when valid

Use bounded labels only: source, result, error type, activity type.
Never use activity ID, date, free text or arbitrary error messages as
labels. Avoid per-activity series and unbounded cardinality.

Build a small dashboard for training frequency/time, recovery context,
comparable easy-ride response and sync/data quality. Do not recreate
every Intervals.icu panel.

## 11. Work package J --- Notifications

Start with stale/failed sync, weekly review ready and persistent
recovery mismatch. Use existing Slack integration only if wanted. Add
cooldowns, deduplication and configurable severity. No alert for one
poor night or one heavy ride. Opt-in and quiet by default.

## 12. Security and privacy

-   Secrets/tokens only in Kubernetes Secrets or external secret store.
-   Keep service private or authenticated.
-   Protect mutation endpoints and diagnostics.
-   Do not expose raw wellness records publicly.
-   Do not log raw provider payloads by default.
-   Back up SQLite PVC and test restore.
-   Set retention for raw streams/reports; support export/deletion.
-   Do not send personal wellness payloads to third-party analytics or
    LLMs by default.

## 13. Testing strategy

**Unit:** calculations, dates/timezones, zones, FTP provenance, quality
gates, fatigue/durability metrics and reports.

**Contract:** Garmin/Intervals adapters against sanitised fixtures;
validate fields, pagination and error handling.

**Integration:** migrations, upsert/idempotency, partial failure/resume,
analysis from stored records, API auth and schemas.

**End-to-end:** start with test DB and mocked providers; run sync;
verify canonical records; run analysis; verify briefing, report and
Prometheus output.

Keep existing parsing fixtures. Preserve current fatigue tests while
deliberately replacing mismatched assumptions. A feature is not complete
based only on mocked unit tests: include representative real-data
validation, keeping sensitive data local.

## 14. Codex execution plan

For each work package: 1. Read current implementation and tests. 2.
Write a short plan and list affected files. 3. Implement the smallest
vertical slice. 4. Add tests before declaring completion. 5. Run full
test suite, lint/type checks if configured, and container build. 6.
Update README and this specification when behaviour changes. 7. Report
changed files, commands, test results, limitations and manual steps. 8.
Do not deploy to the live cluster without an explicit deployment step.

Recommended order: 1. A --- runtime/configuration. 2. B ---
persistence/migrations. 3. C --- incremental sync/backfill. 4. D ---
normalisation/data quality. 5. E --- fatigue v2. 6. F --- durability
analytics. 7. G --- daily/weekly reports. 8. H --- annotations. 9. I ---
Prometheus/Grafana. 10. J --- notifications.

## 15. Release acceptance checklist

-   [ ] Existing Garmin and Intervals ingestion still works.
-   [ ] Data survives pod restart.
-   [ ] Sync is idempotent, resumable and observable.
-   [ ] Missing values remain missing, not zero.
-   [ ] Calculated/estimated/source values are distinguishable.
-   [ ] Fatigue analysis supports normal 45--50 minute rides and 3--4
    ride weeks when evidence is sufficient.
-   [ ] Baselines exclude the evaluated period.
-   [ ] Durability metrics require comparable, good-quality data.
-   [ ] Daily/weekly reports explain reasons and uncertainty.
-   [ ] Prometheus labels are bounded.
-   [ ] Secrets and personal data are protected.
-   [ ] Backup/restore tested.
-   [ ] Unit, contract, integration and end-to-end tests pass.
-   [ ] Helm chart and CronJobs pass template/lint validation.
-   [ ] Deployment and rollback steps are documented.
