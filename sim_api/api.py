"""Simple Flask API wrapper around ReSiE for starting simulation.

Endpoints:
    POST /simulate : Run simulation with JSON argument and return console output
"""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path
from util import _create_run_dir, _get_run_status, _run_dir_exists, _run_simulation, \
    _validate_run_id, _write_temp_json

from flask import Flask, jsonify, request

APP_ROOT = Path(__file__).resolve().parent
TIMEOUT_SECONDS = 300  # Hard stop for long‑running sims

# construct app so routes can be registered via annotation
app = Flask(__name__)

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
    _create_run_dir(run_id)
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
    if not (_validate_run_id(run_id) and _run_dir_exists(run_id)):
        return jsonify({"error": "Run ID is not valid or run is not set up correctly"}), 500

    status_code, status_ts = _get_run_status(run_id)
    if status_code == "unknown":
        return jsonify({"error": "Could not read run status"}), 500

    status_payload = {
        "run_id": run_id,
        "code": status_code,
        "timestamp": status_ts
    }
    return jsonify(status_payload), 200

@app.route("/simulate", methods=["POST"])
def simulate():
    """Endpoint: POST /simulate

    Request body (JSON): arbitrary JSON payload that the Julia simulation
    expects. The payload is written to a temporary file and passed as the
    first argument to `simulate.jl`.

    Response (JSON):
        {
            "stdout": "...",      # Standard output from Julia process
            "stderr": "...",      # Standard error from Julia process
            "exit_code": 0         # Exit code of the process
        }

    If the simulation times out or the Julia script is not found, an error
    response is returned with the appropriate HTTP status code."""
    data = request.get_json(force=True, silent=True)
    if data is None:
        return jsonify({"error": "Expected JSON payload."}), 400

    # Save input JSON to a temporary file
    input_path = _write_temp_json(data)

    # Run the simulation and capture output
    try:
        result = _run_simulation(input_path)
        response = {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
        status_code = 200 if result.returncode == 0 else 500
        return jsonify(response), status_code
    except subprocess.TimeoutExpired:
        return jsonify({"error": f"Simulation timed out after {TIMEOUT_SECONDS} seconds."}), 504
    except FileNotFoundError:
        return jsonify({"error": "Julia executable or simulation script not found."}), 500
    finally:
        # Clean up temporary file
        try:
            input_path.unlink(missing_ok=True)
        except OSError:
            pass
