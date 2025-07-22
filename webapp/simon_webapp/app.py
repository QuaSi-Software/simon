"""Simple Flask app for serving the webapp index and some associated routes.
"""

from __future__ import annotations

from pathlib import Path
import io
import requests
from flask import Flask, render_template, jsonify, request

APP_ROOT = Path(__file__).resolve().parent.parent
SIM_API_ROOT = "http://sim_api:5000/" # @TODO: Implement linking via config
SIM_API_TIMEOUT = 30

# construct app so routes can be registered via annotation
app = Flask("simon_webapp")

# set configs (@TODO: move this to a config file)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
# enables autoreload for templates, useful for dev (@TODO: should this be enabled for production?)
app.config['TEMPLATES_AUTO_RELOAD'] = True

def get_app():
    """Get the global app variable."""
    return app

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Index route.

    Request body: None

    Response (HTML): The index page containing all frontend code as SPA
    """
    return render_template("index.html"), 200

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
    response = requests.get(SIM_API_ROOT + "get_run_id", timeout=SIM_API_TIMEOUT)
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
        SIM_API_ROOT + "upload_file/" + run_id,
        files={"file": ("config.json", file_obj)},
        timeout=SIM_API_TIMEOUT
    )
    if response.ok:
        data = response.json()
    else:
        return jsonify({"error": "Could not upload config file"}), 501

    # start simulation
    response = requests.post(
        SIM_API_ROOT + "start_simulation/" + run_id,
        json={"config_file": "config.json"},
        timeout=SIM_API_TIMEOUT
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
    response = requests.get(SIM_API_ROOT + "run_status/" + run_id, timeout=SIM_API_TIMEOUT)
    if response.ok:
        data = response.json()
        if "error" in data:
            return jsonify({"error": data["error"]}), 400
        return data, 200
    else:
        return jsonify({"error": "Could not get run status from sim API"}), 501
