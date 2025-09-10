"""Simple Flask app for serving the webapp index and some associated routes.
"""

from __future__ import annotations

from pathlib import Path
import io
import uuid
import os
from urllib.parse import urlencode, quote
import requests
import yaml
import debugpy
from flask import Flask, render_template, jsonify, request, session, url_for, redirect
from flask_session import Session
from .nc_requests import ensure_request, fetch_access_token, WEBDAV_REQUEST_PROPFIND_DATA
from .util import parse_webdav_files_response, filename_from_nc_path, encode_nc_path

if os.environ.get("FLASK_ENV") == "development":
    debugpy.listen(("0.0.0.0", 5002))

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

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Index route.

    Request body: None

    Response (HTML): The index page containing all frontend code as SPA
    """
    if "user_id" not in session:
        session["user_id"] = "__anonymous__"
        session["nextcloud_authorized"] = False
    return render_template("index.html", session=session), 200

@app.route("/nextcloud_login", methods=["GET"])
def nextcloud_login():
    """NextCloud login route.

    Request body: None

    Response (HTML): A redirect to the NextCloud login
    """
    if "nextcloud_authorized" in session and session["nextcloud_authorized"]:
        return redirect(url_for("index"))

    session['nextcloud_login_state'] = str(uuid.uuid4())

    qs = urlencode({
        'client_id': app.config['NEXTCLOUD_CLIENT_ID'],
        'redirect_uri': url_for('callback_nextcloud', _external=True),
        'response_type': 'code',
        'scope': "",
        'state': session['nextcloud_login_state'],
    })

    return redirect(app.config['NEXTCLOUD_AUTHORIZE_URL'] + '?' + qs)

@app.route("/nextcloud_logout", methods=["GET"])
def nextcloud_logout():
    """NextCloud logout route.

    Request body: None

    Response (HTML): A redirect to the home page
    """
    if not ("nextcloud_authorized" in session and session["nextcloud_authorized"]):
        return redirect(url_for("index"))

    session["user_id"] = "__anonymous__"
    session["nextcloud_authorized"] = False
    session["nextcloud_access_token"] = None
    session["nextcloud_refresh_token"] = None

    return redirect(url_for("index"))

@app.route('/callback/nextcloud', methods=["GET"])
def callback_nextcloud():
    """NextCloud callback route.

    Request body: None

    Response (HTML): A redirect to the index page
    """
    if "nextcloud_authorized" in session and session["nextcloud_authorized"]:
        redirect(url_for("index"))

    # if the callback request from NextCloud has an error, we might catch this here, however
    # it is not clear how errors are presented in the request for the callback
    # if "error" in request.args:
    #     return jsonify({"error": "NextCloud callback has errors"}), 400

    if str(request.args["state"]) != str(session["nextcloud_login_state"]):
        return jsonify({"error": "CSRF warning! Request states do not match."}), 403

    if "code" not in request.args or request.args["code"] == "":
        return jsonify({"error": "Did not receive valid code in NextCloud callback"}), 400

    response = fetch_access_token(app, request.args["code"])

    if response.status_code != 200:
        return jsonify({"error": "Invalid response while fetching access token"}), 400

    response_data = response.json()
    access_token = response_data.get('access_token')
    if not access_token:
        return jsonify({"error": "Could not find access token in response"}), 400

    refresh_token = response_data.get('refresh_token')
    if not refresh_token:
        return jsonify({"error": "Could not find refresh token in reponse"}), 400

    session["nextcloud_access_token"] = access_token
    session["nextcloud_refresh_token"] = refresh_token
    session["nextcloud_authorized"] = True
    session["user_id"] = response_data.get("user_id")

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

@app.route("/get_run_id", methods=["GET"])
def get_run_id():
    """Endpoint: GET /get_run_id

    Response (JSON):
        {
            "run_id": "...", # ID of the run, required for uploading files, checking status
                             # and fetching results
        }
    """
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
        session["run_id"] = ""
        return jsonify({"error": "Could not acquire run ID from sim API"}), 500

    session["run_id"] = run_id
    return jsonify({"run_id": run_id}), 200

@app.route("/start_simulation_from_form/<run_id>", methods=["POST"])
def start_simulation_from_form(run_id):
    """Endpoint: POST /start_simulation_from_form/<run_id>

    Request arguments (HTTP):
        - run_id -> str: The ID of the run that should be started

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

    # check run ID
    if run_id is None or run_id == "" or run_id != session["run_id"]:
        return jsonify({"error": "Run ID is empty or does not match server-side. Request "
                        + "a new run ID with the corresponding endpoint."}), 409

    # check if input file is set
    input_file = request_data.get("config_file_selection")
    if input_file is None or not input_file or input_file == "":
        return jsonify({"error": "Must be given value for selected config file"}), 500

    # start simulation
    response = requests.post(
        app.config["sim_api"]["endpoint"] + "start_simulation/" + run_id,
        json={"config_file": input_file},
        timeout=app.config["sim_api"]["timeout"],
        headers={"Authorization": "Bearer " + app.config["sim_api"]["api_key"]}
    )
    if not response.ok:
        return jsonify({"error": "Could not start simulation"}), 500

    return jsonify({"run_id": run_id}), 202

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

@app.route('/fetch_results/<run_id>', methods=['POST'])
def fetch_results(run_id):
    """Endpoint: POST /fetch_results/<str:run_id>

    Request arguments (route):
        - run_id -> str: The ID of the run for which to fetch results
    Request arguments (json):
        - destination_dir -> str: The directory path on NC to where the results should
            be uploaded. This should be a NC-encoded path.

    Response (ByteStream): The results file
    """
    file_name = "julia_set.png" # will be dynamic later
    if "destination_dir" not in request.json:
        return jsonify({"error": "No destination specified"}), 400

    # fetch file from sim API
    sim_response = requests.post(
        app.config["sim_api"]["endpoint"] + "download_file/" + run_id,
        json={"filename": file_name},
        timeout=app.config["sim_api"]["timeout"],
        headers={"Authorization": "Bearer " + app.config["sim_api"]["api_key"]}
    )
    if not sim_response.ok:
        return jsonify({"error": "Could not fetch results from sim API"}), 500

    # upload to NC
    user = quote(session["user_id"])
    destination = request.json["destination_dir"] + "/" + file_name
    print(f"destination is {destination}\n")
    print(f"encoded destination is {encode_nc_path(destination)}")
    url = app.config["NEXTCLOUD_API_BASE_URL"] + "remote.php/dav/files/" + user \
        + "/" + encode_nc_path(destination)
    nc_response = ensure_request(url, app, method="PUT", data=sim_response.content)

    if not nc_response.ok:
        return jsonify({"error": "Could not upload results to NextCloud"}), 500

    # return results so the frontend can display them too
    return sim_response.content, 200

@app.route('/get_files', methods=['POST'])
def get_files(dir_path=""):
    """Endpoint: POST /get_files

    Request arguments (JSON):
        - dir_path -> str: The path to the directory for which the contents should be
            listed. This path is relative to the user's root directory.

    Response (JSON): The file list
    """
    if not session["nextcloud_authorized"]:
        return jsonify({"error": "Must be logged in to NextCloud"}), 401

    args = request.json
    dir_path = args.get("dir_path")

    if dir_path != "":
        dir_path = encode_nc_path(dir_path)

    user = quote(session["user_id"])
    url = app.config["NEXTCLOUD_API_BASE_URL"] + "remote.php/dav/files/" + user \
        + "/" + dir_path
    response = ensure_request(url, app, method="PROPFIND", data=WEBDAV_REQUEST_PROPFIND_DATA)
    success, files = parse_webdav_files_response(response.content, session["user_id"])

    if response.ok and success:
        return jsonify(files), 200
    else:
        return jsonify({"error": "Could not fetch files from nextcloud"}), 500

@app.route('/upload_file_to_sim_run/<run_id>', methods=['POST'])
def upload_file_to_sim_run(run_id):
    """Endpoint: POST /upload_file_to_sim_run/<run_id>

    Request arguments (HTTP):
        - run_id -> str: The ID of the run to which to upload to the file
    Request arguments (JSON):
        - file_path -> str: The NC-relative path of the file to upload

    Response (JSON): The file list
    """
    if not session["nextcloud_authorized"]:
        return jsonify({"error": "Must be logged in to NextCloud"}), 401

    if run_id is None or run_id == "" or run_id != session["run_id"]:
        return jsonify({"error": "Run ID is empty or does not match server-side. Request "
                        + "a new run ID with the corresponding endpoint."}), 409

    args = request.json
    file_path = encode_nc_path(args.get("file_path"))
    filename = filename_from_nc_path(file_path)

    user = quote(session["user_id"])
    url = app.config["NEXTCLOUD_API_BASE_URL"] + "remote.php/dav/files/" + user \
        + "/" + file_path
    response = ensure_request(url, app, method="GET")

    if not response.ok:
        return jsonify({"error": "Could not fetch file from NextCloud: "
                       + f"{response.status_code} {response.reason}"}), 404

    file_obj = io.BytesIO(response.content)
    response = requests.post(
        app.config["sim_api"]["endpoint"] + "upload_file/" + run_id,
        files={"file": (filename, file_obj)},
        timeout=app.config["sim_api"]["timeout"],
        headers={"Authorization": "Bearer " + app.config["sim_api"]["api_key"]}
    )
    if not response.ok:
        return jsonify({"error": "Could not upload file to sim API"}), 500

    return ("", 204)
