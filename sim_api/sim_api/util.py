"""Utility functions for the simulation API."""
from __future__ import annotations

import os
import stat
import json
import subprocess
import tempfile
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from werkzeug.datastructures import FileStorage


APP_ROOT = Path(__file__).resolve().parent.parent
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

def update_run_status(run_id: str, new_status: str) -> None:
    """Update the status of the given run with the new status."""
    with open(Path(APP_ROOT / "runs" / run_id / "status"), "w", encoding="utf-8") as file:
        file.write(f"{new_status}\n{datetime.now()}")

def create_run_dir(run_id: str) -> None:
    """Creates a run directory for the given run ID."""
    os.mkdir(Path(APP_ROOT / "runs" / run_id))
    update_run_status(run_id, "new")

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

def validate_uploaded_filename(filename: str) -> tuple[bool,str]:
    """Validates the given filename of a presumably uploaded file.

    Note: This validation cannot be perfect, it merely catches some common problems
    and attack vectors.
    """
    if not filename or filename == "":
        return False, "No filename provided"

    # check for any bad characters. unicode "letters" should be included in \w
    pattern = r"[^\d\w\s\-.,#+=())&%$§~!{}\[\]]+"
    matches = re.findall(pattern, filename)
    if len(matches) > 0:
        return False, "Filename must contain only alphanumeric (unicode) characters, " + \
                      "whitespace and the following characters: .,_-#+=&%$§~!(){}[]"

    # replace all whitespace characters with empty string to check if it collapses
    # to an empty string
    collapsed = re.sub(r"\s+", "", filename)
    if collapsed == "":
        return False, "Filename collapses to empty string when all whitespace is removed"

    # replace all whitespace characters with space, trim the string, so in the following
    # we can check against the "text" part of the filename
    trimmed = re.sub(r"\s+", " ", filename).strip()

    # forbid path traversal and hidden files at the beginning. since / is already forbidden,
    # we only have to check the beginning
    if trimmed[0] == ".":
        return False, "Filename must not start with period"

    return True, "Filename appears valid"

def load_file_index(run_id: str) -> dict:
    """Reads the file index for the given run."""
    file_index_path = Path(APP_ROOT / "runs" / run_id / "file_index.json")
    if not (file_index_path.exists() and file_index_path.is_file()):
        return {"forward": {}, "reverse": {}}

    try:
        with open(file_index_path, "r", encoding="utf-8") as file:
            file_index = json.load(file)
    except json.JSONDecodeError:
        return {"forward": {}, "reverse": {}}

    return file_index

def write_file_index(run_id: str, file_index: dict) -> None:
    """Writes the file index for the given run."""
    file_index_path = Path(APP_ROOT / "runs" / run_id / "file_index.json")
    with open(file_index_path, "w", encoding="utf-8") as file:
        json.dump(file_index, file, indent=4)

def save_file_for_run(run_id: str, file: FileStorage) -> str:
    """Saves the given file in the given run in a safe manner by renaming it"""
    file_index = load_file_index(run_id)

    if file.filename in file_index["forward"]:
        safe_filename = file_index["forward"][file.filename]
    else:
        safe_filename = uuid.uuid4().hex
        file_index["forward"][file.filename] = safe_filename
        file_index["reverse"][safe_filename] = file.filename

    write_file_index(run_id, file_index)

    filepath = Path(APP_ROOT / "runs" / run_id / safe_filename)
    file.save(filepath)
    # set as owner-has-write, group-has-read, other-has-read
    os.chmod(filepath, stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

    return safe_filename

def alias_config_file(run_id: str, alias_filename) -> tuple[bool,str]:
    """Creates a copy of the given config file where all references to files are replaced
    by their alias."""
    alias_path = Path(APP_ROOT / "runs" / run_id / alias_filename)
    if not alias_path.exists():
        return False, "Could not find alias file"

    with open(alias_path, "r", encoding="utf-8") as file:
        content = file.read()
        file_index = load_file_index(run_id)
        for original in file_index["forward"]:
            content = content.replace(original, file_index["forward"][original])

    aliased_config_path = Path(APP_ROOT / "runs" / run_id / "aliased_config.json")
    with open(aliased_config_path, "w", encoding="utf-8") as file:
        file.write(content)

    return True, aliased_config_path
