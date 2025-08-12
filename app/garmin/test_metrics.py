import unittest
from unittest.mock import MagicMock, patch
from prometheus_client.core import Gauge
from app.garmin.metrics import Metrics

class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.metrics = Metrics()

    @patch('prometheus_client.core.Gauge')
    def test_populate_metrics(self, mock_gauge):
        mock_gauge.return_value = MagicMock()
        
        # Collect to initialize mock metrics
        self.metrics.collect()

        # Mock daily data
        dailies = {
            "minHeartRate": 60,
            "maxHeartRate": 120,
            "restingHeartRate": 70,
            "lastSevenDaysAvgRestingHeartRate": 65,
            "bodyBatteryHighestValue": 90,
            "bodyBatteryLowestValue": 20,
            "bodyBatteryDuringSleep": 50,
            "averageStressLevel": 2,
            "maxStressLevel": 5,
            "averageSpo2": 98,
            "lowestSpo2": 92,
            "sedentarySeconds": 3600,
            "sleepingSeconds": 28800,
            "activeSeconds": 7200,
            "highlyActiveSeconds": 1800,
            "totalKilocalories": 2500,
            "dailyStepGoal": 10000,
            "totalSteps": 8500,
            "lastUploadSyncTime": 1672531200
        }

        # Replace metrics with mocked gauges
        for key in self.metrics.metrics:
            metric_mock = MagicMock()
            metric_mock.labels.return_value = metric_mock
            self.metrics.metrics[key] = metric_mock

        self.metrics.populate_metrics(dailies)

        # Verify all metrics are populated with correct values
        for key, val in dailies.items():
            if val is not None and key in self.metrics.metrics:
                print(key)
                self.metrics.metrics[key].set.assert_called_with(val)

if __name__ == "__main__":
    unittest.main()
