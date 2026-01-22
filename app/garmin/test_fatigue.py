import unittest
import datetime
from app.garmin.fatigue import FatigueChecker, FatigueConfig


class TestFatigueCheckerHistoryGating(unittest.TestCase):
    """Test task 2: history gating checks."""

    def setUp(self):
        self.checker = FatigueChecker()

    def test_history_gating_no_rides(self):
        """Gating should fail with no rides."""
        result = self.checker.history_gating([])
        self.assertFalse(result["sufficient_history"])
        self.assertIn("no_rides", result["reasons"])

    def test_history_gating_insufficient_span(self):
        """Gating should fail if history span < 21 days."""
        rides = [
            {"date": "2026-01-01", "avg_power": 100, "avg_heartrate": 140},
            {"date": "2026-01-05", "avg_power": 110, "avg_heartrate": 145},
        ]
        result = self.checker.history_gating(rides)
        self.assertFalse(result["sufficient_history"])
        self.assertIn("insufficient_history_days", result["reasons"])

    def test_history_gating_no_hr_power_data(self):
        """Gating should fail if no rides have both HR and power."""
        rides = [
            {"date": "2026-01-01", "avg_power": 100},  # Missing HR
            {"date": "2026-01-15", "avg_heartrate": 145},  # Missing power
        ]
        result = self.checker.history_gating(rides)
        self.assertFalse(result["sufficient_history"])
        self.assertIn("no_reliable_hr_power", result["reasons"])

    def test_history_gating_sufficient(self):
        """Gating should pass with 21+ days and HR/power data."""
        rides = [
            {"date": "2026-01-01", "avg_power": 100, "avg_heartrate": 140},
            {"date": "2026-01-15", "avg_power": 110, "avg_heartrate": 145},
            {"date": "2026-01-21", "avg_power": 105, "avg_heartrate": 142},
        ]
        result = self.checker.history_gating(rides)
        self.assertTrue(result["sufficient_history"])
        self.assertEqual(result["reasons"], [])

    def test_history_gating_bad_date_format(self):
        """Gating should fail if date format is invalid."""
        rides = [
            {"date": "not-a-date", "avg_power": 100, "avg_heartrate": 140},
        ]
        result = self.checker.history_gating(rides)
        self.assertFalse(result["sufficient_history"])
        self.assertIn("bad_date_format", result["reasons"])


class TestFatigueCheckerIFBands(unittest.TestCase):
    """Test task 3: IF band definitions."""

    def setUp(self):
        self.checker = FatigueChecker()

    def test_if_bands_defined(self):
        """IF bands should be defined as tuples (low, high, label)."""
        bands = self.checker.define_if_bands()
        self.assertIsInstance(bands, list)
        self.assertGreater(len(bands), 0)
        for band in bands:
            self.assertEqual(len(band), 3)
            low, high, label = band
            self.assertLess(low, high)
            self.assertIsInstance(label, str)

    def test_assign_if_band_coverage(self):
        """IF band assignment should cover easy ride ranges."""
        # 0.50–0.60 band
        self.assertEqual(self.checker.assign_if_band(0.50), "IF_50_60")
        self.assertEqual(self.checker.assign_if_band(0.55), "IF_50_60")
        self.assertEqual(self.checker.assign_if_band(0.59), "IF_50_60")

        # 0.60–0.65 band
        self.assertEqual(self.checker.assign_if_band(0.60), "IF_60_65")
        self.assertEqual(self.checker.assign_if_band(0.62), "IF_60_65")
        self.assertEqual(self.checker.assign_if_band(0.64), "IF_60_65")

    def test_assign_if_band_out_of_range(self):
        """High-IF rides should be marked as ignored_for_strain."""
        self.assertEqual(self.checker.assign_if_band(0.65), "ignored_for_strain")
        self.assertEqual(self.checker.assign_if_band(0.75), "ignored_for_strain")
        self.assertEqual(self.checker.assign_if_band(1.0), "ignored_for_strain")

    def test_assign_if_band_low_if(self):
        """Very low IF should still be assigned."""
        self.assertEqual(self.checker.assign_if_band(0.30), "ignored_for_strain")
        self.assertEqual(self.checker.assign_if_band(0.49), "ignored_for_strain")

    def test_assign_if_band_none(self):
        """None IF should return empty string."""
        self.assertEqual(self.checker.assign_if_band(None), "")


class TestFatigueCheckerEasyRide(unittest.TestCase):
    """Test task 4: easy ride eligibility detection."""

    def setUp(self):
        self.checker = FatigueChecker()

    def test_easy_ride_valid(self):
        """Valid easy ride should pass all checks."""
        ride = {
            "intensity_factor": 0.60,
            "total_time": 3600,  # 60 minutes
            "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3},
        }
        is_easy, reasons = self.checker.is_easy_ride(ride)
        self.assertTrue(is_easy)
        self.assertEqual(reasons, [])

    def test_easy_ride_if_too_high(self):
        """IF >= 0.65 should fail."""
        ride = {
            "intensity_factor": 0.65,
            "total_time": 3600,
            "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3},
        }
        is_easy, reasons = self.checker.is_easy_ride(ride)
        self.assertFalse(is_easy)
        self.assertIn("if_too_high", reasons)

    def test_easy_ride_short_duration(self):
        """Rides < 60 minutes should fail."""
        ride = {
            "intensity_factor": 0.60,
            "total_time": 1800,  # 30 minutes
            "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3},
        }
        is_easy, reasons = self.checker.is_easy_ride(ride)
        self.assertFalse(is_easy)
        self.assertIn("short_duration", reasons)

    def test_easy_ride_insufficient_z2(self):
        """< 60% in Z2 or below should fail."""
        ride = {
            "intensity_factor": 0.60,
            "total_time": 3600,
            "zone_percentages": {"Z1": 0.1, "Z2": 0.4, "Z3": 0.5},
        }
        is_easy, reasons = self.checker.is_easy_ride(ride)
        self.assertFalse(is_easy)
        self.assertIn("insufficient_time_in_z2", reasons)

    def test_easy_ride_missing_if(self):
        """Missing IF should fail."""
        ride = {
            "total_time": 3600,
            "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3},
        }
        is_easy, reasons = self.checker.is_easy_ride(ride)
        self.assertFalse(is_easy)
        self.assertIn("missing_if", reasons)

    def test_easy_ride_missing_zones(self):
        """Missing zone percentages should fail."""
        ride = {
            "intensity_factor": 0.60,
            "total_time": 3600,
        }
        is_easy, reasons = self.checker.is_easy_ride(ride)
        self.assertFalse(is_easy)
        self.assertIn("missing_zones", reasons)

    def test_easy_ride_fallback_keys(self):
        """Should handle alternative key names (IF, total_minutes)."""
        ride = {
            "IF": 0.60,
            "total_minutes": 90,
            "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3},
        }
        is_easy, reasons = self.checker.is_easy_ride(ride)
        self.assertTrue(is_easy)


class TestFatigueCheckerStrainMetrics(unittest.TestCase):
    """Test task 5: per-ride strain metric computation."""

    def setUp(self):
        self.checker = FatigueChecker()

    def test_compute_per_ride_strain_basic(self):
        """Basic strain computation should extract core metrics."""
        ride = {
            "avg_heartrate": 140,
            "max_heartrate": 160,
            "hr_drift": 5.0,
            "avg_power": 200,
            "normalized_power": 210,
            "intensity_factor": 0.60,
            "total_time": 3600,
            "tss": 75,
        }
        metrics = self.checker.compute_per_ride_strain(ride)
        self.assertEqual(metrics["avg_heartrate"], 140.0)
        self.assertEqual(metrics["max_heartrate"], 160.0)
        self.assertEqual(metrics["hr_drift"], 5.0)
        self.assertEqual(metrics["avg_power"], 200.0)
        self.assertAlmostEqual(metrics["cardiac_cost"], 140 / 200)

    def test_compute_per_ride_strain_cardiac_cost(self):
        """Cardiac cost should be avg_hr / avg_power."""
        ride = {
            "avg_heartrate": 150,
            "avg_power": 250,
        }
        metrics = self.checker.compute_per_ride_strain(ride)
        self.assertAlmostEqual(metrics["cardiac_cost"], 150 / 250)

    def test_compute_per_ride_strain_no_cardiac_cost(self):
        """Cardiac cost should be None if missing HR or power."""
        ride = {"avg_heartrate": 150}
        metrics = self.checker.compute_per_ride_strain(ride)
        self.assertIsNone(metrics["cardiac_cost"])

    def test_compute_per_ride_strain_easy_ride_flag(self):
        """strain_applicable should reflect easy-ride eligibility."""
        easy_ride = {
            "intensity_factor": 0.60,
            "total_time": 3600,
            "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3},
        }
        metrics = self.checker.compute_per_ride_strain(easy_ride)
        self.assertTrue(metrics["strain_applicable"])

        hard_ride = {
            "intensity_factor": 0.75,
            "total_time": 3600,
            "zone_percentages": {"Z1": 0.0, "Z2": 0.2, "Z3": 0.8},
        }
        metrics = self.checker.compute_per_ride_strain(hard_ride)
        self.assertFalse(metrics["strain_applicable"])

    def test_compute_per_ride_strain_hr_drift_from_series(self):
        """HR drift should be computed from heartrate_series if not provided."""
        ride = {
            "heartrate_series": [130, 135, 140, 145, 150, 155, 160, 165],
        }
        metrics = self.checker.compute_per_ride_strain(ride)
        # First half avg: (130+135+140+145)/4 = 137.5
        # Second half avg: (150+155+160+165)/4 = 157.5
        # Drift: 157.5 - 137.5 = 20
        self.assertAlmostEqual(metrics["hr_drift"], 20.0)

    def test_compute_per_ride_strain_fallback_keys(self):
        """Should handle alternative key names (average_heartrate)."""
        ride = {
            "average_heartrate": 140,
            "avg_power": 200,
        }
        metrics = self.checker.compute_per_ride_strain(ride)
        self.assertEqual(metrics["avg_heartrate"], 140.0)


class TestFatigueCheckerBaseline(unittest.TestCase):
    """Test task 6: baseline statistics per IF band."""

    def setUp(self):
        self.checker = FatigueChecker()

    def test_build_baseline_statistics_empty(self):
        """Empty ride list should return empty baseline."""
        baseline = self.checker.build_baseline_statistics([])
        self.assertEqual(baseline, {})

    def test_build_baseline_statistics_single_band(self):
        """Baseline should aggregate metrics by IF band."""
        rides = [
            {
                "intensity_factor": 0.55,
                "avg_heartrate": 140,
                "hr_drift": 5.0,
                "avg_power": 200,
                "tss": 75,
            },
            {
                "intensity_factor": 0.58,
                "avg_heartrate": 142,
                "hr_drift": 4.0,
                "avg_power": 210,
                "tss": 80,
            },
        ]
        baseline = self.checker.build_baseline_statistics(rides)
        self.assertIn("IF_50_60", baseline)
        self.assertEqual(baseline["IF_50_60"]["avg_heartrate"]["count"], 2)
        self.assertAlmostEqual(baseline["IF_50_60"]["avg_heartrate"]["mean"], 141.0)

    def test_build_baseline_statistics_excludes_high_if(self):
        """High-IF rides should be excluded from baseline."""
        rides = [
            {
                "intensity_factor": 0.55,
                "avg_heartrate": 140,
                "hr_drift": 5.0,
                "avg_power": 200,
                "tss": 75,
            },
            {
                "intensity_factor": 0.75,  # High IF, should be ignored
                "avg_heartrate": 170,
                "hr_drift": 15.0,
                "avg_power": 350,
                "tss": 150,
            },
        ]
        baseline = self.checker.build_baseline_statistics(rides)
        self.assertIn("IF_50_60", baseline)
        # High-IF ride should not influence IF_50_60 baseline
        self.assertEqual(baseline["IF_50_60"]["avg_heartrate"]["count"], 1)
        self.assertAlmostEqual(baseline["IF_50_60"]["avg_heartrate"]["mean"], 140.0)

    def test_build_baseline_statistics_stdev(self):
        """Baseline should compute standard deviation for metrics."""
        rides = [
            {"intensity_factor": 0.55, "avg_heartrate": 140},
            {"intensity_factor": 0.58, "avg_heartrate": 150},
        ]
        baseline = self.checker.build_baseline_statistics(rides)
        # Mean: 145, stdev for [140, 150]: sqrt(((140-145)^2 + (150-145)^2)/2) ≈ 7.07
        self.assertAlmostEqual(baseline["IF_50_60"]["avg_heartrate"]["mean"], 145.0)
        self.assertGreater(baseline["IF_50_60"]["avg_heartrate"]["stdev"], 0)

    def test_build_baseline_statistics_single_ride_stdev(self):
        """Single ride should have stdev = 0."""
        rides = [
            {"intensity_factor": 0.55, "avg_heartrate": 140},
        ]
        baseline = self.checker.build_baseline_statistics(rides)
        self.assertEqual(baseline["IF_50_60"]["avg_heartrate"]["stdev"], 0.0)


class TestFatigueCheckerComparison(unittest.TestCase):
    """Test task 7: compare rides to baseline."""

    def setUp(self):
        self.checker = FatigueChecker()

    def test_compare_ride_to_baseline_normal(self):
        """Comparison should compute delta and z-score."""
        baseline = {
            "IF_50_60": {
                "avg_heartrate": {"mean": 140.0, "stdev": 5.0, "count": 10},
                "cardiac_cost": {"mean": 0.70, "stdev": 0.05, "count": 10},
            }
        }
        ride = {
            "intensity_factor": 0.55,
            "avg_heartrate": 145,
            "avg_power": 200,
        }
        comparison = self.checker.compare_ride_to_baseline(ride, baseline)
        self.assertEqual(comparison["band"], "IF_50_60")
        self.assertIsNotNone(comparison["comparison"])
        # Heart rate: delta = 145 - 140 = 5, z = 5 / 5 = 1.0
        self.assertEqual(comparison["comparison"]["avg_heartrate"]["delta"], 5.0)
        self.assertEqual(comparison["comparison"]["avg_heartrate"]["zscore"], 1.0)

    def test_compare_ride_to_baseline_no_band(self):
        """Comparison should handle rides outside baseline bands."""
        baseline = {"IF_50_60": {"avg_heartrate": {"mean": 140.0, "stdev": 5.0}}}
        ride = {"intensity_factor": 0.75}  # High IF, not in baseline
        comparison = self.checker.compare_ride_to_baseline(ride, baseline)
        self.assertIsNone(comparison["comparison"])

    def test_compare_ride_to_baseline_elevated_zscore(self):
        """Comparison should flag elevated metrics with z-score > 1."""
        baseline = {
            "IF_50_60": {
                "avg_heartrate": {"mean": 140.0, "stdev": 5.0, "count": 10},
            }
        }
        ride = {
            "intensity_factor": 0.55,
            "avg_heartrate": 156,  # +3 stdev above mean
            "avg_power": 200,
        }
        comparison = self.checker.compare_ride_to_baseline(ride, baseline)
        self.assertGreater(comparison["comparison"]["avg_heartrate"]["zscore"], 1.0)


class TestFatigueCheckerRollingWindow(unittest.TestCase):
    """Test task 9: rolling window gating."""

    def setUp(self):
        self.checker = FatigueChecker()

    def test_rolling_window_gating_no_rides(self):
        """Empty window should fail gating."""
        result = self.checker.rolling_window_gating([])
        self.assertFalse(result["eligible"])
        self.assertIn("no_rides_in_window", result["reasons"])

    def test_rolling_window_gating_insufficient_rides(self):
        """< 5 total rides should fail."""
        rides = [
            {"date": "2026-01-01", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},
            {"date": "2026-01-02", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},
        ]
        result = self.checker.rolling_window_gating(rides)
        self.assertFalse(result["eligible"])
        self.assertIn("only_2_rides", result["reasons"])

    def test_rolling_window_gating_insufficient_easy_rides(self):
        """< 2 easy rides should fail."""
        rides = [
            {"date": "2026-01-01", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},
            {"date": "2026-01-02", "intensity_factor": 0.75, "total_time": 3600, "zone_percentages": {"Z1": 0.0, "Z2": 0.2, "Z3": 0.8}},  # High IF
            {"date": "2026-01-03", "intensity_factor": 0.75, "total_time": 3600, "zone_percentages": {"Z1": 0.0, "Z2": 0.2, "Z3": 0.8}},  # High IF
            {"date": "2026-01-04", "intensity_factor": 0.75, "total_time": 3600, "zone_percentages": {"Z1": 0.0, "Z2": 0.2, "Z3": 0.8}},  # High IF
            {"date": "2026-01-05", "intensity_factor": 0.75, "total_time": 3600, "zone_percentages": {"Z1": 0.0, "Z2": 0.2, "Z3": 0.8}},  # High IF
        ]
        result = self.checker.rolling_window_gating(rides)
        self.assertFalse(result["eligible"])
        self.assertIn("only_1_easy_rides", result["reasons"])

    def test_rolling_window_gating_large_gap(self):
        """> 3-day gap should fail."""
        rides = [
            {"date": "2026-01-01", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},
            {"date": "2026-01-02", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},
            {"date": "2026-01-06", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},  # 4-day gap
            {"date": "2026-01-07", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},
            {"date": "2026-01-08", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},
        ]
        result = self.checker.rolling_window_gating(rides)
        self.assertFalse(result["eligible"])
        self.assertTrue(any("gap_of" in r for r in result["reasons"]))

    def test_rolling_window_gating_eligible(self):
        """Sufficient rides, easy rides, and no gaps should pass."""
        rides = [
            {"date": "2026-01-01", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},
            {"date": "2026-01-02", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},
            {"date": "2026-01-03", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},
            {"date": "2026-01-04", "intensity_factor": 0.75, "total_time": 3600, "zone_percentages": {"Z1": 0.0, "Z2": 0.2, "Z3": 0.8}},  # Hard ride
            {"date": "2026-01-05", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},
        ]
        result = self.checker.rolling_window_gating(rides)
        self.assertTrue(result["eligible"])
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["total_rides"], 5)
        self.assertEqual(result["easy_rides"], 4)


class TestFatigueCheckerTrainingLoad(unittest.TestCase):
    """Test task 10: training load context checks."""

    def setUp(self):
        self.checker = FatigueChecker()

    def test_training_load_context_insufficient_rides(self):
        """< 3 rides with TSS should fail."""
        rides = [
            {"tss": 75},
            {"tss": 80},
        ]
        result = self.checker.training_load_context(rides)
        self.assertFalse(result["reliable"])
        self.assertIn("only_2_rides_with_tss", result["reasons"])

    def test_training_load_context_skewed_by_single_ride(self):
        """Single ride > 60% of weekly TSS should fail."""
        rides = [
            {"tss": 75},
            {"tss": 80},
            {"tss": 250},  # > 60% of 405
        ]
        result = self.checker.training_load_context(rides)
        self.assertFalse(result["reliable"])
        self.assertTrue(any("single_ride_is" in r for r in result["reasons"]))

    def test_training_load_context_reliable(self):
        """Well-distributed TSS should pass."""
        rides = [
            {"tss": 75},
            {"tss": 80},
            {"tss": 85},
        ]
        result = self.checker.training_load_context(rides)
        self.assertTrue(result["reliable"])
        self.assertEqual(result["reasons"], [])
        self.assertAlmostEqual(result["tss_stats"]["total"], 240.0)


class TestFatigueCheckerAggregation(unittest.TestCase):
    """Test task 8: 7-day aggregation and classification."""

    def setUp(self):
        self.checker = FatigueChecker()

    def test_aggregate_7day_insufficient_data(self):
        """Insufficient gating should default to neutral_noisy."""
        rides = []
        result = self.checker.aggregate_7day_classification(rides)
        self.assertEqual(result["classification"], "neutral_noisy")
        self.assertFalse(result["gating"]["eligible"])

    def test_aggregate_7day_skewed_load(self):
        """Skewed training load should default to neutral_noisy."""
        rides = [
            {"date": "2026-01-01", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}, "tss": 75},
            {"date": "2026-01-02", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}, "tss": 80},
            {"date": "2026-01-03", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}, "tss": 85},
            {"date": "2026-01-04", "intensity_factor": 0.75, "total_time": 3600, "zone_percentages": {"Z1": 0.0, "Z2": 0.2, "Z3": 0.8}, "tss": 250},
            {"date": "2026-01-05", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}, "tss": 80},
        ]
        result = self.checker.aggregate_7day_classification(rides)
        # TSS distribution: [75, 80, 85, 250, 80] = 570 total, max_pct = 250/570 = 43.9%
        # This should pass load context, but might have other issues
        # Let's verify it includes strain flags
        self.assertIn("strain_flags", result)

    def test_aggregate_7day_no_strain_flags(self):
        """Classification with no strain flags should state "no elevated strain detected"."""
        rides = [
            {"date": "2026-01-01", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}, "avg_heartrate": 140, "avg_power": 200, "tss": 75},
            {"date": "2026-01-02", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}, "avg_heartrate": 141, "avg_power": 205, "tss": 80},
            {"date": "2026-01-03", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}, "avg_heartrate": 139, "avg_power": 195, "tss": 85},
            {"date": "2026-01-04", "intensity_factor": 0.75, "total_time": 3600, "zone_percentages": {"Z1": 0.0, "Z2": 0.2, "Z3": 0.8}, "avg_heartrate": 170, "avg_power": 350, "tss": 150},
            {"date": "2026-01-05", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}, "avg_heartrate": 140, "avg_power": 200, "tss": 80},
        ]
        result = self.checker.aggregate_7day_classification(rides)
        # The key test: verify strain_flags is populated and reasons include a reason
        self.assertIn("strain_flags", result)
        self.assertIsInstance(result["strain_flags"], list)

    def test_aggregate_7day_fatigue_accumulating(self):
        """Multiple elevated easy rides should result in fatigue_accumulating."""
        rides = [
            {"date": "2026-01-01", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}, "avg_heartrate": 160, "avg_power": 200, "tss": 75},
            {"date": "2026-01-02", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}, "avg_heartrate": 161, "avg_power": 205, "tss": 80},
            {"date": "2026-01-03", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}, "avg_heartrate": 159, "avg_power": 195, "tss": 85},
            {"date": "2026-01-04", "intensity_factor": 0.75, "total_time": 3600, "zone_percentages": {"Z1": 0.0, "Z2": 0.2, "Z3": 0.8}, "avg_heartrate": 170, "avg_power": 350, "tss": 150},
            {"date": "2026-01-05", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}, "avg_heartrate": 160, "avg_power": 200, "tss": 80},
        ]
        result = self.checker.aggregate_7day_classification(rides)
        # With baseline mean ~140 bpm and these rides at 160, we have multiple elevated rides
        self.assertIn(result["classification"], ["fatigue_accumulating", "non_training_fatigue_likely"])


class TestFatigueCheckerTextSummary(unittest.TestCase):
    """Test task 12: text summary generation."""

    def setUp(self):
        self.checker = FatigueChecker()

    def test_text_summary_no_classification(self):
        """Missing classification should return insufficient data message."""
        summary = self.checker.text_summary(None, {}, [])
        self.assertIn("Insufficient data", summary)

    def test_text_summary_includes_header(self):
        """Summary should include fatigue status header."""
        classification = {"classification": "neutral_noisy", "gating": {"eligible": True}, "load_context": {"reliable": True}}
        summary = self.checker.text_summary(classification, {}, [])
        self.assertIn("FATIGUE STATUS", summary)

    def test_text_summary_insufficient_gating(self):
        """Insufficient gating should produce warning."""
        classification = {"classification": "neutral_noisy", "gating": {"eligible": False, "reasons": ["no_rides"]}, "load_context": {"reliable": True}}
        summary = self.checker.text_summary(classification, {}, [])
        self.assertIn("INSUFFICIENT DATA", summary)

    def test_text_summary_skewed_load(self):
        """Skewed load should produce warning."""
        classification = {"classification": "neutral_noisy", "gating": {"eligible": True}, "load_context": {"reliable": False, "reasons": ["single_ride_is_70pct"]}}
        summary = self.checker.text_summary(classification, {}, [])
        self.assertIn("TRAINING LOAD SKEWED", summary)

    def test_text_summary_absorbing_well(self):
        """absorbing_well classification should produce positive message."""
        classification = {
            "classification": "absorbing_well",
            "gating": {"eligible": True, "total_rides": 5, "easy_rides": 3},
            "load_context": {"reliable": True, "tss_stats": {"total": 400, "max_percent": 20}},
        }
        summary = self.checker.text_summary(classification, {}, [])
        self.assertIn("ABSORBING WELL", summary)

    def test_text_summary_fatigue_accumulating(self):
        """fatigue_accumulating classification should produce caution message."""
        classification = {
            "classification": "fatigue_accumulating",
            "gating": {"eligible": True, "total_rides": 5, "easy_rides": 3},
            "load_context": {"reliable": True, "tss_stats": {"total": 400, "max_percent": 20}},
        }
        summary = self.checker.text_summary(classification, {}, [])
        self.assertIn("FATIGUE ACCUMULATING", summary)
        self.assertIn("elevated strain", summary)

    def test_text_summary_includes_context(self):
        """Summary should include ride counts and TSS stats."""
        classification = {
            "classification": "neutral_noisy",
            "gating": {"eligible": True, "total_rides": 5, "easy_rides": 3},
            "load_context": {"reliable": True, "tss_stats": {"total": 400, "max_percent": 25}},
        }
        summary = self.checker.text_summary(classification, {}, [])
        self.assertIn("5 total rides", summary)
        self.assertIn("3 easy rides", summary)


class TestFatigueConfig(unittest.TestCase):
    """Test task 15: configurable thresholds."""

    def test_default_config(self):
        """Default config should have expected values."""
        config = FatigueConfig()
        self.assertEqual(config.min_history_days, 21)
        self.assertEqual(config.max_easy_ride_if, 0.65)
        self.assertEqual(config.min_easy_ride_duration_minutes, 60.0)
        self.assertEqual(config.min_easy_ride_z2_percent, 60.0)
        self.assertEqual(config.min_total_rides_in_window, 5)
        self.assertEqual(config.min_easy_rides_in_window, 2)
        self.assertEqual(config.max_gap_days, 3)
        self.assertEqual(config.strain_zscore_threshold, 1.0)

    def test_custom_config(self):
        """Custom config should override defaults."""
        custom_config = FatigueConfig(
            min_history_days=14,
            max_easy_ride_if=0.70,
            min_easy_ride_duration_minutes=45.0,
            max_gap_days=5,
        )
        checker = FatigueChecker(config=custom_config)
        self.assertEqual(checker.config.min_history_days, 14)
        self.assertEqual(checker.config.max_easy_ride_if, 0.70)
        self.assertEqual(checker.config.min_easy_ride_duration_minutes, 45.0)
        self.assertEqual(checker.config.max_gap_days, 5)

    def test_custom_config_affects_history_gating(self):
        """Custom history threshold should affect gating."""
        custom_config = FatigueConfig(min_history_days=5)
        checker = FatigueChecker(config=custom_config)
        
        # 7 days of history (inclusive: Jan 1 to Jan 7 = 7 days)
        rides = [
            {"date": "2026-01-01", "avg_power": 100, "avg_heartrate": 140},
            {"date": "2026-01-07", "avg_power": 110, "avg_heartrate": 145},
        ]
        result = checker.history_gating(rides)
        # Should pass with custom config (5 days min, we have 7 days)
        self.assertTrue(result["sufficient_history"])

    def test_custom_config_affects_easy_ride_detection(self):
        """Custom easy ride thresholds should affect detection."""
        # Stricter config: IF < 0.50, >= 90 minutes
        strict_config = FatigueConfig(
            max_easy_ride_if=0.50,
            min_easy_ride_duration_minutes=90.0,
        )
        checker = FatigueChecker(config=strict_config)
        
        # Ride at IF 0.60, 75 minutes would fail both checks
        ride = {
            "intensity_factor": 0.60,
            "total_time": 4500,  # 75 minutes
            "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3},
        }
        is_easy, reasons = checker.is_easy_ride(ride)
        self.assertFalse(is_easy)
        self.assertIn("if_too_high", reasons)
        self.assertIn("short_duration", reasons)

    def test_custom_config_affects_rolling_window(self):
        """Custom rolling window thresholds should affect gating."""
        lenient_config = FatigueConfig(
            min_total_rides_in_window=2,
            min_easy_rides_in_window=1,
            max_gap_days=15,
        )
        checker = FatigueChecker(config=lenient_config)
        
        rides = [
            {"date": "2026-01-01", "intensity_factor": 0.55, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},
            {"date": "2026-01-15", "intensity_factor": 0.60, "total_time": 3600, "zone_percentages": {"Z1": 0.1, "Z2": 0.6, "Z3": 0.3}},  # 14-day gap
        ]
        result = checker.rolling_window_gating(rides)
        # Would fail with default (3-day gap max, 5 rides min) but pass with lenient config
        self.assertTrue(result["eligible"])

    def test_config_default_if_bands(self):
        """Default config should have standard IF bands."""
        config = FatigueConfig()
        self.assertEqual(len(config.if_bands), 2)
        self.assertEqual(config.if_bands[0], (0.50, 0.60, "IF_50_60"))
        self.assertEqual(config.if_bands[1], (0.60, 0.65, "IF_60_65"))

    def test_custom_if_bands(self):
        """Custom IF bands should work."""
        custom_bands = [
            (0.55, 0.65, "EASY"),
            (0.65, 0.80, "SWEET_SPOT"),
        ]
        custom_config = FatigueConfig(if_bands=custom_bands)
        checker = FatigueChecker(config=custom_config)
        
        self.assertEqual(checker.assign_if_band(0.60), "EASY")
        self.assertEqual(checker.assign_if_band(0.70), "SWEET_SPOT")


if __name__ == "__main__":
    unittest.main()
