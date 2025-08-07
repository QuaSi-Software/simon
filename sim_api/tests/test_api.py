"""Unit tests for module api."""
import uuid
from pathlib import Path
from io import BytesIO
import pytest
from werkzeug.datastructures import FileStorage
from sim_api.api import get_app
from sim_api.util import save_file_for_run, create_run_dir, get_run_status, load_file_index

@pytest.fixture(name="app")
def fixture_app():
    """Fixture to get the app and set it to testing mode"""
    testapp = get_app()
    testapp.config.update({
        "TESTING": True,
        "api_keys": ["123456789abcdef"]
    })
    # other setup can go here
    yield testapp
    # clean up / reset resources here

@pytest.fixture(name="client")
def fixture_client(app):
    """Fixture to get a test client"""
    return app.test_client()

def test_endpoint_start_simulation_good_input(client):
    """Tests endpoint start_simulation with good input."""
    # set up run
    run_id = uuid.uuid4().hex
    create_run_dir(run_id)

    # upload data file
    data_raw_str = """foo;bar\n0.1;0.2"""
    data_fs = FileStorage(BytesIO(data_raw_str.encode("utf8")), filename="some_file.csv")
    save_file_for_run(run_id, data_fs)

    # upload config
    config_raw_str = """{
        "foo": "bar",
        "some_file": "some_file.csv"
    }"""
    config_fs = FileStorage(BytesIO(config_raw_str.encode("utf8")), filename="config.json")
    save_file_for_run(run_id, config_fs)

    # start simulation
    response = client.post("/start_simulation/" + run_id, json={
        "config_file": "config.json"
    }, headers={
        "Authorization": "Bearer 123456789abcdef"
    })

    # check response
    assert response.status_code == 200
    assert "error" not in response.json
    assert "message" in response.json
    assert "Queued run for simulation" in response.json["message"]

    # check config was aliased
    file_index = load_file_index(run_id)
    alias = file_index["forward"]["some_file.csv"]
    assert Path(Path(__file__).resolve().parent.parent / "runs" / run_id / alias).exists()
    alias_config_path = Path(
        Path(__file__).resolve().parent.parent / "runs" / run_id / "aliased_config.json"
    )
    with open(alias_config_path, "r", encoding="utf-8") as file:
        content = file.read()
        assert alias in content

    # check status was updated
    status, date = get_run_status(run_id)
    assert status == "waiting"
    assert date != "1970-01-01 00:00:00.0"

def test_endpoint_download_file_good_input(client):
    """Tests endpoint download_file with good input."""
    # set up run
    run_id = uuid.uuid4().hex
    create_run_dir(run_id)
    file_raw_str = """Lorem ipsum"""
    file_fs = FileStorage(BytesIO(file_raw_str.encode("utf8")), filename="output.txt")
    save_file_for_run(run_id, file_fs)

    # request file
    response = client.post("/download_file/" + run_id, json={
        "filename": "output.txt"
    }, headers={
        "Authorization": "Bearer 123456789abcdef"
    })

    # check response
    assert response.status_code == 200
    assert response.data is not None

    # put bytestream into string and check
    content = response.data.decode("utf-8")
    assert content == "Lorem ipsum"
