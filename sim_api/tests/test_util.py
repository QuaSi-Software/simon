"""Unit tests for module util."""
import pytest
from werkzeug.datastructures import FileStorage
from sim_api.api import get_app
from sim_api.util import validate_run_id, validate_uploaded_filename

@pytest.fixture()
def app():
    """Fixture to get the app and set it to testing mode"""
    testapp = get_app()
    testapp.config.update({
        "TESTING": True,
    })
    # other setup can go here
    yield testapp
    # clean up / reset resources here

@pytest.fixture()
def client(testapp):
    """Fixture to get a test client"""
    return testapp.test_client()

def test_validate_run_id():
    """Tests for validate_run_id for common good/bad cases."""
    assert not validate_run_id("not an ID")
    assert not validate_run_id("")
    assert not validate_run_id(42)
    assert validate_run_id("1a2b3c4e5f1a2b3c4e5f1a2b3c4e5f1a")
    # weird, but valid IDs
    assert validate_run_id("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert validate_run_id("00000000000000000000000000000000")
