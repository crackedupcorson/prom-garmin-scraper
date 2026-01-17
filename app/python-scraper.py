from flask import Flask
from flask import request

from garmin.connector import Connector
from waitress import serve
import prometheus_client
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from garmin.metrics import Metrics
from garmin.scrape import Scrape
from garmin.tsdb import TsdbGenerator
from garmin.intervals import Intervals
from garmin.fatigue import FatigueChecker
import garmin.utils as utils
import json

app = Flask(__name__)
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)
metrics = Metrics()
@app.route('/garmin/daily')
def get_dailies():
    scrape = Scrape()
    dailies = scrape.get_daily_data()
    scrape.check_last_sync(dailies)
    metrics.populate_metrics(dailies)
    
    # Compute and expose fatigue metrics from recent 6 weeks of activity history
    try:
        intervals = Intervals()
        activities = intervals.get_activities_in_last_x_weeks(6)
        ids = intervals.get_activity_ids(activities)
        rides = []
        for aid in ids:
            try:
                file_path, metadata = intervals.get_activity_streams(aid)
                if metadata.get("type") == "Walk":
                    continue
                activity_metrics = intervals.parse_activity(file_path, metadata)
                rides.append(activity_metrics)
            except Exception as e:
                print(f"Caught exception {e} loading activity {aid} for fatigue, skipping")
        
        if rides:
            fc = FatigueChecker()
            baseline = fc.build_baseline_statistics(rides)
            classification = fc.aggregate_7day_classification(rides)
            gating = classification.get("gating", {})
            load_context = classification.get("load_context", {})
            metrics.populate_fatigue_metrics(classification, baseline, gating, load_context)
    except Exception as e:
        print(f"Failed to compute fatigue metrics: {e}")
    
    return dailies


@app.route('/garmin/backfill')
def generate_backfill():
    scrape = Scrape()
    tsdb = TsdbGenerator()
    days = request.args.get('days', default=1)
    backfill = scrape.get_historical_data(int(days))
    tsdb.create_backfill(backfill)
    return f"Successfully found records for {len(backfill)} days"


@app.route('/intervals/activity')
def get_activity_stream():
    intervals = Intervals()
    activity_id = request.args.get('id')
    file_path, metadata = intervals.get_activity_streams(activity_id)
    metrics = intervals.parse_activity(file_path, metadata)
    utils.save_activity_to_file(intervals.activites_file_path, activity_id, metadata["activity_date"] ,  metadata["type"])
    resp = json.dumps(metrics, indent=4, default=utils.convert)
    return resp

@app.route('/intervals/activities')
def get_activities():
    weeks =  request.args.get('weeks', default="6")
    intervals = Intervals()
    activities = intervals.get_activities_in_last_x_weeks(int(weeks))
    ids = intervals.get_activity_ids(activities)
    all_metrics = []
    for activity_id in ids:
        try:
            file_path, metadata = intervals.get_activity_streams(activity_id)
            if metadata["type"] == "Walk":
                continue
            activity_metrics = intervals.parse_activity(file_path, metadata)
            utils.save_activity_to_file(intervals.activities_file_path, activity_id, metadata["activity_date"] ,  metadata["type"])
            all_metrics.append(activity_metrics)
        except Exception as e:
            print(f"Caught exception {e} loading activity {activity_id}, skipping")
    result = json.dumps(all_metrics)
    return result


@app.route('/fatigue/diag', methods=['POST'])
def fatigue_diag():
    """Diagnostic endpoint for the fatigue primitives.

    Accepts JSON body:
      {
        "rides": [ { ... } ],   # optional list of historical rides
        "ride": { ... },        # optional single ride to evaluate
        "weeks": N              # optional: fetch N weeks from Intervals API
      }

    Returns JSON with `history` gating, `baseline` stats per IF band,
    per-sample strain / comparison outputs, and classification.
    """
    data = request.get_json()
    rides = data.get('rides', [])
    sample = data.get('ride')
    weeks = data.get('weeks')
    activity_id = request.args.get('activity_id') or data.get('activity_id')

    # If weeks is provided, fetch from Intervals API (mimics get_activities)
    if weeks:
        try:
            intervals = Intervals()
            activities = intervals.get_activities_in_last_x_weeks(int(weeks))
            ids = intervals.get_activity_ids(activities)
            rides = []
            for aid in ids:
                try:
                    file_path, metadata = intervals.get_activity_streams(aid)
                    if metadata.get("type") == "Walk":
                        continue
                    activity_metrics = intervals.parse_activity(file_path, metadata)
                    rides.append(activity_metrics)
                except Exception as e:
                    print(f"Caught exception {e} loading activity {aid}, skipping")
        except Exception as e:
            print(f"Failed to fetch activities from Intervals: {e}")

    # Optionally accept a single activity_id and use it as sample
    if activity_id and sample is None:
        try:
            intervals = Intervals()
            file_path, metadata = intervals.get_activity_streams(activity_id)
            sample = intervals.parse_activity(file_path, metadata)
        except Exception as e:
            sample = None
            print(f"Failed to load activity {activity_id}: {e}")

    fc = FatigueChecker()
    history = fc.history_gating(rides)
    baseline = fc.build_baseline_statistics(rides) if rides else {}
    
    sample_metrics = None
    is_easy = None
    is_easy_reasons = None
    sample_comparison = None
    if sample:
        sample_metrics = fc.compute_per_ride_strain(sample)
        is_easy, is_easy_reasons = fc.is_easy_ride(sample)
        sample_comparison = fc.compare_ride_to_baseline(sample, baseline)

    classification = fc.aggregate_7day_classification(rides) if rides else None

    resp = {
        'history': history,
        'baseline': baseline,
        'classification': classification,
        'sample_metrics': sample_metrics,
        'is_easy': is_easy,
        'is_easy_reasons': is_easy_reasons,
        'sample_comparison': sample_comparison,
    }
    return json.dumps(resp, indent=2, default=utils.convert)


@app.route('/fatigue/summary', methods=['GET', 'POST'])
def fatigue_summary():
    """Text summary endpoint for fatigue status (task 12).

    Accepts optional query parameter `weeks` (default 6).
    Fetches recent activity history and returns a human-readable summary.
    """
    weeks = request.args.get('weeks', default=6, type=int)
    
    try:
        intervals = Intervals()
        activities = intervals.get_activities_in_last_x_weeks(weeks)
        ids = intervals.get_activity_ids(activities)
        rides = []
        for aid in ids:
            try:
                file_path, metadata = intervals.get_activity_streams(aid)
                if metadata.get("type") == "Walk":
                    continue
                activity_metrics = intervals.parse_activity(file_path, metadata)
                rides.append(activity_metrics)
            except Exception as e:
                print(f"Caught exception {e} loading activity {aid}, skipping")
        
        fc = FatigueChecker()
        baseline = fc.build_baseline_statistics(rides)
        classification = fc.aggregate_7day_classification(rides)
        summary_text = fc.text_summary(classification, baseline, rides)
        
        return summary_text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        print(f"Failed to generate fatigue summary: {e}")
        return f"Error: {e}", 500


def register_prom_metrics():
    metrics.collect()

if __name__ == "__main__":
    register_prom_metrics()
    connector = Connector()

    serve(app, host="0.0.0.0", port=8080)
