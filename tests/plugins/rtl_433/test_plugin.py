import pytest
import fixgw.plugins.rtl_433
from collections import namedtuple
import yaml
import time
import json

def test_plugin_startup(plugin):
    """Test that the plugin starts correctly and assigns a PID."""
    status = plugin.pl.get_status()
    #print(plugin.pl.get_status())
    assert status["rtl_433 pid"] == 99999 #is not None, "rtl_433 process did not start"
    assert status["rtl_433 starts"] == 1

def test_start_rtl_called_correctly(plugin,rtl_433_config):
    """Verify that start_rtl_433 is called with correct parameters."""

    # Verify start_rtl_433 was called with expected params
    expected_device = plugin.config["rtl_device"]
    expected_frequency = plugin.config["frequency"]
    expected_decoders = [sensor["decoder"] for sensor in plugin.config["sensors"]]


    plugin.mock_process.assert_called_once_with(
        simulate=False,
        device=expected_device,
        frequency=expected_frequency,
        decoders=expected_decoders
    )


def test_data_processing(plugin, database):
    """Simulate rtl_433 JSON input and verify correct fixid values are written to the database."""
    plugin.rtl_queue.put(json.dumps({
        "id": 12345,
        "pressure_kPa": 150,
        "temperature_C": 30,
        "battery_V": 2.5
    }) + "\n")

    # Simulate processing JSON
    #plugin.mock_process.process_json(json_data, plugin.pl)
    #print(f"#1: {plugin.pl.get_status()}")
    time.sleep(0.001)
    #print(f"#2: {plugin.pl.get_status()} pressure: {database.read('TIRE_PRESSURE1')}")
    # Verify database updates
    assert database.read("TIRE_PRESSURE1")[0] == pytest.approx(150 * 0.145032632, 0.1)
    assert database.read("TIRE_TEMP1")[0] == (30 - 40)  # Temperature offset applied
    assert database.read("TIRE_BATOK1")[0] == 1  # Battery voltage > 2.0 should set to 1 (OK)

def test_plugin_shutdown(plugin):
    """Ensure that rtl_433 is properly terminated on shutdown."""
    plugin.pl.stop()
    time.sleep(0.1)  # Give time for shutdown
    assert plugin.pl.status["rtl_433 pid"] is None, "rtl_433 process did not terminate"


