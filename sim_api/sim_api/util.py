"""Utility functions for the simulation API."""
from __future__ import annotations

import os
import stat
import json
import uuid
import re
from datetime import datetime
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict
from werkzeug.datastructures import FileStorage

APP_ROOT = Path(__file__).resolve().parent.parent

WIDGET_TYPE_MAP = {
    "Float64": "FLOAT",
    "Union{Nothing, String}": "STRING",
    "Int64": "INT",
    "Vector{String}": "VECTOR_STRING",
    "Vector{Float64}": "VECTOR_FLOAT",
    "Bool": "BOOLEAN",
    "Vector{Union{Nothing, Float64}}": "VECTOR_FLOAT",
    "String": "STRING",
    "UInt64": "INT",
    "Union{Nothing, Float64}": "FLOAT",
}

DATE_PARAMETERS = {
    "start", "start_output", "end"
}

OBJECT_PARAMETERS = {
    "sankey_plot_spec", "output_plot_spec", "csv_output_keys"
}

def parse_key_from_auth_header(header: str) -> str:
    """Parses an API from the given value of the authorization header."""
    header = re.sub(r"\s+", " ", header.strip()) # compress consecutive whitespaces into a
    parts = header.split(" ")                    # single space character, so we can split
    if len(parts) < 2:
        return False
    if parts[0].lower() != "bearer":
        return False
    return parts[1].strip()

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

def check_node_and_replace(node, file_index):
    """Recursively replaces strings in the given JSON-like structure with file name
    substitutions based on the given file index.

    The substitutions will ignore existing paths of file parameters and replace it with
    relative paths.
    """
    if type(node) == str:
        for original in file_index["forward"]:
            if original in node:
                return "./" + file_index["forward"][original]
    elif type(node) == dict:
        for key in node.keys():
            node[key] = check_node_and_replace(node[key], file_index)
    elif type(node) == list:
        for idx, _ in enumerate(node):
            node[idx] = check_node_and_replace(node[idx], file_index)

    return node

def alias_config_file(run_id: str, alias_filename) -> tuple[bool,str]:
    """Creates an aliased copy of the given config file.

    All references to files that exist in the file index (which are uploaded) are replaced
    by their alias. However this also changes the path to a relative path of './' followed
    by the aliased file name. In addition, the output file settings are set to fixed values
    so that fetching the results knows where to find the files.
    """
    alias_path = Path(APP_ROOT / "runs" / run_id / alias_filename)
    if not alias_path.exists():
        return False, "Could not find alias file"

    with open(alias_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    # set base to the run directory so relative paths point to the correct dir for the run
    config["io_settings"]["base_path"] = str(Path(APP_ROOT / "runs" / run_id))

    # replace output filenames with fixed values
    config["io_settings"]["csv_output_file"] = "./out.csv"
    config["io_settings"]["auxiliary_info_file"] = "./auxiliary_info.md"
    config["io_settings"]["output_plot_file"] = "./output_plot.html"
    config["io_settings"]["sankey_plot_file"] = "./output_sankey.html"
    config["io_settings"]["auxiliary_plots_path"] = "./"

    # replace file names with their alias. this will remove any paths, making any
    # replacements relative to the base path
    file_index = load_file_index(run_id)
    config = check_node_and_replace(config, file_index)

    aliased_config_path = Path(APP_ROOT / "runs" / run_id / "aliased_config.json")
    content = json.dumps(config, ensure_ascii=False, indent=4)
    with open(aliased_config_path, "w", encoding="utf-8") as file:
        file.write(content)

    return True, aliased_config_path

def read_resie_version() -> str | None:
    """Read the version string from the ReSiE Project.toml file.

    Returns the version string on success or `None` if anything goes wrong.
    """
    toml_path = APP_ROOT / "resie" / "Project.toml"
    if not toml_path.exists():
        return None

    try:
        with open(toml_path, "r", encoding="utf-8") as fp:
            for line in fp:
                stripped = line.strip()
                if stripped.startswith("version"):
                    parts = stripped.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
    except Exception as exc:
        return None
    return None

def deep_merge_write(a: dict, b: dict) -> dict:
    """Merge two possibly nested dictionaries by adding and overwriting keys from b into a.

    Source - https://stackoverflow.com/a/7205107
    Posted by andrew cooke, modified by community. See post 'Timeline' for change history
    Retrieved 2026-05-28, License - CC BY-SA 4.0
    Further modified by Etienne Ott
    """
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                deep_merge_write(a[key], b[key])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

def widget_type_for_param(name: str, param_dict: dict, medium_pattern=None) -> str:
    """
    Returns the widget type for the given parameter based several factors.
    """
    if medium_pattern is None:
        medium_pattern = re.compile("m_.+_(in|out)")

    if "options" in param_dict and param_dict["options"] != []:
        if isinstance(param_dict["default"], list):
            return "MULTISELECT"
        else:
            return "DROPDOWN"

    elif name in DATE_PARAMETERS:
        return "DATE"

    elif name in OBJECT_PARAMETERS:
        return "CUSTOM_OBJECT"

    elif medium_pattern.match(name) or name == "medium":
        return "MEDIUM"

    elif param_dict["type"] in WIDGET_TYPE_MAP:
        return WIDGET_TYPE_MAP[param_dict["type"]]

    else:
        return "STRING" # fallback for unknown types

def set_widget_types(susi_dict: dict) -> dict:
    """
    Iterates through the given dict for SUSI parameters and sets the widget type for
    each parameter. This is based on the type it has as well as its options, if any.
    """
    medium_pattern = re.compile("m_.+_(in|out)")

    # set for component parameters
    for type_dict in susi_dict["components"]["types"].values():
        for sub_dict in ["economic", "emissions", "parameters"]:
            for name, param_dict in type_dict[sub_dict].items():
                param_dict["widget_type"] = widget_type_for_param(name, param_dict, medium_pattern)

    # set for control parameters
    for name, param_dict in susi_dict["components"]["control"].items():
        param_dict["widget_type"] = widget_type_for_param(name, param_dict, medium_pattern)

    # set for control modules' parameters
    for module_dict in susi_dict["components"]["control_modules"].values():
        for name, param_dict in module_dict.items():
            param_dict["widget_type"] = widget_type_for_param(name, param_dict, medium_pattern)

    # set for general parameters
    for sub_dict in ["economic", "emissions", "io_settings", "simulation"]:
        for name, param_dict in susi_dict["general"][sub_dict].items():
            param_dict["widget_type"] = widget_type_for_param(name, param_dict, medium_pattern)

    return susi_dict

def format_parameters_susi(base_dict: dict) -> dict:
    """Formats the given parameters definition dictionary for the `susi` format."""
    susi_dict = deepcopy(base_dict)

    # determine widget types
    susi_dict = set_widget_types(susi_dict)

    # find most recent version of "patch file" with additional attributes
    version_str = read_resie_version()
    if not version_str:
        raise KeyError("Cannot read ReSiE version")

    v_str = version_str.split(".")
    version = [int(v_str[0]), int(v_str[1]), int(v_str[2])]
    file_path = None
    file_found = False

    while not file_found:
        v_str = f"{version[0]}.{version[1]}.{version[2]}"
        file_path = APP_ROOT / "data" / "formats" / "susi" / ("v" + v_str + ".json")
        if Path.is_file(file_path):
            file_found = True
            break
        else:
            if version[2] > 0:
                version[2] -= 1
            elif version[1] > 0:
                version[1] -= 1
                version[2] = 99
            else:
                raise KeyError(f"Cannot find ReSiE version file for version {version_str} or earlier")

    # merge-write the attributes into the copy of the base_dict
    with open(file_path, "r", encoding="utf-8") as fp:
        content = json.load(fp)
        susi_dict = deep_merge_write(susi_dict, content)

    return susi_dict

def read_resie_parameters() -> dict:
    """Read parameter definitions for ReSiE from the cached files.

    Returns the parsed dictionary with all groupings. If parsing any grouping fails, that
    grouping will be empty, but will always return the secondmost-top-level dictionary.

    The top-most level of the dictionary is sorted by implemented formats.
    """
    all_formats = {}
    base_dict = {}
    files = {
        "components": "component_parameters.json",
        "general": "general_parameters.json"
    }

    for key, file_name in files.items():
        json_path = APP_ROOT / file_name
        if not json_path.exists():
            continue

        content = {}
        try:
            with open(json_path, "r", encoding="utf-8") as fp:
                content = json.loads(fp.read())
        except:
            pass
        base_dict[key] = content

    all_formats["base"] = base_dict
    all_formats["susi"] = format_parameters_susi(base_dict)

    return all_formats
