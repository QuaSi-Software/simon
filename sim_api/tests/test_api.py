"""Unit tests for module api."""
import uuid
from pathlib import Path
from io import BytesIO
import pytest
from werkzeug.datastructures import FileStorage
from sim_api.api import get_app
from sim_api.util import save_file_for_run, create_run_dir, get_run_status

@pytest.fixture(name="app")
def fixture_app():
    """Fixture to get the app and set it to testing mode"""
    testapp = get_app()
    testapp.config.update({
        "TESTING": True,
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
    })

    # check response
    assert response.status_code == 200
    assert "error" not in response.json
    assert "message" in response.json
    assert "Queued run for simulation" in response.json["message"]

    # check config was aliased and status updated
    assert Path(Path(__file__).resolve().parent.parent / "runs" / run_id / "output.txt").exists
    status, date = get_run_status(run_id)
    assert status == "waiting"
    assert date != "1970-01-01 00:00:00.0"
