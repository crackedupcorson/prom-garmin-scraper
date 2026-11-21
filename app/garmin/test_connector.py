import os
import unittest
import tempfile
from unittest.mock import patch
from app.garmin.connector import Connector

class TestConnector(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for GARTH_FOLDER
        self.temp_dir = tempfile.TemporaryDirectory()
        self.garth_folder = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("app.garmin.connector.garth")
    def test_init_already_logged_in(self, mock_garth):
        with patch.dict(os.environ, {"GARMIN_USER": "test_user", "GARTH_FOLDER": self.garth_folder, "GARMIN_PASS": "test_pass"}):
            # Mock the garth functions
            mock_garth.resume.return_value = None
            mock_garth.client.username = "test_user"

            # Create an instance of Connector
            connector = Connector()

            # Check that login and save were not called
            mock_garth.login.assert_not_called()
            mock_garth.save.assert_not_called()

    @patch("app.garmin.connector.garth")
    @patch("app.garmin.connector.logger")
    def test_init_not_logged_in_does_not_log_credentials(self, mock_logger, mock_garth):
        with patch.dict(os.environ, {"GARMIN_USER": "test_user", "GARTH_FOLDER": self.garth_folder, "GARMIN_PASS": "test_pass"}):
            # Mock the garth functions
            mock_garth.resume.side_effect = FileNotFoundError
            mock_garth.client.username = None

            # Create an instance of Connector
            connector = Connector()

            # Check that login and save were called
            mock_garth.login.assert_called_once_with("test_user", "test_pass")
            mock_garth.save.assert_called_once_with(self.garth_folder)

            logged_values = " ".join(
                str(argument)
                for call in mock_logger.method_calls
                for argument in call.args
            )
            self.assertNotIn("test_user", logged_values)
            self.assertNotIn("test_pass", logged_values)

if __name__ == "__main__":
    unittest.main()
