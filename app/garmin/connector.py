import os
import logging

import garth
from garth.exc import GarthException

logger = logging.getLogger(__name__)


class Connector:
    garth_folder = ""
    garmin_user = ""
    garmin_pass = ""

    def __init__(self):
        self.garmin_user = os.environ.get("GARMIN_USER")
        self.garth_folder = os.environ.get("GARTH_FOLDER")
        self.garmin_pass = os.environ.get("GARMIN_PASS")

        if not self.is_logged_in():
            logger.info("Garmin OAuth tokens unavailable; attempting login")
            garth.login(self.garmin_user, self.garmin_pass)
            garth.save(self.garth_folder)



    def is_logged_in(self):
        self.does_garth_exist()
        try:
            garth.resume(self.garth_folder)
        except FileNotFoundError:
            logger.info("Garmin OAuth tokens do not exist")
            return False
        try:
            garth.client.username
        except GarthException:
            logger.info("Garmin OAuth session is expired; login required")
            return False
        logger.info("Garmin OAuth tokens are valid")
        return True

    def does_garth_exist(self):
        exists = os.path.isdir(self.garth_folder)
        if not exists:
            os.makedirs(self.garth_folder, exist_ok=True)
