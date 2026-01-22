from prometheus_client.core import Gauge
from datetime import datetime 

class Metrics(object):
    metrics = {}
    WORK_START = 9
    WORK_END = 6

    def is_work_hours(self, ts: datetime):
        return ts.weekday() < 5 and self.WORK_START >= ts.hour < self.WORK_END


    active_metrics = [
        "sedentarySeconds|Time spent sedentary",
        "sleepingSeconds|Seconds spent sleeping",
        "activeSeconds|Seconds spent active",
        "highlyActiveSeconds|Time spent highly active",
        "moderateIntensityMinutes|Minutes of moderate intensity activity",
        "vigorousIntensityMinutes|Minutes of vigorous intensity activity"
    ]

    heart_metrics = [
        "minHeartRate|Min heart rate",
        "maxHeartRate|Max heart rate",
        "restingHeartRate|Resting heart rate",
        "lastSevenDaysAvgRestingHeartRate|Seven-day average resting heart rate",
        "heartRateVariability|Heart rate variability (HRV)"
    ]

    battery_metrics = [
        "bodyBatteryHighestValue|Body battery highest value",
        "bodyBatteryLowestValue|Body battery lowest value",
        "bodyBatteryDuringSleep|Body battery recovered during sleep",
        "bodyBatteryAverage|Average body battery level over 24h"
    ]

    stress_metrics = [
        "averageStressLevel|Average stress level",
        "maxStressLevel|Max daily stress level",
        "stressDuration|Total stress duration in seconds",
        "restStressDuration|Stress duration during rest",
        "activityStressDuration|Stress duration during activity",
        "lowStressDuration|Duration of low stress levels",
        "mediumStressDuration|Duration of medium stress levels",
        "highStressDuration|Duration of high stress levels",
        "stressPercentage|Percentage of time spent stressed"
    ]

    oxygen_metrics = [
        "averageSpo2|Average SPO2",
        "lowestSpo2|Lowest SPO2",
        "spo2DuringSleep|Average SPO2 during sleep"
    ]

    misc_metrics = [
        "totalKilocalories|Total consumed calories",
        "activeKilocalories|Active calories burned",
        "bmrKilocalories|Basal metabolic rate calories",
        "totalSteps|Total steps",
        "dailyStepGoal|Daily step goal",
        "totalDistanceMeters|Total distance traveled in meters",
        "floorsAscended|Floors ascended",
        "floorsDescended|Floors descended",
        "intensityMinutesGoal|Daily intensity minutes goal",
        "lastUploadSyncTime|Last upload sync time",
        "durationInMilliseconds|Total duration of wellness data in milliseconds"
    ]

    derived_metrics = [
        "activeToSedentaryRatio|Ratio of active time to sedentary time",
        "highlyActiveToActiveRatio|Ratio of highly active time to total active time",
        "heartRateRange|Range of heart rate (max - min)",
        "restingToMaxHeartRateRatio|Ratio of resting heart rate to max heart rate",
        "stressToActiveRatio|Ratio of stress duration to active time",
        "stressToRestRatio|Ratio of stress during rest to total rest time",
        "bodyBatteryRecovery|Body battery recovery (highest - lowest)",
        "spo2DropDuringSleep|Drop in SPO2 during sleep",
        "stepsToDistanceRatio|Ratio of total steps to total distance traveled",
        "caloriesPerStep|Active calories burned per step"
    ]
    intervals_metrics = [
        
    ]

    fatigue_metrics = [
        "fatigue_history_sufficient|Whether 21+ days of history is available (1=yes, 0=no)",
        "fatigue_window_eligible|Whether rolling window meets gating criteria (1=yes, 0=no)",
        "fatigue_load_context_reliable|Whether TSS distribution is reliable (1=yes, 0=no)",
        "fatigue_classification_neutral_noisy|Classification is neutral_noisy (1=yes, 0=no)",
        "fatigue_classification_absorbing_well|Classification is absorbing_well (1=yes, 0=no)",
        "fatigue_classification_non_training_fatigue|Classification is non_training_fatigue_likely (1=yes, 0=no)",
        "fatigue_classification_fatigue_accumulating|Classification is fatigue_accumulating (1=yes, 0=no)",
        "fatigue_baseline_if_50_60_hr_mean|Baseline avg HR for IF 0.50-0.60 band (bpm)",
        "fatigue_baseline_if_50_60_cardiac_cost_mean|Baseline cardiac cost for IF 0.50-0.60 band (bpm/watt)",
        "fatigue_baseline_if_60_65_hr_mean|Baseline avg HR for IF 0.60-0.65 band (bpm)",
        "fatigue_baseline_if_60_65_cardiac_cost_mean|Baseline cardiac cost for IF 0.60-0.65 band (bpm/watt)",
        "fatigue_easy_rides_count|Number of easy rides in rolling window",
        "fatigue_total_rides_count|Total rides in rolling window",
        "fatigue_tss_weekly_total|Total TSS in rolling window",
        "fatigue_tss_max_percent|Percentage of weekly TSS from highest-TSS ride",
    ]

    all_metrics = []

    def collect(self):
        self.all_metrics.append(self.heart_metrics)
        self.all_metrics.append(self.battery_metrics)
        self.all_metrics.append(self.stress_metrics)
        self.all_metrics.append(self.oxygen_metrics)
        self.all_metrics.append(self.active_metrics)
        self.all_metrics.append(self.misc_metrics)
        self.all_metrics.append(self.derived_metrics)
        self.all_metrics.append(self.fatigue_metrics)
        for metrics in self.all_metrics:
            for metric in metrics:
                name = metric.split("|")[0]
                desc = metric.split("|")[1]
                self.metrics[name] = Gauge(name, desc, ["period"])

    def populate_fatigue_metrics(self, classification: dict, baseline: dict, gating: dict, load_context: dict):
        """Populate Prometheus metrics from fatigue checker classification results.
        
        Args:
            classification: result from FatigueChecker.aggregate_7day_classification()
            baseline: baseline stats dict from FatigueChecker.build_baseline_statistics()
            gating: rolling window gating result
            load_context: training load context result
        """
        if not classification or not gating or not load_context:
            return

        # History sufficiency (1=yes, 0=no)
        history_sufficient = 1 if classification.get("classification") != "neutral_noisy" or gating.get("eligible") else 0
        self.metrics["fatigue_history_sufficient"].labels(period="7d").set(history_sufficient)

        # Window eligibility
        window_eligible = 1 if gating.get("eligible") else 0
        self.metrics["fatigue_window_eligible"].labels(period="7d").set(window_eligible)

        # Load context reliability
        load_reliable = 1 if load_context.get("reliable") else 0
        self.metrics["fatigue_load_context_reliable"].labels(period="7d").set(load_reliable)

        # Classification labels (one-hot encoding)
        class_label = classification.get("classification", "neutral_noisy")
        self.metrics["fatigue_classification_neutral_noisy"].labels(period="7d").set(1 if class_label == "neutral_noisy" else 0)
        self.metrics["fatigue_classification_absorbing_well"].labels(period="7d").set(1 if class_label == "absorbing_well" else 0)
        self.metrics["fatigue_classification_non_training_fatigue"].labels(period="7d").set(1 if class_label == "non_training_fatigue_likely" else 0)
        self.metrics["fatigue_classification_fatigue_accumulating"].labels(period="7d").set(1 if class_label == "fatigue_accumulating" else 0)

        # Baseline stats per IF band
        if_50_60 = baseline.get("IF_50_60", {})
        hr_mean_50_60 = if_50_60.get("avg_heartrate", {}).get("mean")
        self.metrics["fatigue_baseline_if_50_60_hr_mean"].labels(period="7d").set(hr_mean_50_60 or 0)

        cc_mean_50_60 = if_50_60.get("cardiac_cost", {}).get("mean")
        self.metrics["fatigue_baseline_if_50_60_cardiac_cost_mean"].labels(period="7d").set(cc_mean_50_60 or 0)

        if_60_65 = baseline.get("IF_60_65", {})
        hr_mean_60_65 = if_60_65.get("avg_heartrate", {}).get("mean")
        self.metrics["fatigue_baseline_if_60_65_hr_mean"].labels(period="7d").set(hr_mean_60_65 or 0)

        cc_mean_60_65 = if_60_65.get("cardiac_cost", {}).get("mean")
        self.metrics["fatigue_baseline_if_60_65_cardiac_cost_mean"].labels(period="7d").set(cc_mean_60_65 or 0)

        # Rolling window stats
        total_rides = gating.get("total_rides", 0)
        easy_rides = gating.get("easy_rides", 0)
        self.metrics["fatigue_easy_rides_count"].labels(period="7d").set(easy_rides)
        self.metrics["fatigue_total_rides_count"].labels(period="7d").set(total_rides)

        # TSS stats
        tss_stats = load_context.get("tss_stats", {})
        tss_total = tss_stats.get("total", 0)
        tss_max_pct = tss_stats.get("max_percent", 0)
        self.metrics["fatigue_tss_weekly_total"].labels(period="7d").set(tss_total or 0)
        self.metrics["fatigue_tss_max_percent"].labels(period="7d").set(tss_max_pct or 0)

    def populate_metrics(self, dailies):
        now = datetime.now()
        period = "work" if self.is_work_hours(now) else "off_work"
        for metrics in self.all_metrics:
            for metric in metrics:
                key = metric.split("|")[0]
                val = dailies.get(key)
                if key in self.derived_metrics and  val is None:
                    print(f"Value for {key} is null")
                if val is not None:
                    self.metrics[key].labels(period=period).set(val)

        # Derived metrics
        active_seconds = dailies.get("activeSeconds", 0)
        sedentary_seconds = dailies.get("sedentarySeconds", 0)
        if active_seconds and sedentary_seconds:
            active_to_sedentary_ratio = active_seconds / sedentary_seconds
            self.metrics["activeToSedentaryRatio"].labels(period=period).set(active_to_sedentary_ratio)

        highly_active_seconds = dailies.get("highlyActiveSeconds", 0)
        if active_seconds:
            highly_active_to_active_ratio = highly_active_seconds / active_seconds
            self.metrics["highlyActiveToActiveRatio"].labels(period=period).set(highly_active_to_active_ratio)

        max_heart_rate = dailies.get("maxHeartRate", 0)
        min_heart_rate = dailies.get("minHeartRate", 0)
        if max_heart_rate and min_heart_rate:
            heart_rate_range = max_heart_rate - min_heart_rate
            self.metrics["heartRateRange"].labels(period=period).set(heart_rate_range)

        resting_heart_rate = dailies.get("restingHeartRate", 0)
        if max_heart_rate and resting_heart_rate:
            resting_to_max_heart_rate_ratio = resting_heart_rate / max_heart_rate
            self.metrics["restingToMaxHeartRateRatio"].labels(period=period).set(resting_to_max_heart_rate_ratio)

        stress_duration = dailies.get("stressDuration", 0)
        if active_seconds:
            stress_to_active_ratio = stress_duration / active_seconds
            self.metrics["stressToActiveRatio"].labels(period=period).set(stress_to_active_ratio)

        rest_stress_duration = dailies.get("restStressDuration", 0)
        if sedentary_seconds:
            stress_to_rest_ratio = rest_stress_duration / sedentary_seconds
            self.metrics["stressToRestRatio"].labels(period=period).set(stress_to_rest_ratio)

        body_battery_high = dailies.get("bodyBatteryHighestValue", 0)
        body_battery_low = dailies.get("bodyBatteryLowestValue", 0)
        if body_battery_high and body_battery_low:
            body_battery_recovery = body_battery_high - body_battery_low
            self.metrics["bodyBatteryRecovery"].labels(period=period).set(body_battery_recovery)

        average_spo2 = dailies.get("averageSpo2", 0)
        spo2_during_sleep = dailies.get("spo2DuringSleep", 0)
        if average_spo2 and spo2_during_sleep:
            spo2_drop_during_sleep = average_spo2 - spo2_during_sleep
            self.metrics["spo2DropDuringSleep"].labels(period=period).set(spo2_drop_during_sleep)

        total_steps = dailies.get("totalSteps", 0)
        total_distance_meters = dailies.get("totalDistanceMeters", 0)
        if total_steps and total_distance_meters:
            steps_to_distance_ratio = total_steps / total_distance_meters
            self.metrics["stepsToDistanceRatio"].labels(period=period).set(steps_to_distance_ratio)

        active_kilocalories = dailies.get("activeKilocalories", 0)
        if total_steps:
            calories_per_step = active_kilocalories / total_steps
            self.metrics["caloriesPerStep"].labels(period=period).set(calories_per_step)