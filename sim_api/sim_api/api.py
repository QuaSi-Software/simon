"""Simple Flask API wrapper around ReSiE for starting simulation.

Endpoints:
    POST /simulate : Run simulation with JSON argument and return console output
"""

from __future__ import annotations

import uuid
import yaml
from pathlib import Path
from flask import Flask, jsonify, request
from sim_api.util import create_run_dir, get_run_status, run_dir_exists, \
    validate_run_id, validate_uploaded_filename, save_file_for_run, load_file_index, \
    alias_config_file, update_run_status, parse_key_from_auth_header, read_resie_version, \
    read_resie_parameters

APP_ROOT = Path(__file__).resolve().parent.parent
APP_CONFIG_PATH = APP_ROOT / "api_config.yml"

# cached value for the ReSiE version. It will be filled on first request defaulting to None
# indicating we haven't read it yet.
RESIE_VERSION: str | None = None

# cached value for the ReSiE parameters. it will be filled on first request, defaulting to
# None indicating we haven't read it yet. The structure contains various parameter dicts
# each can be nested containing the parameter definitions. the upper-most level contains
# various parameters groupings, which are hard-coded. all deeper nested dicts are fetched
# for the current ReSiE version during start-up of the API server
RESIE_PARAMETERS: dict | None = None

RESULTS_FILES = {
    "auxiliary_info.md",
    "logfile_balanceWarn.log",
    "logfile_general.log",
    "out.csv",
    "output_plot.html",
    "output_sankey.html"
}

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
    app_config = yaml.safe_load(config_file)
    for key in app_config:
        app.config[key] = app_config[key]

def get_app():
    """Get the global app variable."""
    return app

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/get_run_id", methods=["GET"])
@api_key_required
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
@api_key_required
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
@api_key_required
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
@api_key_required
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

    if filename in file_index["forward"]:
        alias = file_index["forward"][filename]
    elif filename in RESULTS_FILES:
        alias = filename
    else:
        return jsonify({"error": "Cannot find given `filename` in file index"}), 400

    alias_path = Path(APP_ROOT / "runs" / run_id / alias)
    if not alias_path.exists():
        return jsonify({"error": "Cannot find alias for given `filename`"}), 400

    with open(alias_path, 'rb') as f:
        content = f.read()

    response = app.response_class(content, mimetype='application/octet-stream')
    response.headers.set('Content-Disposition', f'attachment; filename={filename}')
    return response, 200

@app.route("/start_simulation/<run_id>", methods=["POST"])
@api_key_required
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

@app.route('/resie_version', methods=['GET'])
def resie_version():
    """Endpoint: GET /resie_version

    Response (JSON):
        {
            "version": "0.13.0", # the version of ReSiE being used
        }
    """
    # lazily load and cache the version string
    global RESIE_VERSION
    if RESIE_VERSION is None:
        parsed = read_resie_version()
        if parsed is None:
            return jsonify({"error": f"Could not read ReSiE version"}), 500
        else:
            RESIE_VERSION = parsed
    return jsonify({"version": RESIE_VERSION}), 200

@app.route('/parameters/<format>', methods=['GET'])
def resie_parameters(format):
    """Endpoint: GET /parameters

    Request arguments:
        - format -> str: The format in which the parameter definitions are requested.
            Options are: `susi`, `base`

    Response (JSON): The parameter definitions for various groupings. The upper-most level
        of the nested structure has the following keys: `components`
    """
    if format not in ("susi", "base"):
        return jsonify({"error": f"Invalid format specified"}), 400

    # lazily load and cache the parameter definitions.
    # the lazy-loading also helps with a problem where the definitions are written to file
    # typically after the flask server is already running, because the scanner is starting
    # in parallel to the server and is slower. if we read the definitions only on the first
    # requests, this helps mitigate sync issues (though it can still happen with requests
    # coming in before the scanner is up)
    global RESIE_PARAMETERS
    if RESIE_PARAMETERS is None:
        RESIE_PARAMETERS = read_resie_parameters()
    return jsonify(RESIE_PARAMETERS[format]), 200
