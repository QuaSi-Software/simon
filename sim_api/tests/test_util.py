"""Unit tests for module util."""
import uuid
from pathlib import Path
from io import BytesIO
from werkzeug.datastructures import FileStorage
from sim_api.util import validate_run_id, validate_uploaded_filename, save_file_for_run, \
    create_run_dir, parse_key_from_auth_header, check_node_and_replace

def test_validate_run_id():
    """Tests for validate_run_id for common good/bad cases."""
    assert not validate_run_id("not an ID")
    assert not validate_run_id("")
    assert not validate_run_id(42)
    assert validate_run_id("1a2b3c4e5f1a2b3c4e5f1a2b3c4e5f1a")
    # weird, but valid IDs
    assert validate_run_id("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert validate_run_id("00000000000000000000000000000000")

def test_validate_uploaded_filename():
    """Tests for validate_uploaded_filename without client"""
    # filename is empty
    file = FileStorage(filename="")
    success, msg = validate_uploaded_filename(file.filename)
    assert not success
    assert "No filename provided" in msg

    # filename contains forbidden characters
    file = FileStorage(filename="a\"/2:")
    success, msg = validate_uploaded_filename(file.filename)
    assert not success
    assert "Filename must contain only" in msg

    # filename collapses to empty string
    file = FileStorage(filename=" \n\t \r")
    success, msg = validate_uploaded_filename(file.filename)
    assert not success
    assert "Filename collapses" in msg

    # filename attempts path traversal "hidden" by whitespace
    file = FileStorage(filename="\t..important config")
    success, msg = validate_uploaded_filename(file.filename)
    assert not success
    assert "Filename must not start with period" in msg

    # normal filenames
    file = FileStorage(filename="ideal_filename.json")
    success, msg = validate_uploaded_filename(file.filename)
    assert success
    assert "Filename appears valid" in msg

    file = FileStorage(filename="  with §3,14 oddities \t+(500$) but valid.old.json")
    success, msg = validate_uploaded_filename(file.filename)
    assert success
    assert "Filename appears valid" in msg

def test_save_file_for_run():
    """Tests for save_file_for_run"""
    # normal file saving
    run_id = uuid.uuid4().hex
    create_run_dir(run_id)
    file = FileStorage(BytesIO("file contents".encode("utf8")), filename="test.txt")
    filename = save_file_for_run(run_id, file)
    assert Path(Path(__file__).resolve().parent.parent / "runs" / run_id / filename).exists

    # malicious file is circumvented
    run_id = uuid.uuid4().hex
    create_run_dir(run_id)
    file = FileStorage(
        BytesIO("r m -rf --no-preserve-root /".encode("utf8")), # don't remove the space in 'r m'
        filename=("../path/traversal/" + '"' + "\n" + "escape.sh")
    )
    filename = save_file_for_run(run_id, file)
    assert Path(Path(__file__).resolve().parent.parent / "runs" / run_id / filename).exists

def test_parse_key_from_auth_header():
    """Tests for parse_key_from_auth_header"""
    # good input
    assert parse_key_from_auth_header("Bearer 192378z873de8913g") == "192378z873de8913g"
    assert parse_key_from_auth_header("bearer  192378z873de8913g") == "192378z873de8913g"
    # bas input
    assert not parse_key_from_auth_header("")
    assert not parse_key_from_auth_header("82fhj39whf")
    assert not parse_key_from_auth_header("flisdahf isuadfhsadi 92374239")

def test_check_node_and_replace():
    """Tests for check_node_and_replace"""
    file_index = {
        "forward": {
            "foo.prf": "uasf654",
            "profile_with_no_ending": "1238hjf"
        }
    }
    # empty input
    assert check_node_and_replace({}, file_index) == {}
    assert check_node_and_replace([], file_index) == []
    # primitive input
    assert check_node_and_replace("foo", file_index) == "foo"
    assert check_node_and_replace("foo.prf", file_index) == "./uasf654"
    assert check_node_and_replace(1, file_index) == 1
    # nested lists and dicts
    lst = ["foo.prf", 1, [2, "foo", 3.0]]
    assert check_node_and_replace(lst, file_index) == ["./uasf654", 1, [2, "foo", 3.0]]
    dct = {"foo": {"bar": "profile_with_no_ending", "foo": 1}, "a": ["foo.prf", 2], "b": 3.0}
    assert check_node_and_replace(dct, file_index) == {
        "foo": {"bar": "./1238hjf", "foo": 1}, "a": ["./uasf654", 2], "b": 3.0
    }
