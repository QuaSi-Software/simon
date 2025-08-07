"""Simple Flask API wrapper around ReSiE for starting simulation.

Endpoints:
    POST /simulate : Run simulation with JSON argument and return console output
"""

from __future__ import annotations

import uuid
import json
from pathlib import Path
from flask import Flask, jsonify, request
from sim_api.util import create_run_dir, get_run_status, run_dir_exists, \
    validate_run_id, validate_uploaded_filename, save_file_for_run, load_file_index, \
    alias_config_file, update_run_status, parse_key_from_auth_header

APP_ROOT = Path(__file__).resolve().parent.parent
APP_CONFIG_PATH = APP_ROOT / "api_config.json"

def api_key_required(function):
    """Decorator for routes that require an API key."""
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        api_key = parse_key_from_auth_header(str(auth_header))
        if not api_key:
            return jsonify({'error': 'API key is missing'}), 403
        if api_key not in get_app().config['api_keys']:
            return jsonify({'error': 'API key is not valid'}), 403
        return function(*args, **kwargs)
    # renaming the wrapper is necessary due to a bug in flask. see also
    # https://stackoverflow.com/questions/17256602/assertionerror-view-function-mapping-is-overwriting-an-existing-endpoint-functi
    decorated.__name__ = function.__name__
    return decorated

# ---------------------------------------------------------------------------
# App construction
# ---------------------------------------------------------------------------

# construct app so routes can be registered via annotation
app = Flask("sim_api")

# read config and transfer to app config object
if not APP_CONFIG_PATH.exists() or not APP_CONFIG_PATH.is_file():
    raise FileNotFoundError(f"Configuration file {APP_CONFIG_PATH} does not exist or is " +
                             "not a file.")
with open(APP_CONFIG_PATH, 'r', encoding="utf-8") as config_file:
    app_config = json.load(config_file)
    for key in app_config:
        app.config[key] = app_config[key]

def get_app():
    """Get the global app variable."""
    return app

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/get_run_id", methods=["GET"])
def get_run_id():
    """Endpoint: GET /get_run_id

    Request body: None

    Response (JSON):
        {
            "run_id": "1a2b3c4e5f6"
        }
    """
    run_id = uuid.uuid4().hex
    create_run_dir(run_id)
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
    if not (validate_run_id(run_id) and run_dir_exists(run_id)):
        return jsonify({"error": "Run ID is not valid or run is not set up correctly"}), 500

    status_code, status_ts = get_run_status(run_id)
    if status_code == "unknown":
        return jsonify({"error": "Could not read run status"}), 500

    status_payload = {
        "run_id": run_id,
        "code": status_code,
        "timestamp": status_ts
    }
    return jsonify(status_payload), 200

@app.route("/upload_file/<run_id>", methods=["POST"])
def upload_file(run_id):
    """Endpoint: POST /upload_file/<str:run_id>

    Request arguments:
        - run_id -> str: The ID of the run to which the file is uploaded

    Request body (form-data):
        - file: The file to upload

    Response (JSON):
        {
            "message": "File uploaded successfully"
        }

    Error Response (JSON) example:
        {
            "error": "No file part in the request"
        }
    """
    if not (validate_run_id(run_id) and run_dir_exists(run_id)):
        return jsonify({"error": "Run ID is not valid or run is not set up correctly"}), 500

    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    is_valid, msg = validate_uploaded_filename(file.filename)
    if not is_valid:
        return jsonify({"error": f"Filename of uploaded file is not valid: {msg}"}), 400

    save_file_for_run(run_id, file)
    return jsonify({"message": "File uploaded successfully"}), 200

@app.route("/download_file/<run_id>", methods=["POST"])
def download_file(run_id):
    """Endpoint: POST /download_file/<str:run_id>

    Request arguments:
        - run_id -> str: The ID of the run of which the file is requested

    Request body (JSON):
        {
            "filename": "..." # The name of the file to download
        }

    Response (Bytestream): The file content

    Error Response (JSON) example:
        {
            "error": "No such file exists"
        }
    """
    if not (validate_run_id(run_id) and run_dir_exists(run_id)):
        return jsonify({"error": "Run ID is not valid or run is not set up correctly"}), 500

    request_data = request.get_json(force=True, silent=True)
    if request_data is None:
        return jsonify({"error": "Expected JSON payload."}), 400

    if "filename" not in request_data:
        return jsonify({"error": "Missing JSON argument `filename`"}), 400

    filename = request_data['filename']
    file_index = load_file_index(run_id)
    if filename not in file_index["forward"]:
        return jsonify({"error": "Cannot find given `filename` in file index"}), 400

    alias = file_index["forward"][filename]
    alias_path = Path(APP_ROOT / "runs" / run_id / alias)
    if not alias_path.exists():
        return jsonify({"error": "Cannot find alias for given `filename`"}), 400

    with open(alias_path, 'rb') as f:
        content = f.read()

    response = app.response_class(content, mimetype='application/octet-stream')
    response.headers.set('Content-Disposition', f'attachment; filename={filename}')
    return response, 200

@app.route("/start_simulation/<run_id>", methods=["POST"])
def simulate(run_id):
    """Endpoint: POST /start_simulation/<run_id>

    Request arguments:
        - run_id -> str: The ID of the run to which the file is uploaded

    Request body (JSON):
        {
            "config_file": "resie_input.json" # the filename of the config file
        }

    Response (JSON):
        {
            "message": "Queued run for simulation"
        }

    Error Response (JSON) example:
        {
            "error": "Expected JSON payload."
        }
    """
    if not (validate_run_id(run_id) and run_dir_exists(run_id)):
        return jsonify({"error": "Run ID is not valid or run is not set up correctly"}), 500

    request_data = request.get_json(force=True, silent=True)
    if request_data is None:
        return jsonify({"error": "Expected JSON payload."}), 400

    if "config_file" not in request_data:
        return jsonify({"error": "Missing JSON argument `config_file`"}), 400

    config_filename = str(request_data["config_file"])
    file_index = load_file_index(run_id)
    if config_filename not in file_index["forward"]:
        return jsonify({"error": "Cannot find given `config_file` in file index"}), 400

    alias = file_index["forward"][config_filename]
    alias_path = Path(APP_ROOT / "runs" / run_id / alias)
    if not alias_path.exists():
        return jsonify({"error": "Cannot find alias for given `config_file`"}), 400

    success, msg = alias_config_file(run_id, alias)
    if not success:
        return jsonify({"error": f"Could not load config_file: {msg}"}), 400
    _aliased_path = msg # it's only a message in the error case, otherwise a filepath

    update_run_status(run_id, "waiting")
    return jsonify({"message": "Queued run for simulation"}), 200
