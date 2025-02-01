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


@app.route('/backfill')
def generate_backfill():
    scrape = Scrape()
    tsdb = TsdbGenerator()
    days = request.args.get('days', default=1)
    backfill = scrape.get_historical_data(int(days))
    tsdb.create_backfill(backfill)
    return f"Successfully found records for {len(backfill)} days"

def register_prom_metrics():
    metrics.collect()

if __name__ == "__main__":
    register_prom_metrics()
    connector = Connector()

    serve(app, host="0.0.0.0", port=8080)
