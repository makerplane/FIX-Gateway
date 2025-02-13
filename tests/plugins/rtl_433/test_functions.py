import pytest
from fixgw.plugins.rtl_433 import (
    convert_type,
    apply_transform,
    get_rtl_433_path,
    start_rtl_433,
    process_json,
)
import os
import subprocess
from unittest.mock import patch, MagicMock
from fixgw import cfg

import json


@pytest.mark.parametrize(
    "value, dtype, expected",
    [
        (42, "int", 42),
        ("42", "int", 42),
        (42.7, "int", 42),  # Floats should truncate
        ("invalid", "int", "invalid"),  # Conversion failure, return original
        (42.5, "float", 42.5),
        ("42.5", "float", 42.5),
        ("invalid", "float", "invalid"),  # Invalid float should return original
        (1, "bool", True),
        (0, "bool", False),
        ("True", "bool", True),
        ("False", "bool", True),  # Any non-empty string is True in Python
        ("", "bool", False),
        ("test", "string", "test"),
        (123, "string", "123"),
    ],
)
def test_convert_type(value, dtype, expected):
    """Test that convert_type properly converts values."""
    assert convert_type(value, dtype) == expected


@pytest.mark.parametrize(
    "value, transform, expected",
    [
        (10, {"scale": 2}, 20),  # Scaling
        (10, {"offset": 5}, 15),  # Offset
        (10, {"scale": 2, "offset": 5}, 25),  # Scale and offset combined
        (10.567, {"round": 2}, 10.57),  # Rounding
        (10.567, {"round": 0}, 11),  # Rounding to integer
        (10, {"threshold": 5}, 1),  # Threshold (above)
        (4, {"threshold": 5}, 0),  # Threshold (below)
        (10, {"type": "int"}, 10),  # Type conversion
        (10.7, {"type": "int"}, 10),  # Convert float to int
        (10, {"scale": 2, "type": "float"}, 20.0),  # Apply scale then convert
        (None, {}, None),  # None should stay None
        ("test", {}, "test"),  # Strings remain unchanged if no transform applied
    ],
)
def test_apply_transform(value, transform, expected):
    """Test that apply_transform correctly applies scaling, offset, rounding, threshold, and type conversion."""
    assert apply_transform(value, transform) == expected


def test_get_rtl_433_path_normal():
    """Test that get_rtl_433_path returns 'rtl_433' when not running inside a Snap."""
    with patch.dict(os.environ, {}, clear=True):  # Ensure SNAP is not set
        assert get_rtl_433_path() == "rtl_433"


def test_get_rtl_433_path_snap():
    """Test that get_rtl_433_path returns the correct Snap path when SNAP is set."""
    with patch.dict(os.environ, {"SNAP": "/snap/rtl433"}):
        assert get_rtl_433_path() == "/snap/rtl433/usr/bin/rtl_433"


@patch("subprocess.Popen")
def test_start_rtl_433(mock_popen):
    """Test that start_rtl_433 calls subprocess.Popen with the correct arguments."""
    mock_process = MagicMock()
    mock_process.pid = 12345  # Fake process ID
    mock_popen.return_value = mock_process

    device = 0
    frequency = 433920000
    decoders = [203, 204]

    process = start_rtl_433(
        MagicMock(),
        simulate=False,
        device=device,
        frequency=frequency,
        decoders=decoders,
    )

    # Ensure Popen was called with the expected arguments
    mock_popen.assert_called_once_with(
        [
            "rtl_433",
            "-d",
            "0",
            "-f",
            "433920000",
            "-F",
            "json",
            "-M",
            "protocol",
            "-R",
            "203",
            "-R",
            "204",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    assert process == mock_process  # Ensure the returned process is the mock one


@patch("subprocess.Popen")
def test_start_rtl_433_simulate(mock_popen):
    """Test that start_rtl_433 returns None in simulate mode."""
    process = start_rtl_433(
        MagicMock(), simulate=True, device=0, frequency=433920000, decoders=[]
    )

    mock_popen.assert_not_called()  # Ensure Popen was not called in simulate mode
    assert process is None


@pytest.fixture
def mock_plugin(rtl_433_config):
    """Creates a mock plugin instance with a fake db_write method."""
    config = cfg.from_yaml(rtl_433_config)
    plugin_mock = MagicMock()
    plugin_mock.db_write = MagicMock()
    plugin_mock.status = {"Devices Seen": {}}
    plugin_mock.config = config
    return plugin_mock


def test_process_json_valid(mock_plugin):
    """Test that process_json correctly parses and maps valid JSON data."""
    json_data = json.dumps(
        {
            "protocol": 203,
            "id": 12345,
            "pressure_kPa": 250,
            "temperature_C": 30,
            "battery_V": 2.5,
        }
    )

    process_json(json_data, mock_plugin)

    # Ensure database writes were triggered correctly
    mock_plugin.db_write.assert_any_call(
        "TIREP1", pytest.approx(250 * 0.145032632, 0.1)
    )  # PSI conversion
    mock_plugin.db_write.assert_any_call(
        "TIRET1", (30 - 40)
    )  # Temperature offset applied
    mock_plugin.db_write.assert_any_call(
        "TIREB1", 1
    )  # Battery voltage > 2.0 should set to 1 (OK)


def test_process_json_invalid_json(mock_plugin):
    """Test that process_json handles invalid JSON gracefully."""
    invalid_json = "{invalid_json: true}"  # This is not valid JSON

    process_json(invalid_json, mock_plugin)

    # Ensure db_write was never called since JSON was invalid
    mock_plugin.db_write.assert_not_called()


def test_process_json_missing_keys(mock_plugin):
    """Test that process_json does not fail when keys are missing."""
    partial_json = json.dumps(
        {
            "id": 12345,  # Missing "pressure_kPa", "temperature_C", "battery_V"
        }
    )

    process_json(partial_json, mock_plugin)

    # Ensure db_write was not called since no valid data was present
    mock_plugin.db_write.assert_not_called()
