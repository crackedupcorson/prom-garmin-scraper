import unittest
from unittest.mock import patch
import datetime
from app.garmin.scrape import Scrape

class TestScrape(unittest.TestCase):
    def setUp(self):
        self.scrape = Scrape()

    @patch('garth.connectapi')
    def test_get_daily_data(self, mock_connectapi):
        mock_connectapi.side_effect = lambda endpoint, params=None: {
            "/usersummary-service/usersummary/daily": {"summary": "daily_data"},
            "/device-service/deviceregistration/devices": [
                {"displayName": "main-watch", "deviceId": "device123"}
            ],
            "device-service/deviceservice/user-device/device123": {
                "lastUploadTimestamp": 1672531200000
            }
        }.get(endpoint)

        dailies = self.scrape.get_daily_data()

        self.assertIn("lastUploadSyncTime", dailies)
        self.assertEqual(dailies["lastUploadSyncTime"], 1672531200000)

    @patch('garth.connectapi')
    def test_get_historical_data(self, mock_connectapi):
        mock_connectapi.side_effect = lambda endpoint, params=None: {
            "/usersummary-service/usersummary/daily": {"summary": f"data_for_{params['calendarDate']}"}
        }.get(endpoint)

        days = 3
        historical_data = self.scrape.get_historical_data(days)

        self.assertEqual(len(historical_data), days - 1)
        for i, daily_data in enumerate(historical_data):
            expected_date = (datetime.datetime.today() - datetime.timedelta(days=i + 1)).strftime('%Y-%m-%d')
            self.assertEqual(daily_data['summary'], f"data_for_{expected_date}")

    @patch('app.garmin.scrape.Scrape.send_message')
    def test_check_last_sync(self, mock_send_message):
        dailies = {"lastUploadSyncTime": (datetime.datetime.now() - datetime.timedelta(hours=5)).timestamp() * 1000}

        self.scrape.check_last_sync(dailies)

        mock_send_message.assert_called_once()
        msg = mock_send_message.call_args[0][0]
        self.assertIn("Stale watch sync", msg)

    @patch('slack_sdk.WebClient.chat_postMessage')
    def test_send_message(self, mock_chat_post_message):
        mock_chat_post_message.return_value = {"ok": True}
        msg = "Test message"

        self.scrape.send_message(msg)

        mock_chat_post_message.assert_called_once_with(channel=self.scrape.slack_channel, text=msg)

if __name__ == "__main__":
    unittest.main()
