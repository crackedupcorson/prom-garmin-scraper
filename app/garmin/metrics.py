from prometheus_client.core import Gauge


class Metrics(object):
    metrics = {}

    active_metrics = ["sedentarySeconds|time spend sedentary",
                      "sleepingSeconds|seconds spent sleeping",
                      "activeSeconds|seconds spent active",
                      "highlyActiveSeconds|time spent highly active"]

    heart_metrics = ["minHeartRate|Min heart rate",
                     "maxHeartRate|Max heart rate",
                     "restingHeartRate|Resting heart rate",
                     "lastSevenDaysAvgRestingHeartRate|Sevenday avg heart rate"]

    battery_metrics = ["bodyBatteryHighestValue|Body battery highest value",
                       "bodyBatteryLowestValue|body battery lowest value",
                       "bodyBatteryDuringSleep|Body battery recovered during sleep"]

    stress_metrics = ["averageStressLevel|Average stress level",
                      "maxStressLevel|Max daily stress level"]

    oxygen_metrics = ["averageSpo2|Average SPO2",
                      "lowestSpo2|Lowest SPO2"]
    misc_metrics = ["totalKilocalories| Total Consumed Calories", "dailyStepGoal| Daily Step Goal", "totalSteps| Total Steps", "lastUploadSyncTime|Last upload sync time"]
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
                val = dailies[key]
                if val is None:
                    print(f"Value for {key} is null")
                if val is not None:
                    self.metrics[key].set(val)


