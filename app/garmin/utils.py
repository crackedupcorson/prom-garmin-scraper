import requests

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
        raise Exception("Could not process request")
    return res