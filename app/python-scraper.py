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
                "ride": { ... }        # optional single ride to evaluate
            }

        Returns JSON with `history` gating, `baseline` stats per IF band,
        and per-sample strain / comparison outputs (pure diagnostics).
        """
        data = request.get_json(silent=True) or {}
        rides = data.get('rides', [])
        sample = data.get('ride')
        # Optionally accept an Intervals activity id and fetch/parse it here
        activity_id = request.args.get('activity_id') or data.get('activity_id')
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
        resp = {
                'history': history,
                'baseline': baseline,
                'sample_metrics': sample_metrics,
                'is_easy': is_easy,
                'is_easy_reasons': is_easy_reasons,
                'sample_comparison': sample_comparison,
        }
        return json.dumps(resp, indent=2, default=utils.convert)
   
def register_prom_metrics():
    metrics.collect()

if __name__ == "__main__":
    register_prom_metrics()
    connector = Connector()

    serve(app, host="0.0.0.0", port=8080)
