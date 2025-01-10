import logging
import os

import garth
from garth.exc import GarthException


class Connector:
    garth_folder = ""
    garmin_user = ""
    garmin_pass = ""

    def __init__(self):
        self.garmin_user = os.environ.get("GARMIN_USER")
        self.garth_folder = os.environ.get("GARTH_FOLDER")
        self.garmin_pass = os.environ.get("GARMIN_PASS")

        if not self.is_logged_in():
            print(f"Logging in with {self.garmin_user} and {self.garmin_pass}")
            garth.login(self.garmin_user, self.garmin_pass)
            garth.save(self.garth_folder)



    def is_logged_in(self):
        self.does_garth_exist()
        try:
            garth.resume(self.garth_folder)
        except FileNotFoundError:
            print("OAuth2 tokens don't exist")
            return False
        try:
            garth.client.username
        except GarthException:
            print("Session is expired, new login required")
            return False
        print("OAuth tokens valid, already logged in")
        return True

    def does_garth_exist(self):
        exists = os.path.isdir(self.garth_folder)
        if not exists:
            os.makedirs(self.garth_folder, exist_ok=True)
