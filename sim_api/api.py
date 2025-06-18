"""Simple Flask API wrapper around ReSiE for starting simulation.

Endpoints:
    POST /simulate : Run simulation with JSON argument and return console output
"""

from __future__ import annotations

import os
import json
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, request

APP_ROOT = Path(__file__).resolve().parent
TIMEOUT_SECONDS = 300  # Hard stop for long‑running sims

# construct app so routes can be registered via annotation
app = Flask(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_temp_json(data: Dict[str, Any]) -> Path:
    """Write request data to a temp JSON file and return the path."""
    temp_dir = tempfile.gettempdir()
    filename = f"sim_input_{uuid.uuid4().hex}.json"
    file_path = Path(temp_dir) / filename
    with file_path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp)
    return file_path


def _run_simulation(input_file: Path) -> subprocess.CompletedProcess[str]:
    """Run the Julia simulation subprocess and capture output."""
    cmd = ["julia", "simulate.jl", str(input_file)]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)

def _create_run_dir(run_id: str) -> None:
    """Creates a run directory for the given run ID."""
    os.mkdir(Path(APP_ROOT / "runs" / run_id))
    with open(Path(APP_ROOT / "runs" / run_id / "status"), "w", encoding="utf-8") as file:
        file.write(f"new\n{datetime.now()}")

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
