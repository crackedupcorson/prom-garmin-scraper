import os
import garmin.utils as utils
import pandas as pd
from datetime import datetime, timedelta
import csv,json
import base64

class Intervals:

    def __init__(self):
        self.slack_channel = os.environ.get("SLACK_CHANNEL")
        self.slack_user_id = os.environ.get("SLACK_USER_ID")
        self.slack_auth_token = os.environ.get("SLACK_BOT_TOKEN")
        self.intervals_api_key = self.get_api_key()
        self.intervals_base = os.environ.get("INTERVALS_BASE_URL")
        self.garth_folder = os.environ.get("GARTH_FOLDER")
        self.ftp = 218
        self.get_athlete_fields()
    def get_api_key(self):
        api_key_bytes = base64.b64decode(os.environ.get("INTERVALS_API_KEY"))
        try:
            decoded_string = api_key_bytes.decode('utf-8')
            decoded_string = decoded_string.replace("\n", "")
            return decoded_string
        except UnicodeDecodeError:
            print("Decoded data is binary, not UTF-8 text.")
    def get_athlete_fields(self):
        endpoint = "/api/v1/athlete/0"
        url = self.intervals_base + endpoint
        resp = utils.make_request("get", url, self.intervals_api_key)
        athlete = resp.json()
        sport_settings = athlete["sportSettings"]
        for sport_setting in sport_settings:
            if sport_setting["mmp_model"] is not None:
                mmp_model = sport_setting["mmp_model"]
                if mmp_model["ftp"] is not None:
                    self.ftp = int(mmp_model["ftp"])
                    break
        

    def get_latest_activity(self):
        activities_csv = self.get_activities()
        activities = csv.reader(activities_csv.splitlines())
        next(activities)
        activity=next(activities)
        id = activity[0]
        return id
    
    def found_new_activity(self):
        new_activity = False
        activities = self.get_activities()
        filepath = self.garth_folder + os.sep + "activities.csv"
        try: 
            activities = activities.decode('utf-8')
        except UnicodeDecodeError:
            print("utf-8-sig encoding")
            activities = activities.decode('utf-8-sig')
        if not os.path.isfile(filepath):
             with open(filepath, 'w') as f:
                f.write(activities)
        if os.path.isfile(filepath):
            existing_row_count = sum(1 for line in open(filepath))
            reader = csv.reader(activities.splitlines())
            new_row_count = sum(1 for _ in reader)
            if new_row_count > existing_row_count:
                new_activity = True
                with open(filepath, 'w') as f:
                    try:
                        f.write(activities)
                    except UnicodeDecodeError:
                       print("what?")
                print(f"Existing count: {existing_row_count}\n New Row Count: {new_row_count}")
        return new_activity

    def get_activities_in_last_x_weeks(self, weeks):
        date = utils.get_date_from_weeks(weeks)
        endpoint = f"/api/v1/athlete/0/activities?oldest={date}"
        url = self.intervals_base + endpoint
        resp = utils.make_request("get", url, self.intervals_api_key)
        if resp is not None:
            activities = json.loads(resp.text)
            return activities
        return None
    
    def get_activity_ids(self, activities):
        activity_ids = []
        for activity in activities:
            if activity["id"]:
                activity_ids.append(activity["id"])
        return activity_ids

    def get_activities(self):
        url = self.intervals_base + "/api/v1/athlete/0/activities.csv"
        resp = utils.make_request("get", url, self.intervals_api_key)
        if resp is not None:
            activities = resp.content
            return activities
        return None   
    
    def get_activity_streams(self, activity_id):
        filepath = ""
        metadata = self.get_activity_metadata(activity_id)
        endpoint = f"/api/v1/activity/{activity_id}/streams.csv"
        url = self.intervals_base + endpoint
        resp = utils.make_request("get", url, self.intervals_api_key)
        if resp.content is not None:
            activity = resp.content.decode('utf-8-sig')
            filepath = self.garth_folder +  os.sep + "activity.csv"
            with open(filepath, 'w') as f:
                f.write(activity)
        return filepath, metadata

    def get_activity_metadata(self, activity_id):
        activity_metadata = {}
        endpoint = f"/api/v1/activity/{activity_id}"
        url = self.intervals_base + endpoint
        resp = utils.make_request("get", url, self.intervals_api_key)
        if resp.text is not None:
            activity_metadata = json.loads(resp.text)
        start_date = activity_metadata["start_date_local"]
        start_date = datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d')
        activity_metadata["activity_date"]=start_date
        return activity_metadata
    
    def parse_activity(self, filepath, metadata):
        # Load CSV into DataFrame
        activity_type = metadata["type"]
        df = pd.read_csv(filepath)
        # Drop completely empty columns
        df = df.dropna(how='all')
        # Ensure 'time' is numeric seconds, starting at 0
        df = df.dropna(subset=['time'])
        df['time'] = df['time'].astype(int)
        metrics = {}
        if activity_type in ["Ride", "VirtualRide"]:
            if "watts" and "cadence" in df:
                metrics = self.compute_bike_metrics(df, self.ftp)
            else:
                metrics = self.compute_rough_guess_bike_metrics(df, self.ftp, metadata)
        if activity_type == "Run":
            metrics = self.compute_running_metrics(df, metadata)
        if activity_type == "WeightTraining":
            metrics = self.compute_weightlifting_metrics(df, metadata)
        if activity_type == "Walk":
            metrics["status"]="Not Implemented"
        metrics["type"]=metadata["type"]
        metrics["date"]=metadata["activity_date"]
        return metrics
        
    def compute_bike_metrics(self, df, ftp):
        df = df.copy()

        # 1) Clean 'time' and drop empty rows
        df = df.dropna(how='all')
        df = df.dropna(subset=['time'])
        df['time'] = pd.to_numeric(df['time'], errors='coerce')
        df = df[df['time'].notna()].sort_values('time').reset_index(drop=True)

        # 2) Make numeric the columns we use (don't blanket-fill everything with 0)
        for col in ['watts', 'cadence', 'heartrate', 'velocity_smooth']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 3) Per-row duration (seconds). Use median of positive deltas for the last sample.
        dt = df['time'].shift(-1) - df['time']
        med_dt = dt.iloc[:-1][dt.iloc[:-1] > 0].median()
        if pd.isna(med_dt):
            med_dt = 1.0
        dt.iloc[-1] = med_dt
        dt = dt.clip(lower=0)
        df['dt'] = dt

        total_time = float(df['dt'].sum())

        metrics = {}

        # ---- Power metrics ----
        if 'watts' in df.columns and df['watts'].notna().any():
            # Time-weighted average power
            metrics['avg_power'] = float((df['watts'].fillna(0) * df['dt']).sum() / total_time)

            # Normalized Power (approx, assumes ~1 Hz data; still time-weighted)
            p30 = df['watts'].fillna(0).rolling(window=30, min_periods=1).mean()
            NP = float(((p30.pow(4) * df['dt']).sum() / total_time) ** 0.25)
            metrics['normalized_power'] = NP
        else:
            NP = None
            metrics['avg_power'] = None
            metrics['normalized_power'] = None

        # Intensity Factor
        IF = (NP / ftp) if (NP is not None and ftp) else None
        metrics['intensity_factor'] = IF

        # TSS
        if NP is not None and IF is not None and ftp and total_time > 0:
            tss = (total_time * NP * IF) / (ftp * 3600.0) * 100.0
            metrics['tss'] = float(tss)
        else:
            metrics['tss'] = None

        # ---- Zones (time-weighted) ----
        if 'watts' in df.columns and ftp:
            bins = [0, 0.55, 0.75, 0.90, 1.05, 1.20, float('inf')]
            labels = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']
            z = pd.cut(df['watts'] / ftp, bins=bins, labels=labels, right=False)
            zone_times = df.groupby(z, observed=False)['dt'].sum().to_dict()
            metrics['zone_times'] = {k: float(v) for k, v in zone_times.items()}
            metrics['zone_percentages'] = {k: (float(v) / total_time * 100.0) for k, v in zone_times.items()}

        # ---- HR drift (split by elapsed time, not rows) ----
        if 'heartrate' in df.columns and df['heartrate'].notna().any():
            cumt = df['dt'].cumsum()
            half = total_time / 2.0
            hr1 = df.loc[cumt <= half, 'heartrate'].mean()
            hr2 = df.loc[cumt >  half, 'heartrate'].mean()
            metrics['hr_drift'] = None if (pd.isna(hr1) or pd.isna(hr2)) else float(hr2 - hr1)

        # ---- Segment percentages (rest / hard / drafting) ----
        seg_times = {}

        if 'watts' in df.columns and ftp:
            cad = df['cadence'].fillna(0) if 'cadence' in df.columns else 0
            # REST: low cadence & low watts
            rest_mask = (cad < 60) & (df['watts'] < 0.5 * ftp)
            seg_times['rest'] = float(df.loc[rest_mask, 'dt'].sum())

            # HARD: >90% FTP
            hard_mask = (df['watts'] > 0.90 * ftp)
            seg_times['hard'] = float(df.loc[hard_mask, 'dt'].sum())

        if {'velocity_smooth', 'watts'}.issubset(df.columns) and ftp:
            v75 = df['velocity_smooth'].quantile(0.75)
            drafting_mask = (df['velocity_smooth'] > v75) & (df['watts'] < 0.5 * ftp)
            seg_times['drafting'] = float(df.loc[drafting_mask, 'dt'].sum())

        metrics['segment_times'] = seg_times
        metrics['segment_percentages'] = {k: (v / total_time * 100.0 if total_time > 0 else 0.0)
                                        for k, v in seg_times.items()}

        metrics['total_time'] = total_time
        return metrics
    
    def compute_rough_guess_bike_metrics(self, df, ftp, metadata):
        df = df.copy()

        # 1) Clean 'time' and drop empty rows
        df = df.dropna(how='all')
        if 'time' not in df.columns:
            return {'error': 'no time column'}
        df = df.dropna(subset=['time'])
        df['time'] = pd.to_numeric(df['time'], errors='coerce')
        df = df[df['time'].notna()].sort_values('time').reset_index(drop=True)

        # 2) Numeric conversion for HR if present
        if 'heartrate' in df.columns:
            df['heartrate'] = pd.to_numeric(df['heartrate'], errors='coerce')

        # 3) Per-row duration (seconds)
        dt = df['time'].shift(-1) - df['time']
        med_dt = dt.iloc[:-1][dt.iloc[:-1] > 0].median()
        if pd.isna(med_dt):
            med_dt = 1.0
        dt.iloc[-1] = med_dt
        dt = dt.clip(lower=0)
        df['dt'] = dt

        total_time = float(df['dt'].sum())

        metrics = {}

        # ----- Estimate average power -----
        def _get_meta_num(keys, treat_percent=False):
            """Return first numeric metadata value for any of the keys.
            If treat_percent=True then strings like '59%' or numeric values >1.5
            will be treated as percentages and returned as fractions (0.59).
            """
            for k in keys:
                v = metadata.get(k) if isinstance(metadata, dict) else None
                if v is None:
                    continue
                # If it's a string containing a percent sign, parse as percent
                if isinstance(v, str) and '%' in v:
                    try:
                        num = float(v.replace('%', '').strip())
                        return (num / 100.0) if treat_percent else num
                    except Exception:
                        continue
                try:
                    num = float(v)
                    if treat_percent and num > 1.5:
                        # likely given as percent like 59 -> return 0.59
                        num = num / 100.0
                    return num
                except Exception:
                    continue
            return None

        avg_power_est = _get_meta_num(['icu_weighted_avg_watts', 'icu_weighted_avg_power', 'icu_weighted_avg_watts',
                                       'average_watts', 'weighted_avg_watts', 'average_power'])
        # If metadata provides icu_intensity (ratio to FTP) we can invert
        if avg_power_est is None:
            intensity_meta = _get_meta_num(['icu_intensity', 'icu_power_intensity', 'intensity'], treat_percent=True)
            if intensity_meta is not None and ftp:
                avg_power_est = intensity_meta * ftp

        # Fallback to metadata icu_weighted_avg_watts spelled differently or None
        metrics['avg_power'] = float(avg_power_est) if avg_power_est is not None else None

        # ----- Normalized power (crude) -----
        if avg_power_est is not None:
            # Without per-second watts we cannot compute proper NP; use avg as proxy
            NP = float(avg_power_est)
            metrics['normalized_power'] = NP
        else:
            NP = None
            metrics['normalized_power'] = None

        # ----- Intensity Factor -----
        IF = (NP / ftp) if (NP is not None and ftp) else None
        metrics['intensity_factor'] = IF

        # ----- TSS -----
        # If intervals.icu provides a training-load estimate, prefer it
        tss_meta = _get_meta_num(['icu_training_load', 'training_load', 'icu_tss'])
        if tss_meta is not None:
            metrics['tss'] = float(tss_meta)
        elif NP is not None and IF is not None and ftp and total_time > 0:
            tss = (total_time * NP * IF) / (ftp * 3600.0) * 100.0
            metrics['tss'] = float(tss)
        else:
            metrics['tss'] = None

        # ----- Zones (best-effort) -----
        if avg_power_est is not None and ftp:
            bins = [0, 0.55, 0.75, 0.90, 1.05, 1.20, float('inf')]
            labels = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']
            frac = avg_power_est / float(ftp)
            # Place the whole activity into the most-appropriate zone
            zone_label = None
            for i in range(len(bins)-1):
                if frac >= bins[i] and frac < bins[i+1]:
                    zone_label = labels[i]
                    break
            zone_times = {z: 0.0 for z in labels}
            if zone_label:
                zone_times[zone_label] = total_time
            metrics['zone_times'] = zone_times
            metrics['zone_percentages'] = {k: (v / total_time * 100.0 if total_time > 0 else 0.0) for k, v in zone_times.items()}
        else:
            metrics['zone_times'] = {}
            metrics['zone_percentages'] = {}

        # ----- HR drift (if HR present) -----
        if 'heartrate' in df.columns and df['heartrate'].notna().any():
            cumt = df['dt'].cumsum()
            half = total_time / 2.0
            hr1 = df.loc[cumt <= half, 'heartrate'].mean()
            hr2 = df.loc[cumt >  half, 'heartrate'].mean()
            metrics['hr_drift'] = None if (pd.isna(hr1) or pd.isna(hr2)) else float(hr2 - hr1)
        else:
            metrics['hr_drift'] = None

        # ----- Segment times via HR if available, else via metadata intensity -----
        seg_times = {}
        if 'heartrate' in df.columns and df['heartrate'].notna().any():
            # Use lactate threshold HR from metadata if available
            lthr = _get_meta_num(['lthr', 'icu_lthr', 'lactate_threshold_hr'])
            hr = df['heartrate'].fillna(0)
            if lthr is not None:
                rest_mask = hr < (0.6 * lthr)
                hard_mask = hr > (0.9 * lthr)
            else:
                # fall back to relative HR percentiles
                rest_mask = hr < hr.quantile(0.25)
                hard_mask = hr > hr.quantile(0.90)

            seg_times['rest'] = float(df.loc[rest_mask, 'dt'].sum())
            seg_times['hard'] = float(df.loc[hard_mask, 'dt'].sum())
        else:
            # no HR; infer from metadata intensity: if intensity > 0.9 entire ride is hard
            intensity_meta = _get_meta_num(['icu_intensity', 'intensity'])
            if intensity_meta is not None:
                if intensity_meta > 0.9:
                    seg_times['hard'] = float(total_time)
                    seg_times['rest'] = 0.0
                else:
                    seg_times['rest'] = float(total_time)
                    seg_times['hard'] = 0.0

        metrics['segment_times'] = seg_times
        metrics['segment_percentages'] = {k: (v / total_time * 100.0 if total_time > 0 else 0.0)
                                         for k, v in seg_times.items()}

        metrics['total_time'] = total_time
        metrics['estimate_method'] = 'rough_from_metadata_and_hr'
        return metrics

    def compute_running_metrics(self, df, metadata):
        # Running metrics: HR zones, HR drift, pace zones, cadence, elevation.
        # My end goal is cycling fitness, so running is complimentary.
        df = df.copy()

        # 1) Clean 'time' and drop empty rows
        df = df.dropna(how='all')
        if 'time' not in df.columns:
            return {'error': 'no time column'}
        df = df.dropna(subset=['time'])
        df['time'] = pd.to_numeric(df['time'], errors='coerce')
        df = df[df['time'].notna()].sort_values('time').reset_index(drop=True)

        # 2) Numeric conversion for HR, velocity, cadence, elevation if present
        for col in ['heartrate', 'velocity_smooth', 'cadence', 'fixed_altitude']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 3) Per-row duration (seconds)
        dt = df['time'].shift(-1) - df['time']
        med_dt = dt.iloc[:-1][dt.iloc[:-1] > 0].median()
        if pd.isna(med_dt):
            med_dt = 1.0
        dt.iloc[-1] = med_dt
        dt = dt.clip(lower=0)
        df['dt'] = dt

        total_time = float(df['dt'].sum())

        metrics = {}

        # Helper for metadata parsing
        def _get_meta_num(keys, treat_percent=False):
            for k in keys:
                v = metadata.get(k) if isinstance(metadata, dict) else None
                if v is None:
                    continue
                if isinstance(v, str) and '%' in v:
                    try:
                        num = float(v.replace('%', '').strip())
                        return (num / 100.0) if treat_percent else num
                    except Exception:
                        continue
                try:
                    num = float(v)
                    if treat_percent and num > 1.5:
                        num = num / 100.0
                    return num
                except Exception:
                    continue
            return None

        # ----- Heart rate metrics -----
        metrics['avg_heartrate'] = None
        metrics['max_heartrate'] = None
        metrics['hr_drift'] = None
        if 'heartrate' in df.columns and df['heartrate'].notna().any():
            metrics['avg_heartrate'] = float(df['heartrate'].mean())
            metrics['max_heartrate'] = float(df['heartrate'].max())
            # HR drift: compare first and second half
            cumt = df['dt'].cumsum()
            half = total_time / 2.0
            hr1 = df.loc[cumt <= half, 'heartrate'].mean()
            hr2 = df.loc[cumt >  half, 'heartrate'].mean()
            metrics['hr_drift'] = None if (pd.isna(hr1) or pd.isna(hr2)) else float(hr2 - hr1)

        # ----- Velocity / Pace metrics -----
        metrics['avg_velocity'] = None
        metrics['max_velocity'] = None
        pace_zones = {}
        if 'velocity_smooth' in df.columns and df['velocity_smooth'].notna().any():
            vel = df['velocity_smooth'].fillna(0)
            metrics['avg_velocity'] = float((vel * df['dt']).sum() / total_time) if total_time > 0 else None
            metrics['max_velocity'] = float(vel.max())
            # Pace zones: Z1-Z5 by velocity percentiles
            q20 = vel.quantile(0.20)
            q40 = vel.quantile(0.40)
            q60 = vel.quantile(0.60)
            q80 = vel.quantile(0.80)
            bins = [0, q20, q40, q60, q80, float('inf')]
            labels = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5']
            z = pd.cut(vel, bins=bins, labels=labels, right=False)
            pace_zones = df.groupby(z, observed=False)['dt'].sum().to_dict()
            metrics['pace_zone_times'] = {k: float(v) for k, v in pace_zones.items()}
            metrics['pace_zone_percentages'] = {k: (float(v) / total_time * 100.0 if total_time > 0 else 0.0)
                                               for k, v in pace_zones.items()}

        # ----- Cadence metrics -----
        metrics['avg_cadence'] = None
        if 'cadence' in df.columns and df['cadence'].notna().any():
            cad = df['cadence'].fillna(0)
            metrics['avg_cadence'] = float((cad * df['dt']).sum() / total_time) if total_time > 0 else None

        # ----- Elevation / effort metrics -----
        metrics['total_elevation_gain'] = _get_meta_num(['total_elevation_gain', 'elevation_gain'])
        metrics['total_elevation_loss'] = _get_meta_num(['total_elevation_loss', 'elevation_loss'])

        # ----- Training Load (from metadata if available) -----
        metrics['training_load'] = _get_meta_num(['icu_training_load', 'training_load', 'tss'])

        # ----- Segment times (easy / steady / hard) via HR zones -----
        seg_times = {}
        if 'heartrate' in df.columns and df['heartrate'].notna().any():
            lthr = _get_meta_num(['lthr', 'icu_lthr', 'lactate_threshold_hr'])
            hr = df['heartrate'].fillna(0)
            if lthr is not None:
                # Easy: <75% LTHR, Steady: 75-90%, Hard: >90%
                seg_times['easy'] = float(df.loc[hr < (0.75 * lthr), 'dt'].sum())
                seg_times['steady'] = float(df.loc[(hr >= (0.75 * lthr)) & (hr <= (0.90 * lthr)), 'dt'].sum())
                seg_times['hard'] = float(df.loc[hr > (0.90 * lthr), 'dt'].sum())
            else:
                # Fallback to HR percentiles
                seg_times['easy'] = float(df.loc[hr < hr.quantile(0.40), 'dt'].sum())
                seg_times['steady'] = float(df.loc[(hr >= hr.quantile(0.40)) & (hr <= hr.quantile(0.75)), 'dt'].sum())
                seg_times['hard'] = float(df.loc[hr > hr.quantile(0.75), 'dt'].sum())

        metrics['segment_times'] = seg_times
        metrics['segment_percentages'] = {k: (v / total_time * 100.0 if total_time > 0 else 0.0)
                                         for k, v in seg_times.items()}

        metrics['total_time'] = total_time
        metrics['estimate_method'] = 'running_from_hr_and_velocity'
        return metrics
    
    def compute_weightlifting_metrics(self, df, metadata):
        # Weightlifting: minimal DF (time + HR only).
        # icu_training_load is the key metric for strength training effort.
        df = df.copy()

        # 1) Clean 'time' and drop empty rows
        df = df.dropna(how='all')
        if 'time' not in df.columns:
            return {'error': 'no time column'}
        df = df.dropna(subset=['time'])
        df['time'] = pd.to_numeric(df['time'], errors='coerce')
        df = df[df['time'].notna()].sort_values('time').reset_index(drop=True)

        # 2) Numeric conversion for HR if present
        if 'heartrate' in df.columns:
            df['heartrate'] = pd.to_numeric(df['heartrate'], errors='coerce')

        # 3) Per-row duration (seconds)
        dt = df['time'].shift(-1) - df['time']
        med_dt = dt.iloc[:-1][dt.iloc[:-1] > 0].median()
        if pd.isna(med_dt):
            med_dt = 1.0
        dt.iloc[-1] = med_dt
        dt = dt.clip(lower=0)
        df['dt'] = dt

        total_time = float(df['dt'].sum())

        metrics = {}

        # Helper for metadata parsing
        def _get_meta_num(keys, treat_percent=False):
            for k in keys:
                v = metadata.get(k) if isinstance(metadata, dict) else None
                if v is None:
                    continue
                if isinstance(v, str) and '%' in v:
                    try:
                        num = float(v.replace('%', '').strip())
                        return (num / 100.0) if treat_percent else num
                    except Exception:
                        continue
                try:
                    num = float(v)
                    if treat_percent and num > 1.5:
                        num = num / 100.0
                    return num
                except Exception:
                    continue
            return None

        # ----- Training Load (PRIMARY METRIC for strength) -----
        metrics['training_load'] = _get_meta_num(['icu_training_load', 'training_load', 'tss'])

        # ----- Heart rate metrics -----
        metrics['avg_heartrate'] = None
        metrics['max_heartrate'] = None
        metrics['hr_drift'] = None
        if 'heartrate' in df.columns and df['heartrate'].notna().any():
            metrics['avg_heartrate'] = float(df['heartrate'].mean())
            metrics['max_heartrate'] = float(df['heartrate'].max())
            # HR drift: compare first and second half
            cumt = df['dt'].cumsum()
            half = total_time / 2.0
            hr1 = df.loc[cumt <= half, 'heartrate'].mean()
            hr2 = df.loc[cumt >  half, 'heartrate'].mean()
            metrics['hr_drift'] = None if (pd.isna(hr1) or pd.isna(hr2)) else float(hr2 - hr1)

        # ----- HR-based segment times (easy / moderate / intense) -----
        seg_times = {}
        if 'heartrate' in df.columns and df['heartrate'].notna().any():
            lthr = _get_meta_num(['lthr', 'icu_lthr', 'lactate_threshold_hr'])
            hr = df['heartrate'].fillna(0)
            if lthr is not None:
                # Easy: <70% LTHR, Moderate: 70-85%, Intense: >85%
                seg_times['easy'] = float(df.loc[hr < (0.70 * lthr), 'dt'].sum())
                seg_times['moderate'] = float(df.loc[(hr >= (0.70 * lthr)) & (hr <= (0.85 * lthr)), 'dt'].sum())
                seg_times['intense'] = float(df.loc[hr > (0.85 * lthr), 'dt'].sum())
            else:
                # Fallback to HR percentiles
                seg_times['easy'] = float(df.loc[hr < hr.quantile(0.33), 'dt'].sum())
                seg_times['moderate'] = float(df.loc[(hr >= hr.quantile(0.33)) & (hr <= hr.quantile(0.67)), 'dt'].sum())
                seg_times['intense'] = float(df.loc[hr > hr.quantile(0.67), 'dt'].sum())
        else:
            # No HR data; mark as unknown intensity but still track total time
            seg_times['unknown'] = float(total_time)

        metrics['segment_times'] = seg_times
        metrics['segment_percentages'] = {k: (v / total_time * 100.0 if total_time > 0 else 0.0)
                                         for k, v in seg_times.items()}

        # ----- Distance / Elevation (if present) -----
        metrics['distance'] = _get_meta_num(['distance', 'icu_distance'])
        metrics['elevation_gain'] = _get_meta_num(['total_elevation_gain', 'elevation_gain'])

        metrics['total_time'] = total_time
        metrics['estimate_method'] = 'strength_from_training_load_and_hr'
        return metrics
        


