# Training Intelligence Service --- Product Recommendations

**Purpose:** Define what `prom-garmin-scraper` should become and the
value it should return. See
[FEATURE_IMPLEMENTATION.md](FEATURE_IMPLEMENTATION.md) for
implementation detail.

## Executive recommendation

Evolve this repository from a Garmin-to-Prometheus exporter with
Intervals.icu parsing into a durable personal **training intelligence
service**.

It should combine activity performance with recovery context, identify
meaningful trends, and help answer:

1.  What training have I actually completed?
2.  Is aerobic durability improving?
3.  Is my current workload being absorbed?
4.  Are there persistent signs that recovery is becoming a limiter?
5.  What does the evidence suggest about the next few days?
6.  How confident is the analysis, and what data is missing?

The product is not a workout prescription engine and must not encourage
chasing CTL, TSS or a composite readiness score. It should return a
small number of explainable observations that support consistent,
sustainable training.

## Athlete profile and assumptions

Initial configurable defaults should reflect: - Primary sport:
cycling. - Current focus: aerobic base, repeatability and durability,
not intensity. - Typical repeatable indoor session: 45--50 minutes,
mostly easy Z1/low Z2. - Longer rides are more likely outdoors; 60--90+
minute rides are possible when life and recovery allow. - Normal
pattern: approximately 3--4 rides per week, flexibly scheduled. -
Progress only when current volume is repeatable and recovery is
acceptable. - Running is not currently a training priority. - Sleep
disruption, work/on-call load, travel and family demands are relevant
context. - Sustainable consistency matters more than Intervals.icu
Fitness/CTL.

These are editable athlete settings, not hard-coded assumptions or
universal training rules.

## Product capabilities and priorities

### P0 --- Reliable personal training record

Build one canonical, deduplicated history of activities and daily
wellness data. It must survive pod restarts and Prometheus
retention/TSDB loss.

-   Synchronise Garmin daily wellness/recovery data.
-   Synchronise Intervals.icu activities and relevant streams/metadata.
-   Support safe incremental sync and resumable backfill.
-   Track source timestamps, ingestion timestamps, sync status and data
    quality.
-   Handle API outages, expired credentials, rate limits and partial
    failures without losing already-ingested data.
-   Represent missing values as missing, never as zero.

### P0 --- Daily training/recovery briefing

Provide a concise briefing covering: - Training load and frequency over
7 and 28 days. - Recent sleep/recovery context. - Whether comparable
easy rides show unusual physiological cost. - Whether the current
pattern looks stable, is accumulating strain, or is too uncertain to
interpret. - A cautious posture: normal easy training, keep it light,
recovery priority, or insufficient information.

Every conclusion must include evidence and caveats. This is an
interpretation aid, not a medical assessment or prescriptive workout.

### P0 --- Durability and aerobic development

Track progress in terms that reflect the actual goal: - Repeatability of
45--50 minute easy rides. - Ability to complete longer rides without
disproportionate fatigue afterwards. - HR response at comparable
power/intensity. - Aerobic efficiency (power relative to HR), only
across comparable conditions. - HR drift/decoupling during sufficiently
steady efforts. - Weekly cycling frequency, duration and
session-duration distribution. - Recovery between sessions and tolerance
of back-to-back riding. - Longer-ride frequency and effect on the next
one or two sessions.

Show trends and representative examples. Do not claim that a small HR
change proves fitness has improved.

### P1 --- Training load and progression guardrails

Summarise weekly and rolling 7/28/42-day: - Ride count, cycling time,
distance, elevation and TSS. - Longest ride and share of weekly load. -
Easy/moderate/hard distribution when zone data is reliable. - Changes in
volume and frequency against recent history. - Recovery context
alongside training load.

CTL/ATL/TSB can be secondary context, not the objective or sole decision
rule. Avoid simplistic acute:chronic ratios and automatic "safe
increase" percentages. Flag abrupt changes as prompts for review, not
declarations of injury risk.

### P1 --- Explainable fatigue mismatch detection

Retain the existing Fatigue Checker as a foundation, but validate and
revise its assumptions.

Look for repeated elevated physiological cost during comparable easy
efforts against the athlete's own baseline. Inputs may include: - HR at
comparable power/IF. - HR/power relationship, guarded against very low
power. - HR drift/decoupling on steady efforts. - Resting HR and HRV
trends. - Sleep duration/quality and Garmin recovery indicators. -
Recent volume, frequency and harder sessions. - Optional athlete
annotations.

Possible outcomes: - No clear mismatch. - Possible elevated
strain/recovery mismatch. - Persistent strain pattern. - Insufficient or
incomparable data.

Never diagnose illness, infer a cause, or label one poor ride as
fatigue. Heat, hydration, stress, illness, caffeine, terrain and sensor
quality can all affect measurements.

### P1 --- Weekly review

Generate a report containing: 1. Training completed versus the previous
1--4 weeks. 2. Time, frequency and session-duration trends. 3. One or
two meaningful durability observations. 4. Recovery context and
persistent anomalies. 5. What appears to be working. 6. Risks and
uncertainty. 7. A conservative emphasis for next week: consolidate,
maintain or cautiously progress.

Do not invent a plan when the evidence is weak.

### P2 --- Athlete annotations

Allow optional, low-friction notes for: - Illness/feeling unwell. -
Disrupted sleep. - Work/on-call stress. - Travel. - Unusual family/life
demands. - Strength training. - Subjective leg freshness or perceived
exertion. - Why a session was shortened or skipped.

Do not require a daily questionnaire.

### P2 --- Notifications

Notify only for persistent, actionable events: - Sync has failed or
become stale. - A weekly review is ready. - A recovery mismatch persists
across multiple comparable sessions.

Avoid daily overtraining alerts or alerts triggered by one poor night.
Quiet by default.

## Assessment of the current repository

The repository already has meaningful foundations: - Garmin connector
and daily wellness metrics. - Intervals.icu client and stream parsing. -
Prometheus exporter and Helm deployment. - FatigueChecker with explicit
gates, baseline comparisons, classifications and tests. - Diagnostic and
plain-text summary endpoints. - Backfill and alerting concepts.

This is a useful prototype, not a blank slate. However, a completion
report saying the fatigue feature is complete is not evidence that its
assumptions fit the athlete or that the service is operationally
resilient.

### Important gaps

1.  **Fatigue eligibility does not fit normal training.** Current
    defaults require 60-minute easy rides, at least five total rides in
    seven days, two qualifying easy rides and six rides per IF band for
    a baseline. The athlete commonly rides 45--50 minutes and 3--4 times
    weekly, so normal weeks may produce "insufficient data".
2.  **Analysis is coupled to `/garmin/daily`.** The app is largely
    request-triggered. A long-running service needs an explicit,
    reliable scheduled ingestion and analysis workflow.
3.  **Prometheus is not a system of record.** It is suitable for
    current-state gauges and operational telemetry, not canonical
    activity records, annotations, reproducible analysis or reliable
    backfill.
4.  **Activity history is repeatedly fetched and reparsed.** Persist
    normalised activities/features once, then recompute locally.
5.  **The fatigue classifier is too narrow to be the product.** It does
    not yet assess durability, progression, repeatability or longer-ride
    tolerance.
6.  **Thresholds and parsing need real-data validation.** Check zone
    fraction/percentage handling, duration semantics, FTP changes,
    trainer rides, missing HR and HR drift calculations.
7.  **Operational hardening is required.** Idempotency, persistence,
    checkpoints, retries, health endpoints, structured logs, bounded API
    work and secret handling need explicit design.

## Design principles

-   Personal baselines, not population norms.
-   Compare like with like: intensity, duration, power and conditions.
-   Prefer "unknown" over false confidence.
-   No single magic readiness score.
-   No prescriptive workout engine in the initial scope.
-   Durable canonical source data outside Prometheus.
-   Reproducible analysis with versioned algorithms.
-   Idempotent ingestion and resumable backfill.
-   Explainable outputs with sample counts, reasons and limitations.
-   Keep the existing Python/Flask/Prometheus/Helm stack unless a real
    limitation justifies change.
-   AI is an implementation accelerator, not a runtime dependency. Core
    calculations remain deterministic and testable. An LLM may later
    render structured findings into prose, but must not invent metrics
    or decide readiness.

## Delivery order

### Phase 1 --- Trust the data

Fix parsing/time semantics; add persistent storage and migrations;
implement idempotent incremental sync; add checkpoints, retry/backoff
and health endpoints; add fixture-backed integration tests.

### Phase 2 --- Make fatigue analysis useful

Adapt eligibility to real 45--50 minute rides and 3--4 ride weeks;
separate data sufficiency from interpretation; improve comparable-effort
baselines; validate against real activities.

### Phase 3 --- Add durability analytics

Build weekly summaries, duration distribution, comparable aerobic
efficiency, steady-ride drift, repeatability and longer-ride tolerance.

### Phase 4 --- Add coaching interface

Add daily briefing, weekly review, optional annotations and low-noise
notifications.

Do not start by adding more Grafana panels. Build trustworthy data and
analysis first.

## Definition of success

After a normal week, the athlete can understand: - What training was
completed and how it compares with recent weeks. - Whether the usual
easy session is becoming easier or more costly. - Whether longer
sessions and consecutive days are becoming more repeatable. - Whether
recovery signals are broadly supportive or persistently concerning. -
Whether evidence supports continuing, consolidating or easing off. -
What the service does not know.

The service should reduce uncertainty and support consistency, not make
the athlete feel obliged to train because a dashboard says Fitness is
falling.
