"""Simple Flask app for serving the webapp index and some associated routes.
"""

from __future__ import annotations

from pathlib import Path
import io
import requests
import yaml
from flask import Flask, render_template, jsonify, request, session, url_for, redirect
from flask_session import Session
from authlib.integrations.flask_client import OAuth

APP_ROOT = Path(__file__).resolve().parent.parent
APP_CONFIG_PATH = APP_ROOT / "webapp_config.yml"

# ---------------------------------------------------------------------------
# App construction
# ---------------------------------------------------------------------------

# construct app so routes can be registered via annotation
app = Flask("simon_webapp")

# read config and transfer to app config object
if not APP_CONFIG_PATH.exists() or not APP_CONFIG_PATH.is_file():
    raise FileNotFoundError(f"Configuration file {APP_CONFIG_PATH} does not exist or is " +
                             "not a file.")
with open(APP_CONFIG_PATH, "r", encoding="utf-8") as config_file:
    webapp_config = yaml.safe_load(config_file)
    for key in webapp_config:
        app.config[key] = webapp_config[key]

def get_app():
    """Get the global app variable."""
    return app

# set session to be managed server-side
Session(app)

# register NextCloud oauth
oauth = OAuth(app)
oauth.register('nextcloud')

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Index route.

    Request body: None

    Response (HTML): The index page containing all frontend code as SPA
    """
    if "user" not in session:
        session["user"] = "__anonymous__"
        session["nextcloud_authorized"] = False
    return render_template("index.html", session=session), 200

@app.route("/nextcloud_login", methods=["GET"])
def nextcloud_login():
    """NextCloud login route.

    Request body: None

    Response (HTML): A redirect to the NextCloud login
    """
    if "nextcloud_authorized" in session and session["nextcloud_authorized"]:
        redirect(url_for("index"))

    redirect_uri = url_for("callback_nextcloud", _external=True)
    return oauth.nextcloud.authorize_redirect(redirect_uri)

@app.route('/callback/nextcloud', methods=["GET"])
def callback_nextcloud():
    """NextCloud callback route.

    Request body: None

    Response (HTML): A redirect to the index page
    """
    token = oauth.nextcloud.authorize_access_token()
    session["nextcloud_token"] = token
    session["nextcloud_authorized"] = True
    return redirect(url_for("index"))

@app.route("/imprint", methods=["GET"])
def imprint():
    """Imprint route.

    Request body: None

    Response (HTML): The imprint page containing all boilerplate information
    """
    return render_template("imprint.html"), 200

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.route("/start_simulation", methods=["POST"])
def start_simulation():
    """Endpoint: POST /start_simulation

    Request body (JSON):
        {
            // form data from the parameters form
        }

    Response (JSON):
        {
            "run_id": "...", # ID of the run, required for checking status and fetching results
        }

    Error Response (JSON) example:
        {
            "error": "Expected JSON payload."
        }
    """
    request_data = request.form
    if request_data is None:
        return jsonify({"error": "Expected form data."}), 400

    # fetch run ID
    run_id = None
    response = requests.get(
        app.config["sim_api"]["endpoint"] + "get_run_id",
        timeout=app.config["sim_api"]["timeout"],
        headers={"Authorization": "Bearer " + app.config["sim_api"]["api_key"]}
    )
    if response.ok:
        data = response.json()
        run_id = data["run_id"] if "run_id" in data else None
    else:
        run_id = None
    if run_id is None:
        return jsonify({"error": "Could not acquire run ID from sim API"}), 501

    # upload config file
    file_content = (
        f'{{ \
            "c_re": {request_data.get("c_re", -0.4)}, \
            "c_im": {request_data.get("c_im", 1.3)}}}'
    ).encode("utf-8")
    file_obj = io.BytesIO(file_content)
    response = requests.post(
        app.config["sim_api"]["endpoint"] + "upload_file/" + run_id,
        files={"file": ("config.json", file_obj)},
        timeout=app.config["sim_api"]["timeout"],
        headers={"Authorization": "Bearer " + app.config["sim_api"]["api_key"]}
    )
    if response.ok:
        data = response.json()
    else:
        return jsonify({"error": "Could not upload config file"}), 501

    # start simulation
    response = requests.post(
        app.config["sim_api"]["endpoint"] + "start_simulation/" + run_id,
        json={"config_file": "config.json"},
        timeout=app.config["sim_api"]["timeout"],
        headers={"Authorization": "Bearer " + app.config["sim_api"]["api_key"]}
    )
    if response.ok:
        data = response.json()
    else:
        return jsonify({"error": "Could not start simulation"}), 501

    return jsonify({"run_id": run_id}), 200

@app.route('/run_status/<run_id>', methods=['GET'])
def run_status(run_id):
    """Endpoint: GET /run_status/<str:run_id>

    Request arguments:
        - run_id -> str: The ID of the run to which the status is requested

    Response (JSON):
        {
            "run_id": "1a2b3c4e5f1a2b3c4e5f1a2b3c4e5f1a", # run ID
            "code": "new",                                # status code, one of:
                                                          # [new, waiting, running,
                                                          # finished, old]
            "timestamp": "2015-01-01 12:00:00"            # server time (default UTC), when
                                                          # the status was written
        }
    """
    response = requests.get(
        app.config["sim_api"]["endpoint"] + "run_status/" + run_id,
        timeout=app.config["sim_api"]["timeout"],
        headers={"Authorization": "Bearer " + app.config["sim_api"]["api_key"]}
    )
    if response.ok:
        data = response.json()
        if "error" in data:
            return jsonify({"error": data["error"]}), 400
        return data, 200
    else:
        return jsonify({"error": "Could not get run status from sim API"}), 501

@app.route('/fetch_results/<run_id>', methods=['GET'])
def fetch_results(run_id):
    """Endpoint: GET /fetch_results/<str:run_id>

    Request arguments:
        - run_id -> str: The ID of the run for which to fetch results

    Response (ByteStream): The results file
    """
    response = requests.post(
        app.config["sim_api"]["endpoint"] + "download_file/" + run_id,
        json={"filename": "julia_set.png"},
        timeout=app.config["sim_api"]["timeout"],
        headers={"Authorization": "Bearer " + app.config["sim_api"]["api_key"]}
    )
    if response.ok:
        return response.content, 200
    else:
        return jsonify({"error": "Could not fetch results from sim API"}), 501
