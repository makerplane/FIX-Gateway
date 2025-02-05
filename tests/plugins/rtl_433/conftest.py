import pytest
import fixgw.plugins.rtl_433
from collections import namedtuple
import yaml
import time
from fixgw import cfg
from unittest.mock import patch, MagicMock
import json
import select
import queue
import threading


@pytest.fixture
def rtl_433_config():
    return """
    load: yes
    module: fixgw.plugins.rtl_433
    frequency: 433920000
    rtl_device: 0
    #simulate: true
    sensors:
      - sensor_id: 12345   # TPMS ID for front wheel
        decoder: 203  # The decoder needed to capture this data
        mappings:
          TIRE_PRESSURE1:
            source: "pressure_kPa"
            scale: 0.145032632
            round: 1
            type: "float"
          TIRE_TEMP1:
            source: "temperature_C"
            offset: -40
            round: 0
            type: "float"
          TIRE_BATOK1:
            source: "battery_V"
            threshold: 2.0  # Battery OK if voltage > 2.0 (1 = OK, 0 = Low)
            type: "bool"
"""


Objects = namedtuple(
    "Objects",
    ["pl", "config", "rtl_queue", "mock_popen", "fail_event"],
)


@pytest.fixture
def plugin(rtl_433_config, database):
    config, config_meta = cfg.from_yaml(rtl_433_config, metadata=True)
    # Mock the start_rtl_433 function
    with patch("subprocess.Popen") as mock_popen, patch("select.select") as mock_select:
        # Create a mock process
        mock_process = MagicMock()
        mock_process.pid = 99999  # Fake PID

        # Queue to control when lines are available
        rtl_queue = queue.Queue()

        # Event flag to trigger process failure from a test
        fail_event = threading.Event()

        # Make stdout.readline() read from the queue
        def fake_readline():
            try:
                return rtl_queue.get(timeout=1)  # Blocks if empty
            except queue.Empty:
                return ""  # Simulates no data

        mock_process.stdout.readline = MagicMock(side_effect=fake_readline)

        # Mock fileno() to return a valid descriptor
        mock_process.stdout.fileno = MagicMock(return_value=1)

        # Control select.select() to only indicate readiness when data is available
        def fake_select(rlist, _, __, timeout):
            if not rtl_queue.empty():
                return (rlist, [], [])  # Indicate data is ready
            return ([], [], [])  # No data available

        mock_select.side_effect = fake_select

        # `poll()` returns None (running) until test sets fail_event, then returns 1 (failed)
        def fake_poll():
            return 1 if fail_event.is_set() else None

        mock_process.poll.side_effect = fake_poll

        # Make subprocess.Popen return the mock process
        mock_popen.return_value = mock_process

        pl = fixgw.plugins.rtl_433.Plugin("rtl_433", config, config_meta)
        pl.run()
        time.sleep(0.1)  # Allow the plugin time to initialize

        yield Objects(
            pl=pl,
            config=config,
            rtl_queue=rtl_queue,
            mock_popen=mock_popen,
            fail_event=fail_event,
        )

        pl.stop()
