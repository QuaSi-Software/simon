"""Utility functions for the simulation API."""
from __future__ import annotations

import os
import json
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


APP_ROOT = Path(__file__).resolve().parent
TIMEOUT_SECONDS = 300  # Hard stop for long‑running sims

def write_temp_json(data: Dict[str, Any]) -> Path:
    """Write request data to a temp JSON file and return the path."""
    temp_dir = tempfile.gettempdir()
    filename = f"sim_input_{uuid.uuid4().hex}.json"
    file_path = Path(temp_dir) / filename
    with file_path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp)
    return file_path

def run_simulation(input_file: Path) -> subprocess.CompletedProcess[str]:
    """Run the Julia simulation subprocess and capture output."""
    cmd = ["julia", "simulate.jl", str(input_file)]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)

def create_run_dir(run_id: str) -> None:
    """Creates a run directory for the given run ID."""
    os.mkdir(Path(APP_ROOT / "runs" / run_id))
    with open(Path(APP_ROOT / "runs" / run_id / "status"), "w", encoding="utf-8") as file:
        file.write(f"new\n{datetime.now()}")

def validate_run_id(run_id: str) -> bool:
    """Validates the given run_id.

    This checks if the ID looks like something created by UUID4 hex representation."""
    return (
        isinstance(run_id, str)
        and len(str(run_id)) == 32
        and all(c in '0123456789abcdef' for c in str(run_id))
    )

def run_dir_exists(run_id: str) -> bool:
    """Checks if the run directory exists for the given run_id."""
    run_dir = Path(APP_ROOT / "runs" / run_id)
    return run_dir.exists() and run_dir.is_dir()

def get_run_status(run_id: str) -> tuple[str,str]:
    """Reads the run status from the status file in the run dir."""
    status_file = Path(APP_ROOT / "runs" / run_id / "status")
    if not status_file.exists():
        return "unknown", "1970-01-01 00:00:00.0"

    with open(status_file, "r", encoding="utf-8") as file:
        lines = file.readlines()
        if len(lines) < 2:
            return "unknown", "1970-01-01 00:00:00.0"
        return lines[0].strip(), lines[1].strip()
