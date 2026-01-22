"""Sample datasets and fixtures for testing the Fatigue Checker system.

These fixtures represent realistic cycling data patterns and can be used for:
- Manual testing via the diagnostic endpoint
- Demonstration of different fatigue states
- Integration testing with the Intervals API
- Debugging classification logic
"""


# Scenario 1: Baseline establishment
# A cyclist with stable, low-intensity training.
# Expected: No elevated strain, classification = neutral_noisy
SCENARIO_STABLE_WEEK = [
    {
        "date": "2026-01-15",
        "intensity_factor": 0.55,
        "total_time": 3600,
        "zone_percentages": {"Z1": 0.05, "Z2": 0.70, "Z3": 0.25},
        "avg_heartrate": 135,
        "max_heartrate": 155,
        "avg_power": 180,
        "normalized_power": 185,
        "tss": 65,
        "hr_drift": 2.0,
    },
    {
        "date": "2026-01-16",
        "intensity_factor": 0.60,
        "total_time": 4200,
        "zone_percentages": {"Z1": 0.08, "Z2": 0.65, "Z3": 0.27},
        "avg_heartrate": 138,
        "max_heartrate": 158,
        "avg_power": 195,
        "normalized_power": 200,
        "tss": 78,
        "hr_drift": 3.0,
    },
    {
        "date": "2026-01-17",
        "intensity_factor": 0.58,
        "total_time": 3900,
        "zone_percentages": {"Z1": 0.06, "Z2": 0.68, "Z3": 0.26},
        "avg_heartrate": 136,
        "max_heartrate": 156,
        "avg_power": 188,
        "normalized_power": 192,
        "tss": 72,
        "hr_drift": 2.5,
    },
    {
        "date": "2026-01-18",
        "intensity_factor": 0.75,
        "total_time": 5400,
        "zone_percentages": {"Z1": 0.02, "Z2": 0.15, "Z3": 0.30, "Z4": 0.35, "Z5": 0.18},
        "avg_heartrate": 160,
        "max_heartrate": 180,
        "avg_power": 280,
        "normalized_power": 300,
        "tss": 155,
        "hr_drift": 8.0,
    },
    {
        "date": "2026-01-19",
        "intensity_factor": 0.56,
        "total_time": 3700,
        "zone_percentages": {"Z1": 0.07, "Z2": 0.69, "Z3": 0.24},
        "avg_heartrate": 134,
        "max_heartrate": 154,
        "avg_power": 182,
        "normalized_power": 186,
        "tss": 64,
        "hr_drift": 1.8,
    },
]


# Scenario 2: Elevated easy-ride strain
# A cyclist showing elevated HR and cardiac cost during easy rides.
# Pattern: stable baseline, then easy rides with HR 8-12 bpm higher than expected
# Expected: 2-3 easy rides flagged, classification = non_training_fatigue_likely
SCENARIO_ELEVATED_STRAIN_WEEK = [
    {
        "date": "2026-01-08",
        "intensity_factor": 0.55,
        "total_time": 3600,
        "zone_percentages": {"Z1": 0.05, "Z2": 0.70, "Z3": 0.25},
        "avg_heartrate": 135,
        "max_heartrate": 155,
        "avg_power": 180,
        "normalized_power": 185,
        "tss": 65,
        "hr_drift": 2.0,
    },
    {
        "date": "2026-01-09",
        "intensity_factor": 0.57,
        "total_time": 3900,
        "zone_percentages": {"Z1": 0.08, "Z2": 0.65, "Z3": 0.27},
        "avg_heartrate": 136,
        "max_heartrate": 156,
        "avg_power": 185,
        "normalized_power": 190,
        "tss": 70,
        "hr_drift": 2.5,
    },
    {
        "date": "2026-01-10",
        "intensity_factor": 0.75,
        "total_time": 5400,
        "zone_percentages": {"Z1": 0.02, "Z2": 0.15, "Z3": 0.30, "Z4": 0.35, "Z5": 0.18},
        "avg_heartrate": 160,
        "max_heartrate": 180,
        "avg_power": 280,
        "normalized_power": 300,
        "tss": 155,
        "hr_drift": 8.0,
    },
    # Easy ride with elevated HR (8 bpm higher than baseline)
    {
        "date": "2026-01-11",
        "intensity_factor": 0.56,
        "total_time": 3700,
        "zone_percentages": {"Z1": 0.07, "Z2": 0.68, "Z3": 0.25},
        "avg_heartrate": 145,  # +10 from baseline of 135
        "max_heartrate": 165,
        "avg_power": 182,
        "normalized_power": 186,
        "tss": 64,
        "hr_drift": 5.0,  # elevated drift
    },
    # Another easy ride with elevated strain
    {
        "date": "2026-01-12",
        "intensity_factor": 0.58,
        "total_time": 3800,
        "zone_percentages": {"Z1": 0.06, "Z2": 0.67, "Z3": 0.27},
        "avg_heartrate": 146,  # +11 from baseline
        "max_heartrate": 166,
        "avg_power": 184,
        "normalized_power": 188,
        "tss": 66,
        "hr_drift": 5.5,
    },
]


# Scenario 3: Fatigue accumulating
# A cyclist showing multiple (3+) easy rides with elevated strain.
# Expected: classification = fatigue_accumulating
SCENARIO_FATIGUE_ACCUMULATING_WEEK = [
    {
        "date": "2026-01-01",
        "intensity_factor": 0.55,
        "total_time": 3600,
        "zone_percentages": {"Z1": 0.05, "Z2": 0.70, "Z3": 0.25},
        "avg_heartrate": 135,
        "max_heartrate": 155,
        "avg_power": 180,
        "normalized_power": 185,
        "tss": 65,
        "hr_drift": 2.0,
    },
    {
        "date": "2026-01-02",
        "intensity_factor": 0.60,
        "total_time": 4200,
        "zone_percentages": {"Z1": 0.08, "Z2": 0.65, "Z3": 0.27},
        "avg_heartrate": 138,
        "max_heartrate": 158,
        "avg_power": 195,
        "normalized_power": 200,
        "tss": 78,
        "hr_drift": 3.0,
    },
    {
        "date": "2026-01-03",
        "intensity_factor": 0.78,
        "total_time": 5400,
        "zone_percentages": {"Z1": 0.02, "Z2": 0.12, "Z3": 0.28, "Z4": 0.38, "Z5": 0.20},
        "avg_heartrate": 162,
        "max_heartrate": 182,
        "avg_power": 290,
        "normalized_power": 310,
        "tss": 165,
        "hr_drift": 9.0,
    },
    # Easy ride 1: elevated strain
    {
        "date": "2026-01-04",
        "intensity_factor": 0.57,
        "total_time": 3700,
        "zone_percentages": {"Z1": 0.07, "Z2": 0.68, "Z3": 0.25},
        "avg_heartrate": 147,  # +12 from baseline of 135
        "max_heartrate": 167,
        "avg_power": 182,
        "normalized_power": 186,
        "tss": 64,
        "hr_drift": 6.0,
    },
    # Easy ride 2: elevated strain
    {
        "date": "2026-01-05",
        "intensity_factor": 0.59,
        "total_time": 3800,
        "zone_percentages": {"Z1": 0.06, "Z2": 0.66, "Z3": 0.28},
        "avg_heartrate": 148,  # +13 from baseline
        "max_heartrate": 168,
        "avg_power": 184,
        "normalized_power": 188,
        "tss": 66,
        "hr_drift": 6.5,
    },
    # Easy ride 3: elevated strain
    {
        "date": "2026-01-06",
        "intensity_factor": 0.56,
        "total_time": 3600,
        "zone_percentages": {"Z1": 0.08, "Z2": 0.67, "Z3": 0.25},
        "avg_heartrate": 149,  # +14 from baseline
        "max_heartrate": 169,
        "avg_power": 180,
        "normalized_power": 184,
        "tss": 62,
        "hr_drift": 7.0,
    },
]


# Scenario 4: Insufficient data (too few rides)
# Represents early in a training block or limited activity data.
# Expected: classification = neutral_noisy, gating = ineligible
SCENARIO_INSUFFICIENT_RIDES = [
    {
        "date": "2026-01-20",
        "intensity_factor": 0.60,
        "total_time": 3900,
        "zone_percentages": {"Z1": 0.08, "Z2": 0.65, "Z3": 0.27},
        "avg_heartrate": 138,
        "max_heartrate": 158,
        "avg_power": 195,
        "normalized_power": 200,
        "tss": 78,
        "hr_drift": 3.0,
    },
    {
        "date": "2026-01-21",
        "intensity_factor": 0.58,
        "total_time": 3700,
        "zone_percentages": {"Z1": 0.07, "Z2": 0.69, "Z3": 0.24},
        "avg_heartrate": 134,
        "max_heartrate": 154,
        "avg_power": 182,
        "normalized_power": 186,
        "tss": 64,
        "hr_drift": 1.8,
    },
    # Only 2 rides: insufficient for rolling window (needs 5+)
]


# Scenario 5: Skewed training load
# One workout is >60% of weekly TSS.
# Expected: load context = unreliable, classification = neutral_noisy
SCENARIO_SKEWED_TSS_WEEK = [
    {
        "date": "2026-01-22",
        "intensity_factor": 0.55,
        "total_time": 3600,
        "zone_percentages": {"Z1": 0.05, "Z2": 0.70, "Z3": 0.25},
        "avg_heartrate": 135,
        "max_heartrate": 155,
        "avg_power": 180,
        "normalized_power": 185,
        "tss": 50,
        "hr_drift": 2.0,
    },
    {
        "date": "2026-01-23",
        "intensity_factor": 0.82,
        "total_time": 7200,
        "zone_percentages": {"Z1": 0.01, "Z2": 0.05, "Z3": 0.20, "Z4": 0.42, "Z5": 0.32},
        "avg_heartrate": 168,
        "max_heartrate": 188,
        "avg_power": 305,
        "normalized_power": 330,
        "tss": 300,  # > 60% of ~500 total
        "hr_drift": 12.0,
    },
    {
        "date": "2026-01-24",
        "intensity_factor": 0.58,
        "total_time": 3800,
        "zone_percentages": {"Z1": 0.06, "Z2": 0.68, "Z3": 0.26},
        "avg_heartrate": 136,
        "max_heartrate": 156,
        "avg_power": 188,
        "normalized_power": 192,
        "tss": 70,
        "hr_drift": 2.5,
    },
    {
        "date": "2026-01-25",
        "intensity_factor": 0.56,
        "total_time": 3700,
        "zone_percentages": {"Z1": 0.07, "Z2": 0.69, "Z3": 0.24},
        "avg_heartrate": 134,
        "max_heartrate": 154,
        "avg_power": 182,
        "normalized_power": 186,
        "tss": 55,
        "hr_drift": 1.8,
    },
    {
        "date": "2026-01-26",
        "intensity_factor": 0.57,
        "total_time": 3900,
        "zone_percentages": {"Z1": 0.08, "Z2": 0.65, "Z3": 0.27},
        "avg_heartrate": 138,
        "max_heartrate": 158,
        "avg_power": 195,
        "normalized_power": 200,
        "tss": 60,
        "hr_drift": 3.0,
    },
]


# Scenario 6: Long history (21+ days) for baseline establishment
# Used to test history gating and baseline computation over extended periods.
def generate_stable_history_month():
    """Generate 30 days of stable, realistic cycling data.
    
    Returns a list of ride dicts suitable for history gating and baseline tests.
    """
    rides = []
    import datetime
    
    base_date = datetime.datetime(2025, 12, 1)
    
    # Simple pattern: 4-5 rides per week, mostly easy with occasional hard session
    patterns = [
        # Mon: easy
        {"if": 0.55, "dur": 3600, "z": {"Z1": 0.05, "Z2": 0.70, "Z3": 0.25}, "hr": 135, "power": 180, "tss": 65},
        # Tue: easy-moderate
        {"if": 0.60, "dur": 4200, "z": {"Z1": 0.08, "Z2": 0.65, "Z3": 0.27}, "hr": 138, "power": 195, "tss": 78},
        # Wed: hard
        {"if": 0.78, "dur": 5400, "z": {"Z1": 0.02, "Z2": 0.12, "Z3": 0.28, "Z4": 0.38, "Z5": 0.20}, "hr": 162, "power": 290, "tss": 165},
        # Thu: easy
        {"if": 0.57, "dur": 3700, "z": {"Z1": 0.07, "Z2": 0.68, "Z3": 0.25}, "hr": 134, "power": 182, "tss": 64},
        # Fri: rest (no ride)
        None,
        # Sat: easy
        {"if": 0.56, "dur": 3600, "z": {"Z1": 0.06, "Z2": 0.70, "Z3": 0.24}, "hr": 136, "power": 180, "tss": 62},
        # Sun: moderate
        {"if": 0.62, "dur": 4800, "z": {"Z1": 0.06, "Z2": 0.62, "Z3": 0.32}, "hr": 140, "power": 205, "tss": 85},
    ]
    
    for i in range(30):
        current_date = base_date + datetime.timedelta(days=i)
        day_of_week = i % 7
        pattern = patterns[day_of_week]
        
        if pattern is None:
            continue
        
        # Add minor variation
        hr_var = (i % 3) - 1  # -1, 0, or +1
        power_var = (i % 5) - 2  # -2 to +2
        
        ride = {
            "date": current_date.strftime("%Y-%m-%d"),
            "intensity_factor": pattern["if"],
            "total_time": pattern["dur"],
            "zone_percentages": pattern["z"],
            "avg_heartrate": pattern["hr"] + hr_var,
            "max_heartrate": pattern["hr"] + 20 + hr_var,
            "avg_power": pattern["power"] + power_var,
            "normalized_power": pattern["power"] + power_var + 5,
            "tss": pattern["tss"],
            "hr_drift": 2.0 + (i % 4),
        }
        rides.append(ride)
    
    return rides


__all__ = [
    "SCENARIO_STABLE_WEEK",
    "SCENARIO_ELEVATED_STRAIN_WEEK",
    "SCENARIO_FATIGUE_ACCUMULATING_WEEK",
    "SCENARIO_INSUFFICIENT_RIDES",
    "SCENARIO_SKEWED_TSS_WEEK",
    "generate_stable_history_month",
]
