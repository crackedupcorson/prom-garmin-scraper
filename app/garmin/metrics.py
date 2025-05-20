from prometheus_client.core import Gauge
class Metrics(object):
    metrics = {}

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

    all_metrics = []

    def collect(self):
        self.all_metrics.append(self.heart_metrics)
        self.all_metrics.append(self.battery_metrics)
        self.all_metrics.append(self.stress_metrics)
        self.all_metrics.append(self.oxygen_metrics)
        self.all_metrics.append(self.active_metrics)
        self.all_metrics.append(self.misc_metrics)
        for metrics in self.all_metrics:
            for metric in metrics:
                name = metric.split("|")[0]
                desc = metric.split("|")[1]
                self.metrics[name] = Gauge(name, desc)

    def populate_metrics(self, dailies):
        for metrics in self.all_metrics:
            for metric in metrics:
                key = metric.split("|")[0]
                val = dailies.get(key)
                if val is None:
                    print(f"Value for {key} is null")
                if val is not None:
                    self.metrics[key].set(val)