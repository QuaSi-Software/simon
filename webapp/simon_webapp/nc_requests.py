"""Functions for performing requests to NextCloud using oauth authentication."""
import requests
from flask import session

def refresh_access_token(app, timeout=10):
    """Fetches a new access token using the refresh token.

    The required tokens are stored in the session and the new token values are being written
    back to the session.

    Args:
    -`app`: The flask app, used for accessing settings and the session
    -`timeout:int`: (Optional) Timeout in seconds for waiting for a response. Defaults to
        10 seconds.
    """
    response = requests.post(
        app.config['NEXTCLOUD_ACCESS_TOKEN_URL'],
        data={
            'client_id': app.config['NEXTCLOUD_CLIENT_ID'],
            'client_secret': app.config['NEXTCLOUD_SECRET'],
            'grant_type': 'refresh_token',
            'refresh_token': session['nextcloud_refresh_token'],
        },
        headers={'Accept': 'application/json'},
        timeout=timeout
    )
    response_data = response.json()
    session["nextcloud_access_token"] = response_data.get('access_token')
    session["nextcloud_refresh_token"] = response_data.get('refresh_token')

def ensure_request(url, app, method="GET", data=None, json=None, headers=None, timeout=10):
    """Performs a request to the configured NextCloud instance, ensuring the request is
    not being rejected due to an expired access token.

    If a request is rejected (presumably) due to an expired access token, a new access
    token is fetched using the refresh token and the original request is sent again. The
    returned response is either the direct response to the original request if it was not
    rejected with status code 401 or the response to the re-sent request if a new token was
    fetched in between.

    Args:
    -`url:str`: The URL of the request
    -`app`: The flask app, used for settings
    -`method:str`: (Optional) The method of the request. Defaults to "GET"
    -`data:dict|None`: (Optional) Data for the request. How this is used depends on the
        method of the request. See documentation of `request` of the `requests` package
        for more information. Defaults to `None`.
    -`json:dict|list|None`: (Optional) JSON-style data for the request. How this is used
        depends on the method of the request. See documentation of `request` of the
        `requests` package for more information. Defaults to `None`.
    -`headers:dict|None`: (Optional) Headers to be used for the request. Note that the
        `Authorization` header will be set with the NC access token if not given or no
        headers are given. Defaults to None`.
    -`timeout:int`: (Optional) Timeout in seconds for waiting for a response. Defaults to
        10 seconds.
    Returns:
    -`HtmlResponse`: The response to the request.
    """
    # ensure authorization header is set if not done so already
    if headers is None:
        headers = {}
    if "Authorization" not in headers:
        headers["Authorization"] = "Bearer " + session["nextcloud_access_token"]

    # try to fetch, refresh access token if necessary, and try again.
    for try_idx in range(0,2):
        response = requests.request(
            method=method,
            url=url,
            data=data,
            json=json,
            timeout=timeout,
            headers=headers
        )
        if try_idx == 0 and response.status_code == 401:
            # assuming the 401 was due to an expired access token, we refresh it and try again
            refresh_access_token(app)
            headers["Authorization"] = "Bearer " + session["nextcloud_access_token"]
            continue
        else:
            # we're either on the first try and didn't get a 401 or we still got a 401 after
            # refreshing the access token. either case, we return the response as is
            return response
