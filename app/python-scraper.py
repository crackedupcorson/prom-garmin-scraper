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
@app.route('/daily')
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
   
def register_prom_metrics():
    metrics.collect()

if __name__ == "__main__":
    register_prom_metrics()
    connector = Connector()

    serve(app, host="0.0.0.0", port=8080)
