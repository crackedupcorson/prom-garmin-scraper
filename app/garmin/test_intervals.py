import json
import os
import unittest
from unittest.mock import Mock, patch
from garmin.intervals import Intervals
import garmin.utils as utils


class TestIntervals(unittest.TestCase):

    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "INTERVALS_BASE_URL": "https://intervals.example",
            "INTERVALS_API_KEY": "test-api-key",
            "GARTH_FOLDER": "/tmp/test-garth",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

        self.make_request_patcher = patch("garmin.intervals.utils.make_request")
        self.mock_make_request = self.make_request_patcher.start()
        self.addCleanup(self.make_request_patcher.stop)

    def make_intervals(self, athlete_case):
        response = Mock()
        response.json.return_value = self.mock_athlete_fields(athlete_case)
        self.mock_make_request.return_value = response
        return Intervals()

    def test_get_valid_ftp(self):
        intervals = self.make_intervals("valid")
        self.assertEqual(intervals.ftp, 170)
        self.mock_make_request.assert_called_with(
            "get",
            "https://intervals.example/api/v1/athlete/0",
            "test-api-key",
        )

    def test_get_athlete_fields_no_sport_settings(self):
        intervals = self.make_intervals("no_sport_settings")
        self.assertEqual(intervals.ftp, 218)

    def test_get_athlete_fields_no_mmp_model(self):
        intervals = self.make_intervals("no_mmp_model")
        self.assertEqual(intervals.ftp, 218)

    def test_get_athlete_fields_no_ftp_in_mmp_model(self):
        intervals = self.make_intervals("no_ftp_in_mmp_model")
        self.assertEqual(intervals.ftp, 218)

    def test_get_activities_in_last_x_weeks(self):
        test_weeks = 4
        date = utils.get_date_from_weeks(test_weeks)

        athlete_response = Mock()
        athlete_response.json.return_value = self.mock_athlete_fields("valid")
        activities_response = self.mock_activities_response("valid")

        def mock_request(method, url, api_key):
            if url == "https://intervals.example/api/v1/athlete/0":
                return athlete_response
            if url == f"https://intervals.example/api/v1/athlete/0/activities?oldest={date}":
                return activities_response
            self.fail(f"Unexpected request: {method} {url}")

        self.mock_make_request.side_effect = mock_request

        intervals = Intervals()
        activities = intervals.get_activities_in_last_x_weeks(test_weeks)
        assert len(activities) == 2

    def test_get_no_activities_in_last_x_weeks(self):
        test_weeks = 4
        date = utils.get_date_from_weeks(test_weeks)

        athlete_response = Mock()
        athlete_response.json.return_value = self.mock_athlete_fields("valid")
        activities_response = self.mock_activities_response("no_activities")

        def mock_request(method, url, api_key):
            if url == "https://intervals.example/api/v1/athlete/0":
                return athlete_response
            if url == f"https://intervals.example/api/v1/athlete/0/activities?oldest={date}":
                return activities_response
            self.fail(f"Unexpected request: {method} {url}")

        self.mock_make_request.side_effect = mock_request

        intervals = Intervals()
        activities = intervals.get_activities_in_last_x_weeks(test_weeks)
        assert len(activities) == 0
    
    def test_get_activity_ids(self):
        intervals = Intervals()
        activities = [
            {"id": 12345, "startTimeLocal": "2023-01-01T10:00:00Z"},
            {"id": 67890, "startTimeLocal": "2023-01-02T10:00:00Z"},
        ]
        ids = intervals.get_activity_ids(activities)
        assert len(ids) == 2

    def test_get_activity_ids_empty(self):
        intervals = Intervals()
        activities = []
        ids = intervals.get_activity_ids(activities)
        assert len(ids) == 0
    
    def mock_activities_response(self, test_case):
        test_cases = dict()
        valid = [
            {
                "id": 12345,
                "startTimeLocal": "2023-01-01T10:00:00Z",
                "sportType": "cycling",
                "distance": 10000,
                "duration": 3600,
            },
            {
                "id": 67890,
                "startTimeLocal": "2023-01-02T10:00:00Z",
                "sportType": "running",
                "distance": 5000,
                "duration": 1800,
            },
        ]
        no_activities = []
        test_cases["valid"] = valid
        test_cases["no_activities"] = no_activities

        response = Mock()
        response.text = json.dumps(test_cases[test_case])
        return response

    def mock_athlete_fields(self, test_case):
        test_cases = dict()
        valid = {
            "id": "12345",
            "sportSettings": [
                {
                    "mmp_model": {
                        'type': 'FFT_CURVES',
                        'criticalPower': 166,
                        'wPrime': 10800,
                        'pMax': 898,
                        'inputPointIndexes': [109],
                        'ftp': 170,
                    }
                }
            ],
        }
        no_sport_settings = {
            "id": 0,
            "username": ""
        }
        no_mmp_model = {
            "id": 0,
            "username": "",
            "sportSettings": [
                {"mmp_model": None}
            ],
        }
        no_ftp_in_mmp_model = {
            "id": 0,
            "username": "",
            "sportSettings": [
                {
                    "mmp_model": {
                        'type': 'FFT_CURVES',
                        'ftp': None,
                    }
                }
            ],
        }
        test_cases["valid"] = valid
        test_cases["no_sport_settings"] = no_sport_settings
        test_cases["no_mmp_model"] = no_mmp_model
        test_cases["no_ftp_in_mmp_model"] = no_ftp_in_mmp_model
        return test_cases[test_case]


