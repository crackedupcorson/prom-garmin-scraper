import datetime
import os
from datetime import timedelta

import garth
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class Scrape():
    slack_channel = ""
    slack_user_id = ""
    slack_auth_token = ""
    def __init__(self):
        self.slack_channel = os.environ.get("SLACK_CHANNEL")
        self.slack_user_id = os.environ.get("SLACK_USER_ID")
        self.slack_auth_token = os.environ.get("SLACK_BOT_TOKEN")
    def get_daily_data(self):
        date = datetime.datetime.now()
        date_str = date.strftime('%Y-%m-%d')
        params = {
            'calendarDate': date_str
        }
        dailies = garth.connectapi(f"/usersummary-service/usersummary/daily", params=params)
        devices = garth.connectapi("/device-service/deviceregistration/devices")
        for device in devices:
            if device["displayName"] == "main-watch":
                deviceId = device["deviceId"]
                device_data = garth.connectapi(f"device-service/deviceservice/user-device/{deviceId}")
                sync_time = device_data["lastUploadTimestamp"]
                dailies["lastUploadSyncTime"] = sync_time
        return dailies

    def get_historical_data(self, days):
        historical_data = []
        current_date = datetime.datetime.today()
        for day in [day for day in range(days) if day != 0]:
            backfill_date = current_date - timedelta(days=day)
            date_str = backfill_date.strftime('%Y-%m-%d')
            params = {
                'calendarDate': date_str
            }
            daily_summary = garth.connectapi(f"/usersummary-service/usersummary/daily", params=params)
            historical_data.append(daily_summary)
        return historical_data

    def check_last_sync(self, dailies):
        scrape_time = datetime.datetime.now()
        if dailies["lastUploadSyncTime"]:
            sync_time = dailies["lastUploadSyncTime"]
            sync_time = datetime.datetime.fromtimestamp(sync_time / 1000.0)
            time_difference = scrape_time - sync_time
            is_sync_stale = time_difference > datetime.timedelta(hours=4)
            msg = f"@{self.slack_user_id} Stale watch sync. Time difference between scrape & last sync is {time_difference}"
            if is_sync_stale:
                self.send_message(msg)
                
    def send_message(self, msg):
        client = WebClient(token=self.slack_auth_token)
        try:
            result = client.chat_postMessage(channel=self.slack_channel, text=msg)
            print(result)
        except SlackApiError as e:
            print(f"Error: {e}")