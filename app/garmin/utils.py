import requests
from datetime import datetime, timedelta

def convert(o):
    if hasattr(o, 'item'):
        return o.item()
    if isinstance(o, set):
        return list(o)
    return str(o)

def get_session(api_key):
    session = requests.Session()
    session.auth = ('API_KEY', api_key)
    return session

def get_date_from_weeks(weeks):
    today = datetime.now().date()
    target = today - timedelta(weeks=weeks)
    monday = target - timedelta(days=target.weekday())
    return monday.strftime('%Y-%m-%d')


def make_request(method, url, api_key, params=None, json=None, headers=None):
    session = get_session(api_key)
    if json is not None:
        if headers is None:
            headers = {}
        headers['Content-Type'] = '*/*'
        headers['authorization'] = f"Basic {api_key}"

    res = session.request(
        method,
        url,
        params=params,
        json=json,
        headers=headers)
    
    if res.status_code == 401:
        raise Exception("Invalid Credentials")
    if res.status_code == 403:
        raise Exception (f"Missing permissions for {method }{url} ")
    if res.status_code == 404:
        raise Exception("Missing resource, invalid request")
    if res.status_code == 422:
        print(f"Can't process request for {url}")
        raise Exception("Could not process request")
    return res

def save_activity_to_file(activities_file, activity_id, activity_date, activity_type):
    activities = []
    file = open(activities_file, 'a+')
    for line in file:
        line = line.split("|")
        activities.append(line[0])
    
    if activity_id not in activities:
        line = f"{activity_id}|{activity_date}|{activity_type}\n"
        file.write(line)
    file.close()



