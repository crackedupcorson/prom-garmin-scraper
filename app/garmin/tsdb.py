import datetime


class TsdbGenerator:
    def create_backfill(self, historical_data):
        for daily in historical_data:
            daily = self.cleanup_daily(daily)
            self.generate_tsdb_data(daily)

    def get_timestamp_from_date(self, date):
        timestamps = []
        current_time = datetime.datetime.strptime(date, "%Y-%m-%d")
        for x in range(11):
            timestamp = current_time.timestamp()
            timestamps.append(int(timestamp))
            delta = datetime.timedelta(hours=2)
            current_time = current_time + delta
        return timestamps


    def generate_tsdb_data(self, daily):
        timestamps = self.get_timestamp_from_date(daily['calendarDate'])
        for timestamp in timestamps:
            self.generate_blockfile(timestamp, daily)

    def generate_blockfile(self, timestamp, daily):
        filename = f"c:\\Users\\ciara\\RaspberriPi\\K8s\\raw\\backfill_{timestamp}.txt"
        print(f"Getting TSDB data for {daily['calendarDate']}")
        with open(filename, "w", newline="\n") as f:
            f.write("# HELP minHeartRate Min heart rate\n")
            f.write("# TYPE minHeartRate gauge\n")
            f.write(f"minHeartRate {daily['minHeartRate']} {timestamp}\n")
            f.write("# HELP maxHeartRate Max heart rate\n")
            f.write("# TYPE maxHeartRate gauge\n")
            f.write(f"maxHeartRate {daily['maxHeartRate']} {timestamp}\n")
            f.write("# HELP restingHeartRate Resting heart rate\n")
            f.write("# TYPE restingHeartRate gauge\n")
            f.write(f"restingHeartRate {daily['restingHeartRate']} {timestamp}\n")
            f.write("# HELP lastSevenDaysAvgRestingHeartRate Sevenday avg heart rate\n")
            f.write("# TYPE lastSevenDaysAvgRestingHeartRate gauge\n")
            f.write(f"lastSevenDaysAvgRestingHeartRate {daily['lastSevenDaysAvgRestingHeartRate']} {timestamp}\n")
            f.write("# HELP bodyBatteryHighestValue Body battery highest value\n")
            f.write("# TYPE bodyBatteryHighestValue gauge\n")
            f.write(f"bodyBatteryHighestValue {daily['bodyBatteryHighestValue']} {timestamp}\n")
            f.write("# HELP bodyBatteryLowestValue body battery lowest value\n")
            f.write("# TYPE bodyBatteryLowestValue gauge\n")
            f.write(f"bodyBatteryLowestValue {daily['bodyBatteryLowestValue']} {timestamp}\n")
            f.write("# HELP bodyBatteryDuringSleep Body battery recovered during sleep\n")
            f.write("# TYPE bodyBatteryDuringSleep gauge\n")
            f.write(f"bodyBatteryDuringSleep {daily['bodyBatteryDuringSleep']} {timestamp}\n")
            f.write("# HELP averageStressLevel Average stress level\n")
            f.write("# TYPE averageStressLevel gauge\n")
            f.write(f"averageStressLevel {daily['averageStressLevel']} {timestamp}\n")
            f.write("# HELP maxStressLevel Max daily stress level\n")
            f.write("# TYPE maxStressLevel gauge\n")
            f.write(f"maxStressLevel {daily['maxStressLevel']} {timestamp}\n")
            f.write("# HELP averageSpo2 Average SPO2\n")
            f.write("# TYPE averageSpo2 gauge\n")
            f.write(f"averageSpo2 {daily['averageSpo2']} {timestamp}\n")
            f.write("# HELP lowestSpo2 Lowest SPO2\n")
            f.write("# TYPE lowestSpo2 gauge\n")
            f.write(f"lowestSpo2 {daily['lowestSpo2']} {timestamp}\n")
            f.write("# HELP sedentarySeconds time spend sedentary\n")
            f.write("# TYPE sedentarySeconds gauge\n")
            f.write(f"sedentarySeconds {daily['sedentarySeconds']} {timestamp}\n")
            f.write("# HELP sleepingSeconds seconds spent sleeping\n")
            f.write("# TYPE sleepingSeconds gauge\n")
            f.write(f"sleepingSeconds {daily['sleepingSeconds']} {timestamp}\n")
            f.write("# HELP activeSeconds seconds spent highly active\n")
            f.write("# TYPE activeSeconds gauge\n")
            f.write(f"activeSeconds {daily['activeSeconds']} {timestamp}\n")
            f.write("# HELP highlyActiveSeconds time spent highly active\n")
            f.write("# TYPE highlyActiveSeconds gauge\n")
            f.write(f"highlyActiveSeconds {daily['highlyActiveSeconds']} {timestamp}\n")
            f.write("# EOF")
            f.close()

    def cleanup_daily(self, daily):
        for metric in daily:
            if daily[metric] is None:
                daily[metric] = 0
        return daily
