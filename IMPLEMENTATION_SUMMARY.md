# Fatigue Checker Implementation Summary

## Overview
The fatigue checker mini-app is now **complete** (steps 1–18). This document summarizes what was built, how it works, and how to use it.

## What Was Built

### Core System: FatigueChecker + FatigueConfig
- **Location:** `app/garmin/fatigue.py`
- **Lines:** 630+ with comprehensive docstrings and inline comments
- **Key Classes:**
  - `FatigueConfig`: Dataclass with 13+ configurable thresholds
  - `FatigueChecker`: Pure, rule-based detector for physiological strain mismatch

### Test Suite
- **Location:** `app/garmin/test_fatigue.py`
- **Tests:** 57 comprehensive unit tests across 11 test classes
- **Coverage:** All methods and configuration variants
- **Status:** ✅ All passing

### Fixtures & Sample Data
- **Location:** `app/garmin/fixtures.py`
- **Scenarios:** 6 realistic training patterns (stable, elevated strain, accumulating, insufficient data, skewed load, 30-day baseline)
- **Usage:** For manual testing, demos, and integration validation

### Integration Points (Already Existing)
- **Endpoints:**
  - `POST /fatigue/diag` — Diagnostic endpoint with full classification details
  - `GET/POST /fatigue/summary` — Plain-English summary output
  - `GET /garmin/daily` — Auto-integration on every Garmin sync
- **Metrics:** 15+ Prometheus metrics exposed via `populate_fatigue_metrics()` in `metrics.py`
- **Code:** `app/python-scraper.py` lines 56, 106–207

### Documentation
- **README:** "Fatigue Checker" section covering philosophy, usage, limitations, configuration
- **Inline Comments:** Extensive "WHY" explanations in fatigue.py
- **Docstrings:** Full module, class, and method documentation

## How It Works

### The Pipeline
```
[Ride Data from Intervals API]
         ↓
[History Gating] — Need ≥21 days of HR+power data?
         ↓
[Easy Ride Detection] — IF <0.65, ≥60 min, Z2 time ≥60%?
         ↓
[Per-Ride Metrics] — Compute HR, cardiac cost, HR drift, TSS
         ↓
[Build Baselines] — Group easy rides by IF band (0.50–0.60, 0.60–0.65)
         ↓
[Rolling Window Gating] — ≥5 total rides, ≥2 easy rides, no >3-day gaps?
         ↓
[Training Load Check] — TSS reliable? (no single ride >60% of weekly)
         ↓
[Compare Rides to Baseline] — Z-score each easy ride's metrics
         ↓
[Classify 7-Day Window] — Count flagged rides → classification
         ↓
[Classification Output]
  - absorbing_well
  - neutral_noisy (default)
  - non_training_fatigue_likely (2+ easy rides elevated strain)
  - fatigue_accumulating (3+ easy rides elevated strain)
```

### Key Design Decisions

#### Why Easy-Ride Only Analysis?
High-intensity efforts (IF ≥ 0.65) naturally show elevated HR and cardiac cost. Comparing them to low-intensity baselines would create false positives. The system explicitly ignores high-IF rides for strain interpretation; they only count toward training load context (task 10).

#### Why Three Gating Layers?
1. **History gating** (21 days) — Ensures stable baseline statistics
2. **Rolling window gating** (7-day window, ≥5 rides, ≥2 easy, no >3-day gaps) — Ensures recent, complete data
3. **Training load context** (min TSS reliability) — Ensures a single outlier (race, epic) doesn't skew the interpretation

Multiple gates prevent premature or noisy classifications.

#### Why Z-Score Thresholds?
Z-score = (observed - mean) / stdev. A z-score >1.0 means the ride is 1+ standard deviations above the baseline. This is a conservative threshold (captures ~15% of normal distribution), preventing noise-driven false positives.

#### Why Cardiac Cost (HR/Power)?
- **Cardiac cost** = avg_heartrate / avg_power (bpm per watt)
- Elevated cardiac cost with fixed power = sympathetic stress signal
- More stable than raw HR (accounts for fitness-based changes)
- Sensitive to sleep debt, illness, stress, altitude, humidity

#### Why NOT Single Classifications?
The system returns **reasons** alongside classifications. "Non-training fatigue likely" doesn't mean you're sick—it means the pattern is *consistent with* non-training stress. Athletes can drill into reasons and use context to make decisions.

## Configuration

### Default Thresholds
```python
config = FatigueConfig(
    # History
    min_history_days=21,
    
    # Easy ride gates
    max_easy_ride_if=0.65,
    min_easy_ride_duration_minutes=60.0,
    min_easy_ride_z2_percent=60.0,
    
    # Baseline
    min_rides_per_band=6,
    
    # Rolling window
    rolling_window_days=7,
    min_easy_rides_in_window=2,
    min_total_rides_in_window=5,
    max_gap_days=3,
    
    # Training load
    max_single_ride_tss_percent=60.0,
    
    # Strain detection
    strain_zscore_threshold=1.0,
    min_flagged_rides_for_non_training=2,
    min_flagged_rides_for_accumulating=3,
)
```

### How to Tune
Edit default values in `FatigueConfig()` and pass to `FatigueChecker()`:
```python
config = FatigueConfig(strain_zscore_threshold=0.8)  # More sensitive
checker = FatigueChecker(config)
```

## Testing

### Run Unit Tests
```bash
pytest app/garmin/test_fatigue.py -v
```

### Manual Testing with Fixtures
```python
from app.garmin.fixtures import SCENARIO_STABLE_WEEK, SCENARIO_FATIGUE_ACCUMULATING_WEEK
from app.garmin.fatigue import FatigueChecker

checker = FatigueChecker()
result = checker.aggregate_7day_classification(SCENARIO_FATIGUE_ACCUMULATING_WEEK)
print(result["classification"])  # "fatigue_accumulating"
```

### Integration Testing via Endpoints
```bash
# Diagnostic endpoint (POST with rides)
curl -X POST http://localhost:8080/fatigue/diag \
  -H "Content-Type: application/json" \
  -d '{"rides": [...]}'

# Summary endpoint (GET for latest 7-day summary)
curl http://localhost:8080/fatigue/summary
```

## Output Examples

### Diagnostic Endpoint (`/fatigue/diag`)
```json
{
  "classification": "non_training_fatigue_likely",
  "reasons": ["2_rides_show_strain_pattern"],
  "gating": {
    "eligible": true,
    "reasons": [],
    "total_rides": 6,
    "easy_rides": 4
  },
  "load_context": {
    "reliable": true,
    "reasons": [],
    "tss_stats": {
      "total": 480,
      "count": 6,
      "max": 155,
      "max_percent": 32.3
    }
  },
  "strain_flags": [
    {"ride_date": "2026-01-11", "metric": "avg_heartrate", "zscore": 1.2},
    {"ride_date": "2026-01-12", "metric": "cardiac_cost", "zscore": 1.1}
  ]
}
```

### Summary Endpoint (`/fatigue/summary`)
```
=== FATIGUE STATUS SUMMARY ===

⚠️  POSSIBLE NON-TRAINING FATIGUE
Multiple easy rides show elevated strain (HR, cardiac cost) relative to baseline.
This pattern is consistent with external stress (work, illness, sleep, etc.)
not training load. Consider recovery and non-training factors.

📈 CONTEXT: 6 total rides (4 easy rides) over 7 days
   Total TSS: 480 | Max ride: 32.3% of weekly
   IF 0.50–0.60 baseline: 135 bpm (n=12)
   IF 0.60–0.65 baseline: 140 bpm (n=8)

NOTE: This system detects strain mismatch during easy riding only.
High-intensity efforts are expected to show elevated strain (by design).
This is a warning and interpretation layer, not a decision engine.
```

### Prometheus Metrics
```
prom_fatigue_classification{window="7d"} = 1  # "non_training_fatigue_likely"
prom_fatigue_easy_rides_flagged = 2
prom_fatigue_total_rides_window = 6
prom_fatigue_baseline_hr_mean{band="IF_50_60"} = 135.0
prom_fatigue_baseline_hr_stdev{band="IF_50_60"} = 4.5
... (15+ metrics total)
```

## Architecture Strengths

1. **Pure Data Primitives:** Each method does one thing: extract, gate, aggregate, or compare. No hidden state or side effects.
2. **Conservative Thresholds:** Multiple gates, z-score >1.0, min 2–3 flagged rides required. Avoids false positives.
3. **Configurable:** All thresholds tunable without code changes via `FatigueConfig`.
4. **Reason-Based:** Every classification includes reasons, not just a label.
5. **Well-Tested:** 57 tests covering all paths and configuration variations.
6. **Well-Commented:** Extensive "WHY" comments in the code explaining design decisions.
7. **Production-Ready:** Integrated with Flask app, Prometheus metrics, and Intervals API.

## Limitations & Caveats

1. **Easy Rides Only:** High-intensity efforts are exempt from strain interpretation (by design).
2. **Recent Data Only:** Gap >3 days disqualifies the window (prevents stale baselines).
3. **No Causality:** Classifications describe patterns, not causes. Athletes must interpret context.
4. **HR+Power Only:** System requires both metrics; indoor trainers with power-only data are skipped.
5. **Static IF Bands:** Hard-coded at 0.50–0.60 and 0.60–0.65. Cannot be dynamically updated per athlete.
6. **No Learning:** No machine learning or personalization; purely rule-based.

## What's Next?

The system is **complete and production-ready**. Future enhancements could include:
- Anomaly detection for single rides (not just windows)
- Integration with sleep/stress APIs
- Per-athlete IF band customization
- Real-time alerts (e.g., SMS when fatigue_accumulating)
- Weekly digest reports
- Cross-sport support (running, swimming)

## Files Modified/Created

### Created
- `app/garmin/fatigue.py` — Core system (630 lines)
- `app/garmin/test_fatigue.py` — Unit tests (713 lines, 57 tests)
- `app/garmin/fixtures.py` — Sample datasets (250+ lines)
- `IMPLEMENTATION_SUMMARY.md` — This file

### Modified
- `app/python-scraper.py` — Already integrated; no changes needed
- `app/garmin/metrics.py` — Already integrated; no changes needed
- `README.md` — Added "Fatigue Checker" section
- `FATIGUE_TODO.md` — Marked all 18 items complete

---

**Status:** ✅ Complete (Steps 1–18)  
**Tests:** ✅ 57 passing  
**Documentation:** ✅ Comprehensive  
**Production:** ✅ Ready
