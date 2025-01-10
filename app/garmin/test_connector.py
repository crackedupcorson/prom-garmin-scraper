import os
import unittest
from unittest.mock import patch
from app.garmin.connector import Connector

class TestConnector(unittest.TestCase):

    @patch.dict(os.environ, {"GARMIN_USER": "test_user", "GARTH_FOLDER": "/test/folder", "GARMIN_PASS": "test_pass"})
    @patch("app.garmin.connector.garth")
    def test_init_already_logged_in(self, mock_garth):
        # Mock the garth functions
        mock_garth.resume.return_value = None
        mock_garth.client.username = "test_user"

        # Create an instance of Connector
        connector = Connector()

        # Check that login and save were not called
        mock_garth.login.assert_not_called()
        mock_garth.save.assert_not_called()

    @patch.dict(os.environ, {"GARMIN_USER": "test_user", "GARTH_FOLDER": "/test/folder", "GARMIN_PASS": "test_pass"})
    @patch("app.garmin.connector.garth")
    def test_init_not_logged_in(self, mock_garth):
        # Mock the garth functions
        mock_garth.resume.side_effect = FileNotFoundError
        mock_garth.client.username = None

        # Create an instance of Connector
        connector = Connector()

        # Check that login and save were called
        mock_garth.login.assert_called_once_with("test_user", "test_pass")
        mock_garth.save.assert_called_once_with("/test/folder")

if __name__ == "__main__":
    unittest.main()