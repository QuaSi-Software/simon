"""Unit tests for module util."""
from sim_api.util import validate_run_id

def test_validate_run_id():
    """Tests for validate_run_id for common good/bad cases."""
    assert not validate_run_id("not an ID")
    assert not validate_run_id("")
    assert not validate_run_id(42)
    assert validate_run_id("1a2b3c4e5f1a2b3c4e5f1a2b3c4e5f1a")
    # weird, but valid IDs
    assert validate_run_id("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert validate_run_id("00000000000000000000000000000000")
