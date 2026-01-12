# Fatigue Mismatch & Recovery Signal Detection — Copilot Prompt (v0)

## Purpose

This project implements a **conservative, rule-based fatigue mismatch detection system** for a cyclist.

Its job is to detect when **physiological strain appears elevated relative to recent training load**, in order to:
- Reduce ambiguity around rest vs ride decisions
- Explain why legs feel heavy when TSS looks reasonable
- Support consistency during periods of non-training stress (work, illness, poor sleep)

This system is a **warning and interpretation layer**, not a decision engine.

If the system is unsure, it must say so.

---

## Explicit Non-Goals (Do NOT Build These)

This system must **not**:

- Prescribe workouts
- Adjust or estimate FTP
- Produce a readiness, freshness, or recovery score
- Optimize performance
- Replace subjective feel
- Infer causality
- Use machine learning or probabilistic models

If functionality feels like coaching or automation, it is out of scope.

---

## Available Data (Already Ingested)

### Per Ride (Intervals / activity streams)
- TSS
- IF
- Average HR
- HR drift
- Zone distribution
- Ride duration

### Daily Garmin Metrics
- Resting HR
- Sleep duration / quality
- HRV (where available)

No new external APIs may be added.

---

## System Philosophy

- Rule-based heuristics only
- Conservative thresholds
- False negatives preferred over false positives
- Trend-based interpretation only
- No single-ride conclusions
- Interpretability > accuracy

The system must be allowed to say:
> “Insufficient data to interpret.”

---

## Core Concept

Detect **fatigue mismatch** when:

> Training load is low or moderate, but physiological strain during easy riding is elevated.

This does **not** claim causality — only likelihood.

---

## Minimum Data Requirements (Hard Gates)

### Global Requirements
Do not emit fatigue interpretations unless ALL are true:

- ≥ 21 days of historical data
- Reliable HR and power data on rides

If unmet:
- System state = `insufficient_history`
- No fatigue labels allowed

---

### Baseline Eligibility (Per IF Band)

Initial IF bands:
- 0.50–0.60
- 0.60–0.65

To establish a baseline for an IF band:
- ≥ 6 rides
- Each ride:
  - ≥ 45 minutes
  - Continuous HR + power
  - No long pauses (>2 minutes)

If a band does not meet this:
- That band is inactive
- Rides in that band cannot be evaluated for strain

---

### Easy Ride Eligibility (Ride-Level)

A ride qualifies as an **easy ride** only if:

- IF < 0.65
- Duration ≥ 60 minutes
- ≥ 60% of time in Z2 or below

If any condition fails:
- Ignore the ride for fatigue mismatch logic
- Still include it in training load totals

---

### Rolling Window Eligibility (Interpretation-Level)

To produce ANY classification other than `neutral_noisy`:

**7-day window**
- ≥ 2 eligible easy rides
- ≥ 5 total rides
- No >3-day gap with zero riding

If unmet:
- Output = `neutral_noisy`
- No fatigue accumulation labels allowed

---

## Training Load Context

Before interpreting strain vs load:

- ≥ 3 rides with TSS in the last 7 days
- No single ride contributing >60% of weekly TSS

If violated:
- Load context = `unreliable`
- Mismatch logic should be muted

---

## First Signal to Implement (v0)

### Easy Ride Strain Detection

For eligible easy rides:

Compare against rolling baseline for the same IF band:
- Average HR
- HR drift
- Cardiac cost proxy (avg HR / avg power)

Flag a ride ONLY when:
- Multiple strain indicators are elevated vs baseline

Single-ride flags are descriptive only and must not trigger conclusions.

---

## Aggregation & Interpretation

Aggregate strain flags over rolling windows (e.g. 7 days).

Possible classification outputs:
- `absorbing_well`
- `neutral_noisy`
- `fatigue_accumulating`
- `non_training_fatigue_likely`

Rules must be:
- Simple
- Explicit
- Commented
- Easy to delete or change later

If classification is ambiguous:
- Default to `neutral_noisy`

---

## Outputs

### Prometheus Metrics
Expose:
- Raw strain metrics
- Rolling baseline values
- Boolean flags (0/1)
- Gating states (eligibility, sufficiency)

Avoid composite scores where possible.

---

### Text Summary Endpoint

Expose a plain-English summary such as:

> “Last 7 days: training load moderate, easy-ride strain elevated on multiple rides, pattern consistent with non-training fatigue.”

If data is insufficient:
- Say so explicitly.

---

## Coding Style Guidance

- Prefer clarity over cleverness
- Use explicit thresholds
- Comment WHY a rule exists
- Optimize for debuggability and trust
- Make the system easy to silence

---

## Prime Directive

> This system exists to **reduce decision ambiguity**, not remove athlete agency.

Do not violate this principle.

If unsure how to proceed:
- Do less
- Be conservative
- Bias toward silence
