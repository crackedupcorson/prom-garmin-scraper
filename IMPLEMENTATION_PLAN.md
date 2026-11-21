# Training Intelligence Service — Implementation Plan

This is the implementation backlog for the v2 branch. The authoritative product and implementation requirements are:

- [.github/agents/TRAINING_INTELLIGENCE_RECOMMENDATIONS.md](.github/agents/TRAINING_INTELLIGENCE_RECOMMENDATIONS.md)
- [.github/agents/FEATURE_IMPLEMENTATION.md](.github/agents/FEATURE_IMPLEMENTATION.md)

The service should evolve from a Garmin-to-Prometheus prototype into a durable, explainable personal training-intelligence service. Work is intentionally phased: data trust comes before richer analysis, and analysis comes before coaching/reporting features.

Product priority labels in the agent documents (`P0`, `P1`, and `P2`) describe user value and urgency. They do not override the implementation dependencies or permit later-phase work to bypass the Phase 0 safety and architecture gates.

## Current assessment

The repository has useful foundations:

- Garmin/Garth authentication and daily wellness retrieval.
- Intervals.icu activity and stream retrieval/parsing.
- Prometheus metrics and a Helm deployment.
- A pure-function fatigue prototype with unit tests and fixtures.
- Diagnostic and plain-text fatigue endpoints.

The current implementation is not yet the target architecture:

- Flask routes perform provider calls and repeatedly reparse activity history.
- Prometheus and ad-hoc files are used instead of canonical persistent storage.
- There are no durable sync checkpoints, resumable ingestion workflows, or migration-backed models.
- Configuration is read directly from environment variables throughout the code.
- Garmin authentication logs credentials.
- The parser applies one current FTP to historical activities and calculates HR drift without a steady-power gate.
- The fatigue defaults do not fit the normal 45–50 minute, 3–4 ride/week pattern.
- Helm has no health probes or scheduled sync/analysis CronJobs.
- Existing alerts include noisy or medically suggestive interpretations that do not fit the product principles.
- SQLite/PVC/CronJob topology has not yet been designed well enough to safely begin persistence work.

## Delivery rules

- Preserve working behavior while moving one boundary at a time.
- Add tests with every vertical slice.
- Keep deterministic calculations separate from interpretation and presentation.
- Prefer unknown or insufficient data over false confidence.
- Keep Prometheus for current-state and operational metrics, not historical source-of-truth data.
- Do not add a prescriptive workout engine or a composite readiness score.
- Do not deploy automatically to the live Kubernetes cluster.
- Copilot implements only the current brief; it does not expand scope without review.
- Codex reviews code and tests before a task is accepted or marked complete.
- Phase transitions require product-owner approval.

## Immediate safety fix

### TI-000 — Remove credential logging

Status: complete in v2 working tree.

Remove password and token exposure from stdout/logging in Garmin authentication. Preserve useful authentication state messages without logging usernames, passwords, tokens, or payloads.

Acceptance:

- No Garmin password is printed or logged.
- Authentication tests cover the login path and assert that captured output/log records contain no credential values.
- This fix remains independent of the configuration and provider-adapter migrations.

## Phase 0 — Establish a safe baseline

### TI-001 — Define compatibility and migration boundaries

Document current endpoint contracts and identify compatibility routes while new services are introduced.

Acceptance:

- Existing `/garmin/daily`, `/intervals/*`, `/fatigue/*`, and `/metrics` behavior is covered by tests.
- New services can be introduced without a wholesale rewrite.
- Live deployment is excluded from implementation changes.

### TI-002 — Add a reproducible development/test environment

Make dependencies and test execution reproducible, with provider calls mocked and fixture-backed integration tests.

Acceptance:

- Tests run from a clean environment using one documented command.
- Garmin, Intervals.icu, Slack, and Prometheus are not required for unit tests.
- The test suite includes parser, normalization, storage, sync, and API boundary coverage.

### TI-002B — Resolve SQLite/PVC/CronJob deployment topology

Design and record the safe single-writer deployment topology before persistence implementation begins. SQLite remains the preferred starting point.

The design must cover:

- ReadWriteOnce PVC ownership and pod scheduling/affinity.
- How the API Deployment and sync/analysis CronJobs avoid concurrent SQLite writers.
- Migration execution and failure/retry behavior.
- Backup, restore, retention, and corruption-recovery procedures.
- What operational signal indicates that SQLite is no longer sufficient and PostgreSQL should be reconsidered.

Acceptance:

- The chosen topology is documented with a deployment sequence and failure scenarios.
- Only one process can perform SQLite writes at a time.
- Migrations are run exactly once per release or otherwise safely serialized.
- Backups can be taken without corrupting the database and a restore procedure is tested.
- The design does not require CronJobs to access the Kubernetes API merely to invoke the service.
- No persistence implementation starts until this task is approved.

## Phase 1 — Trust the data

### TI-003 — Add typed configuration

Create `app/config.py` for credentials, provider URLs, timeouts, database path, timezone, sync windows, FTP provenance, analysis thresholds, schedules, logging, and notifications.

Acceptance:

- Required settings fail fast with actionable errors.
- Optional integrations can be explicitly disabled.
- Business modules no longer read `os.environ` directly.

### TI-004 — Add persistent canonical storage and migrations

Introduce SQLite on the existing PVC using SQLAlchemy/Alembic or an equivalent migration-backed approach.

Initial tables:

- `activities`, keyed by `(source, source_activity_id)`.
- `activity_streams`, retaining only streams needed by planned analytics.
- `daily_wellness`, keyed by `(source, local_date)`.
- `sync_runs`, including status, counters, checkpoints, and error summaries.
- `athlete_annotations`, for optional private context.
- `analysis_runs`, including algorithm version, input watermark, and result JSON.

Acceptance:

- Upserts are idempotent and provider IDs are not assumed globally unique.
- Missing values remain missing, never zero.
- Data survives pod restart.
- Migrations support database creation and upgrade.
- Source snapshots are retained where useful for debugging.

### TI-005 — Build provider adapters

Move Garmin and Intervals.icu access behind `app/clients/garmin.py` and `app/clients/intervals.py`.

Acceptance:

- Provider behavior is isolated and mockable.
- Requests have timeouts and bounded exponential retries with jitter.
- Auth, rate-limit, network, malformed-payload, and not-found failures are distinct.
- Credentials, tokens, and sensitive payloads never appear in logs.

### TI-006 — Implement normalization and data-quality flags

Create a normalization layer for UTC/local dates, moving versus elapsed time, sport type, indoor/outdoor status, activity-specific FTP, zones, sensor gaps, and metric provenance.

Required quality flags include `hr_missing`, `power_missing`, `power_sensor_dropout`, `duration_ambiguous`, `ftp_unknown`, `zones_unavailable`, `not_steady_enough_for_decoupling`, and `source_value_estimated`.

Acceptance:

- UTC is canonical and athlete-local dates use configured timezone rules.
- HR/power ranges are validated without fabricating values.
- Strength and running remain distinct from cycling.
- Zone fractions and percentages are handled explicitly.
- Analytics expose the quality gates that excluded an activity.

### TI-007 — Implement incremental sync orchestration

Add source-specific sync services with overlap windows, per-record errors, checkpoints, partial status, and idempotent upserts.

Intervals.icu must fetch athlete/FTP context, activity metadata, and streams only for new or changed activities. Garmin must sync wellness over an overlap window and track the last successful date/API sync.

Acceptance:

- Re-running a sync creates no duplicates.
- Failed records do not discard successful records.
- Checkpoints advance only after successful pages/windows.
- Expired credentials produce actionable sync errors.
- Freshness and partial failure status are measurable.

### TI-008 — Replace the current backfill

Add a bounded CLI with date ranges, dry-run, resume, retries, rate limiting, partial progress, and post-ingestion analysis.

Acceptance:

- Backfill does not use Prometheus TSDB blocks as primary storage.
- A restart resumes from persisted progress.
- Derived analysis runs after the batch, not after every record.
- The current unbounded GET backfill is replaced or retained only as a protected compatibility route.

### TI-009 — Add health and operational endpoints

Add `/health/live` and `/health/ready`, structured logs, request bounds, and protection for mutation/diagnostic routes.

Acceptance:

- Liveness does not depend on providers.
- Readiness fails when required local storage is unavailable.
- Temporary provider outages do not make the API unready.
- Logs include sync run ID, source, activity ID, and error category without secrets.
- `weeks`, `days`, and activity counts are bounded.
- Mutations use POST; reads use GET.

### TI-010 — Add Helm-managed scheduled jobs

Add configurable CronJobs for Garmin wellness sync, Intervals activity sync, analysis, and weekly reports.

Acceptance:

- Jobs use `concurrencyPolicy: Forbid`.
- Resource limits, `activeDeadlineSeconds`, and bounded history are configured.
- The deployment has liveness/readiness probes.
- The design preserves a single SQLite writer.
- Manual triggering is supported without requiring Kubernetes API access from the job.

## Phase 2 — Make fatigue analysis useful

### TI-011 — Redesign fatigue eligibility around actual training

Replace the current 60-minute/five-ride assumptions with configurable duration cohorts, initially 35–55, 55–80, and 80+ minutes. Use 28–42-day baselines and 7-/14-day evaluation windows when sample counts permit.

Acceptance:

- Stable 45-minute, 3–4 ride weeks are analyzable.
- Evaluation rides are excluded from their own baseline.
- Missing zones are handled explicitly rather than automatically rejected.
- Small samples produce `insufficient_data`.

### TI-012 — Separate sufficiency, strain, and interpretation

Refactor the current classifier into separate outputs for data sufficiency, observed strain, and contextual interpretation.

Acceptance:

- Output has a stable JSON contract with status, confidence, observations, reasons, limitations, and algorithm version.
- Supported statuses are `insufficient_data`, `no_clear_mismatch`, `possible_recovery_mismatch`, and `persistent_strain_pattern`.
- No illness, overtraining, causal, or unsupported “absorbing well” claims are emitted.
- One anomalous ride cannot create a fatigue classification.

### TI-013 — Harden comparable-effort calculations

Add robust summaries, minimum-power guards, FTP-change handling, indoor/outdoor separation, and steady-power requirements for drift/decoupling.

Acceptance:

- Zero/near-zero power cannot create misleading cardiac-cost values.
- HR drift returns `not_applicable` for non-steady rides.
- Streams align by timestamps rather than assumed indexes.
- Missing HR, power, streams, and sensor dropouts are tested.

### TI-014 — Add real-data validation fixtures

Add fixtures for normal 45-minute rides, repeated elevated HR, one anomaly, missing sensors, FTP changes, indoor/outdoor differences, DST transitions, duplicate dates, empty streams, and poor sleep without ride strain.

## Phase 3 — Add durability analytics

### TI-015 — Add weekly and rolling training summaries

Implement calendar-week and rolling 7/28/42-day summaries for ride count, cycling time, distance, elevation, TSS, duration distribution, longest ride, gaps, back-to-back rides, and strength separately.

### TI-016 — Add repeatability analysis

Create the 35–55-minute easy cycling reference cohort and compare HR/power, completion, time to next ride, and next-ride response. Show representative examples and uncertainty rather than a single score.

### TI-017 — Add aerobic efficiency and decoupling

Implement comparable indoor/outdoor efficiency trends and aligned HR/power decoupling. Exclude stops, intervals, gaps, sensor failures, and unstable power; require multiple observations before reporting a trend.

### TI-018 — Add long-ride tolerance

Track 75–90+ minute ride frequency, response during the ride, time until the next ride, and effects on the following one or two sessions. Do not label duration alone as harmful.

## Phase 4 — Add the coaching interface

### TI-019 — Add the daily briefing API

Return 7-/28-day training load, frequency, sleep/recovery context, comparable easy-ride response, cautious posture, evidence, confidence, and limitations.

### TI-020 — Add weekly review generation

Generate recent comparisons, time/frequency/session-duration trends, durability observations, recovery context, persistent anomalies, uncertainty, and a conservative next-week emphasis.

### TI-021 — Add athlete annotations

Add authenticated POST/GET endpoints for optional notes covering sleep disruption, illness, work stress, travel, strength, subjective freshness, perceived exertion, and shortened sessions.

### TI-022 — Add low-noise notifications

Notify only for stale/failed syncs, completed weekly reviews, or persistent mismatch across comparable sessions. Avoid daily overtraining alerts and one-night triggers.

## Dependency order

The critical path is:

`TI-000 → TI-001 → TI-002 → TI-002B → TI-003 → TI-004 → TI-005 → TI-006 → TI-007 → TI-008/TI-009 → TI-010 → TI-011–TI-014 → TI-015–TI-018 → TI-019–TI-022`

The first meaningful milestone is Phase 1: a durable, restart-safe canonical record with reliable sync status. More dashboards should wait until that milestone is complete. Phase 1 must not begin until TI-002B has been reviewed and approved.
