#  Copyright (c) 2018 Phil Birkelbach
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import time
import yaml
import random
import re
import can
import canfix
from fixgw import cfg

import fixgw.database as database
import fixgw.quorum as quorum
import pytest
import fixgw.plugins.canfix
from collections import namedtuple
from unittest.mock import MagicMock, patch
import logging
import warnings

# canfix needs updated to support quorum so we will monkey patch it for now
# Pull to fix canfix: https://github.com/birkelbach/python-canfix/pull/13
# Request to add this to the canfix specification: https://github.com/makerplane/canfix-spec/issues/4
canfix.NodeStatus.knownTypes = (
    ("Status", "WORD", 1),
    ("Unit Temperature", "INT", 0.1),
    ("Supply Voltage", "INT", 0.1),
    ("CAN Transmit Frame Count", "UDINT", 1),
    ("CAN Receive Frame Count", "UDINT", 1),
    ("CAN Transmit Error Count", "UDINT", 1),
    ("CAN Transmit Error Count", "UDINT", 1),
    ("CAN Receive Overrun Count", "UDINT", 1),
    ("Serial Number", "UDINT", 1),
    ("Quorum", "UINT", 1),
)


config = """
    load: yes
    module: fixgw.plugins.canfix
    # See the python-can documentation for the meaning of these options
    interface: virtual
    channel: tcan0

    # Use the actual current mapfile
    mapfile: 'tests/config/canfix/map.yaml'
    # The following is our Node Identification Information
    # See the CAN-FIX Protocol Specification for more information
    node: 145     # CAN-FIX Node ID
    device: 145   # CAN-FIX Device Type
    revision: 0   # Software Revision Number
    model: 0      # Model Number
    CONFIGPATH: ''
"""

bad_mapfile_config = """
    load: yes
    module: fixgw.plugins.canfix
    # See the python-can documentation for the meaning of these options
    interface: virtual
    channel: tcan0

    # Use the actual current mapfile
    mapfile: 'missing_map_file.yaml'
    # The following is our Node Identification Information
    # See the CAN-FIX Protocol Specification for more information
    node: 145     # CAN-FIX Node ID
    device: 145   # CAN-FIX Device Type
    revision: 0   # Software Revision Number
    model: 0      # Model Number
    CONFIGPATH: ''
"""


# This is a list of the parameters that we are testing.  It is a list of tuples
# that contain (FIXID, CANID, DataString, Value, Test tolerance)
ptests = [
    ("PITCH", 0x180, "FF0000D8DC", -90.0, 0.0),
    ("PITCH", 0x180, "FF00002823", 90.0, 0.0),
    ("PITCH", 0x180, "FF00000000", 0.0, 0.0),
    ("ROLL", 0x181, "FF0000B0B9", -180.0, 0.0),
    ("ROLL", 0x181, "FF00005046", 180.0, 0.0),
    ("ROLL", 0x181, "FF00000000", 0.0, 0.0),
    ("IAS", 0x183, "FF00000000", 0.0, 0.0),
    ("IAS", 0x183, "FF0000E803", 100.0, 0.0),
    ("IAS", 0x183, "FF0000E803", 100.0, 0.0),
    ("IAS", 0x183, "FF00000F27", 999.9, 0.01),
    ("IAS.Min", 0x183, "FF00100000", 0.0, 0.01),
    ("IAS.Max", 0x183, "FF0020D007", 200.0, 0.01),
    ("IAS.V1", 0x183, "FF00309001", 40.0, 0.01),
    ("IAS.V2", 0x183, "FF00406202", 61.0, 0.01),
    ("IAS.Vne", 0x183, "FF0050DC02", 73.2, 0.01),
    ("IAS.Vfe", 0x183, "FF0060EE02", 75.0, 0.01),
    ("IAS.Vmc", 0x183, "FF00702003", 80.0, 0.01),
    ("IAS.Va", 0x183, "FF00802B03", 81.1, 0.01),
    ("IAS.Vno", 0x183, "FF00908603", 90.2, 0.01),
    ("IAS.Vs", 0x183, "FF00A0A501", 42.1, 0.01),
    ("IAS.Vs0", 0x183, "FF00B0C401", 45.2, 0.01),
    ("IAS.Vx", 0x183, "FF00E06203", 86.6, 0.01),
    ("IAS.Vy", 0x183, "FF00F06D03", 87.7, 0.01),
    ("ALT", 0x184, "FF000018FCFFFF", -1000.0, 0.01),
    ("ALT", 0x184, "FF000000000000", 0.0, 0.01),
    ("ALT", 0x184, "FF0000E8030000", 1000.0, 0.01),
    ("ALT", 0x184, "FF0000D0070000", 2000.0, 0.01),
    ("ALT", 0x184, "FF000010270000", 10000.0, 0.01),
    ("ALT", 0x184, "FF000060EA0000", 60000.0, 0.01),
    ("HEAD", 0x185, "FF00000000", 0.0, 0.01),
    ("HEAD", 0x185, "FF00000807", 180.0, 0.01),
    ("HEAD", 0x185, "FF00000F0E", 359.9, 0.01),
    ("HEAD", 0x185, "FF0000100E", 359.9, 0.01),  # Write 360.0 get back 359.9
    ("VS", 0x186, "FF0000D08A", -30000, 0.01),
    ("VS", 0x186, "FF00000000", 0, 0.01),
    ("VS", 0x186, "FF00003075", 30000, 0.01),
    ("VS.Min", 0x186, "FF0010F0D8", -10000, 0.01),
    ("VS.Max", 0x186, "FF00201027", 10000, 0.01),
    ("TACH1", 0x200, "FF00000000", 0, 0.01),
    ("TACH1", 0x200, "FF0000E803", 1000, 0.01),
    ("TACH1", 0x200, "FF00005A0A", 2650, 0.01),
    ("PROP1", 0x202, "FF00000000", 0, 0.01),
    ("PROP1", 0x202, "FF0000E803", 1000, 0.01),
    ("PROP1", 0x202, "FF00005A0A", 2650, 0.01),
    ("MAP1", 0x21E, "FF00000000", 0.0, 0.001),
    ("MAP1", 0x21E, "FF0000C409", 25.0, 0.001),
    ("MAP1.Min", 0x21E, "FF00100000", 0.0, 0.001),
    ("MAP1.Max", 0x21E, "FF0020B80B", 30.0, 0.001),
    ("OILP1", 0x220, "FF00000000", 0.0, 0.001),
    ("OILP1", 0x220, "FF0000A911", 45.21, 0.001),
    ("OILP1", 0x220, "FF00005125", 95.53, 0.001),
    ("OILP1.Min", 0x220, "FF00100000", 0.0, 0.001),
    ("OILP1.Max", 0x220, "FF00201027", 100.0, 0.001),
    ("OILP1.lowWarn", 0x220, "FF0040A00F", 40.0, 0.001),
    ("OILP1.lowAlarm", 0x220, "FF0050AC0D", 35.0, 0.001),
    ("OILP1.highWarn", 0x220, "FF0060401F", 80.0, 0.001),
    ("OILP1.highAlarm", 0x220, "FF00701C25", 95.0, 0.001),
    #          ("OILT1", 0x220, "FF0000", 0.0, 0.001),
]

qtests = [
    ("QVOTE1", 1, 1),
    ("QVOTE2", 2, 2),
    ("QVOTE3", 3, 3),
]


def string2data(s):
    b = bytearray()
    for x in range(0, len(s), 2):
        b.append(int(s[x : x + 2], 16))  # noqa: E203
    return b


def button_data(data_type, data_code, index, button_bits, canid, nodeid, ns):
    bytes_array = []
    for x in range(5):
        bytes_array.append(button_bits[8 * x : 8 * (x + 1)])
    valueData = canfix.utils.setValue(data_type, bytes_array)
    data = bytearray([])
    if ns:
        data.append(data_code)  # Control Code 12-19 index 1-8
        x = (index % 32) << 11 | canid
        data.append(x % 256)
        data.append(x >> 8)
    else:
        data.append(nodeid)
        data.append(index // 32)
        data.append(0x00)
    data.extend(valueData)
    return data


Objects = namedtuple(
    "Objects",
    ["bus", "pl", "interface", "channel", "node", "device", "revision", "model"],
)


@pytest.fixture
def plugin():
    # Use the default database
    database.init("src/fixgw/config/database.yaml")

    cc = yaml.safe_load(config)
    pl = fixgw.plugins.canfix.Plugin("canfix", cc)
    pl.start()
    can_bus = can.Bus(cc["channel"], interface=cc["interface"])
    time.sleep(0.1)  # Give plugin a chance to get started

    yield Objects(
        bus=can_bus,
        interface=cc["interface"],
        channel=cc["channel"],
        node=cc["node"],
        device=cc["device"],
        revision=cc["revision"],
        model=cc["model"],
        pl=pl,
    )
    pl.shutdown()
    can_bus.shutdown()
    quorum.enabled = False
    quorum.nodeid = None


def test_missing_mapfile():
    with pytest.raises(Exception):
        bad_cc = yaml.safe_load(bad_mapfile_config)
        bad_pl = fixgw.plugins.canfix.Plugin("canfix", bad_cc)
        # bad_pl.start()


def test_parameter_writes(plugin):
    for param in ptests:
        msg = can.Message(is_extended_id=False, arbitration_id=param[1])
        msg.data = string2data(param[2])
        plugin.bus.send(msg)
        time.sleep(0.03)
        x = database.read(param[0])
        if "." in param[0]:
            val = x
        else:
            val = x[0]
        assert abs(val - param[3]) <= param[4]

    status = plugin.pl.get_status()
    assert status["Received Frames"] == len(ptests)
    assert status["Ignored Frames"] == 0
    assert status["Invalid Frames"] == 0
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


def test_unowned_outputs(plugin):
    database.write("BARO", 30.04)
    msg = plugin.bus.recv(1.0)
    assert msg.arbitration_id == plugin.node + 1760
    assert msg.data == bytearray([12, 0x90, 0x01, 0x58, 0x75])
    status = plugin.pl.get_status()
    assert status["Received Frames"] == 0
    assert status["Ignored Frames"] == 0
    assert status["Invalid Frames"] == 0
    assert status["Sent Frames"] == 1
    assert status["Send Error Count"] == 0


def test_all_frame_ids(plugin):
    """Loop through every CAN ID and every length of data with random data"""
    random.seed(14)  # We want deterministic input for testing
    # Not all ids are usable this causes a warning.
    # Need to only use known ids accroding to canfix library
    # Check against venv/lib/python3.10/site-packages/canfix/protocol.py parameters[pid]
    import canfix.protocol

    count = 0
    for id in range(2048):
        if id in canfix.protocol.parameters:
            for dsize in range(9):
                msg = can.Message(is_extended_id=False, arbitration_id=id)
                for x in range(dsize):
                    msg.data.append(random.randrange(256))
                msg.dlc = dsize
                plugin.bus.send(msg)
                count += 1
    time.sleep(0.03)
    status = plugin.pl.get_status()
    assert status["Received Frames"] == count
    assert status["Ignored Frames"] == 3294
    assert status["Invalid Frames"] == 10
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


# TODO Add asserts above


def test_ignore_quorum_mssages_when_diabled(plugin):
    for param in qtests:
        p = canfix.NodeStatus()
        p.sendNode = param[1]
        p.parameter = 0x09
        p.value = param[2]
        plugin.bus.send(p.msg)
        time.sleep(0.03)
        x = database.read(param[0])
        # Nothing should change since we are not accepting the messages
        assert x[0] == 0
    status = plugin.pl.get_status()
    # All received frames should be ignored
    assert status["Received Frames"] == len(qtests)
    assert status["Ignored Frames"] == len(qtests)
    assert status["Invalid Frames"] == 0
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


def test_accept_quorum_mssages_when_enabled(plugin):
    quorum.enabled = True
    quorum.nodeid = 1
    p = canfix.NodeStatus()
    # keep track of the frames we should ignore
    ignoreframes = 0
    for param in qtests:
        if param[1] == quorum.nodeid:
            ignoreframes += 1
        p.sendNode = param[1]
        p.parameter = 0x09
        p.value = param[2]
        plugin.bus.send(p.msg)
        time.sleep(0.03)
        x = database.read(param[0])
        if param[2] == 1:
            assert x[0] == 0
        else:
            assert x[0] == param[2]
    status = plugin.pl.get_status()
    assert status["Received Frames"] == len(qtests)
    assert status["Ignored Frames"] == ignoreframes
    assert status["Invalid Frames"] == 0
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


def test_reject_invalid_quorum_mssages_when_enabled(plugin, caplog):
    quorum.enabled = True
    quorum.nodeid = 1
    p = canfix.NodeStatus()
    p.parameter = 0x09
    # keep track of the frames we should ignore
    sentframes = 0
    invalidframes = 0
    # Test invalid value 101
    p.sendNode = 5
    p.value = 101
    plugin.bus.send(p.msg)
    time.sleep(0.03)
    invalidframes += 1
    sentframes += 1
    assert database.read("QVOTE5")[0] == 0
    # Test invalid value 0
    p.value = 0
    plugin.bus.send(p.msg)
    time.sleep(0.03)
    invalidframes += 1
    sentframes += 1
    assert database.read("QVOTE5")[0] == 0

    # Test DB not configured for 6 nodes
    p.sendNode = 6
    p.value = 6
    invalidframes += 1
    sentframes += 1
    with caplog.at_level(logging.WARNING):
        plugin.bus.send(p.msg)
        time.sleep(0.03)
        assert "Received a vote for QVOTE6 but this fixid does not exist" in caplog.text
    status = plugin.pl.get_status()
    assert status["Received Frames"] == sentframes
    assert status["Ignored Frames"] == 0
    assert status["Invalid Frames"] == invalidframes
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


def test_switch_inputs(plugin):
    msg = can.Message(arbitration_id=776, is_extended_id=False)
    # Set TSBTN112 True
    msg.data = bytearray(b"\x91\x00\x00\x01\x00\x00\x00\x00")
    plugin.bus.send(msg)
    time.sleep(0.03)
    assert database.read("TSBTN112")[0] == True
    # Set TSBTN112 False and TBTN212 True
    msg.data = bytearray(b"\x91\x00\x00\x02\x00\x00\x00\x00")
    plugin.bus.send(msg)
    time.sleep(0.03)
    assert database.read("TSBTN112")[0] == False
    assert database.read("TSBTN212")[0] == True
    assert database.read("TSBTN124")[0] == False
    # Set TSBTN124, a Toggle button, to True
    # All other buttons are False
    msg.data = bytearray(b"\x91\x00\x00\x00\x01\x00\x00\x00")
    plugin.bus.send(msg)
    time.sleep(0.03)
    # TSBTN124 wss toggeled False to True
    assert database.read("TSBTN124")[0] == True
    # Set all buttons False
    msg.data = bytearray(b"\x91\x00\x00\x00\x00\x00\x00\x00")
    plugin.bus.send(msg)
    time.sleep(0.03)
    # Sending false on a toggle button does not change its state
    assert database.read("TSBTN124")[0] == True
    # Set TSBTN124 to True
    msg.data = bytearray(b"\x91\x00\x00\x00\x01\x00\x00\x00")
    plugin.bus.send(msg)
    time.sleep(0.03)
    # Button toggled from True to False
    assert database.read("TSBTN124")[0] == False
    # Set all buttons False
    msg.data = bytearray(b"\x91\x00\x00\x00\x00\x00\x00\x00")
    plugin.bus.send(msg)
    time.sleep(0.03)
    # Sending false for toggle does not change state
    assert database.read("TSBTN124")[0] == False
    status = plugin.pl.get_status()
    assert status["Received Frames"] == 6
    assert status["Ignored Frames"] == 0
    assert status["Invalid Frames"] == 0
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


def test_nodespecific_switch_inputs(plugin):
    # msg = can.Message(arbitration_id=1905, is_extended_id=False)
    # Set MAVADJ True
    # database.write("MAVADJ", False)
    index = 0
    canid = 0x309
    nodeid = 0x91
    button_bits = [False] * 40
    # Set first button true
    button_bits[0] = True
    # Set 7th button True
    button_bits[6] = True
    code = (index // 32) + 0x0C
    # Setup the can message as node specific
    msg = can.Message(arbitration_id=0x6E0 + nodeid, is_extended_id=False)
    # Set the message data
    msg.data = button_data("BYTE[5]", code, index, button_bits, canid, nodeid, True)
    plugin.bus.send(msg)
    time.sleep(0.03)
    assert database.read("MAVADJ")[0] == True
    assert database.read("MAVWPVALID")[0] == True
    assert database.read("MAVREQADJ")[0] == False
    assert database.read("MAVREQAUTOTUNE")[0] == False

    # Reset all buttons to False
    button_bits = [False] * 40
    msg = can.Message(arbitration_id=0x6E0 + nodeid, is_extended_id=False)
    # Set the message data
    msg.data = button_data("BYTE[5]", code, index, button_bits, canid, nodeid, True)
    plugin.bus.send(msg)
    time.sleep(0.03)
    assert database.read("MAVADJ")[0] == False
    assert database.read("MAVWPVALID")[0] == False
    assert database.read("MAVREQADJ")[0] == False
    assert database.read("MAVREQAUTOTUNE")[0] == False
    status = plugin.pl.get_status()
    assert status["Received Frames"] == 2
    assert status["Ignored Frames"] == 0
    assert status["Invalid Frames"] == 0
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


def test_nodespecific_switch_input_that_we_do_not_want(plugin):
    index = 0
    canid = 0x30A
    nodeid = 0x91
    button_bits = [False] * 40
    # Set first button true
    button_bits[0] = True
    # Set 7th button True
    button_bits[6] = True
    code = (index // 32) + 0x0C
    msg = can.Message(arbitration_id=0x6E0 + nodeid, is_extended_id=False)
    with patch("canfix.parseMessage") as mock_parse:
        # send valid message we do not want
        mock_parse = MagicMock()
        msg.data = button_data("BYTE[5]", code, index, button_bits, canid, nodeid, True)
        plugin.bus.send(msg)
        time.sleep(0.03)
        # send invalid message to test exception branch
        mock_parse = MagicMock()
        msg.data = button_data("BYTE[5]", code, 9, button_bits, canid, nodeid, True)
        plugin.bus.send(msg)
        time.sleep(0.03)
    # Since we do not need either of these messages they are never parsed
    mock_parse.assert_not_called()
    status = plugin.pl.get_status()
    assert status["Received Frames"] == 2
    assert status["Ignored Frames"] == 1
    assert status["Invalid Frames"] == 1
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


def test_bad_parse(plugin):
    # Bad CAN data can cause exceptions if the code does not
    # Ensure the data is valid before using it
    # I found, and fixed, such a bug when writing a test
    # This test ensures we do not have regressions
    try:
        # Send Parameter set for VS
        cur_vs = database.read("VS")[0]
        msg = can.Message(arbitration_id=0x186, is_extended_id=False)
        # Incomplete message sent
        msg.data = bytearray(b"\x00\x00\x00\x00")
        plugin.bus.send(msg)
        time.sleep(0.3)
    except Exception as e:
        pytest.fail(f"An unexpected exception occurred: {e}")
    # Data should not change if bad data is sent
    assert cur_vs == database.read("VS")[0]
    status = plugin.pl.get_status()
    assert status["Received Frames"] == 1
    assert status["Ignored Frames"] == 0
    assert status["Invalid Frames"] == 1
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


def test_mapfile_input_canid_too_low():
    with pytest.raises(ValueError) as excinfo:
        database.init("src/fixgw/config/database.yaml")
        cc = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_input_canid_low.yaml",
                bad_mapfile_config,
            )
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc)
        pl.start()
        pl.shutdown()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "canid must be >= to 256 (0x100) on line 34, column 14 in file 'tests/config/canfix/map_bad_input_canid_low.yaml'"
    )


def test_mapfile_input_canid_too_high():
    with pytest.raises(ValueError) as excinfo:
        database.init("src/fixgw/config/database.yaml")
        cc = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_input_canid_high.yaml",
                bad_mapfile_config,
            )
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc)
        pl.start()
        pl.shutdown()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "canid must be <= to 2015 (0x7df) on line 34, column 14 in file 'tests/config/canfix/map_bad_input_canid_high.yaml'"
    )


def test_mapfile_input_canid_missing():
    with pytest.raises(ValueError) as excinfo:
        database.init("src/fixgw/config/database.yaml")
        cc = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_input_canid_missing.yaml",
                bad_mapfile_config,
            )
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc)
        pl.start()
        pl.shutdown()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "Key 'canid' is missing on line 34, column 5 in file 'tests/config/canfix/map_bad_input_canid_missing.yaml'"
    )


def test_mapfile_input_not_dict():
    with pytest.raises(ValueError) as excinfo:
        database.init("src/fixgw/config/database.yaml")
        cc = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_input_not_dict.yaml",
                bad_mapfile_config,
            )
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc)
        pl.start()
        pl.shutdown()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "Inputs should be dictionaries on line 40, column 5 in file 'tests/config/canfix/map_bad_input_not_dict.yaml'"
    )

def test_mapfile_input_nodespecific_not_bool():
    with pytest.raises(ValueError) as excinfo:
        database.init("src/fixgw/config/database.yaml")
        cc = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_input_nodespecific_not_bool.yaml",
                bad_mapfile_config,
            )
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc)
        pl.start()
        pl.shutdown()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "nodespecific should be true or false without quotes on line 34, column 73 in file 'tests/config/canfix/map_bad_input_nodespecific_not_bool.yaml'"
    )


def test_mapfile_input_index_high():
    with pytest.raises(ValueError) as excinfo:
        database.init("src/fixgw/config/database.yaml")
        cc = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_input_index_high.yaml",
                bad_mapfile_config,
            )
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc)
        pl.start()
        pl.shutdown()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "Index should be less than 256 and greater than or equall to 0 on line 29, column 28 in file 'tests/config/canfix/map_bad_input_index_high.yaml'"
    )

def test_mapfile_input_index_low():
    with pytest.raises(ValueError) as excinfo:
        database.init("src/fixgw/config/database.yaml")
        cc = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_input_index_low.yaml",
                bad_mapfile_config,
            )
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc)
        pl.start()
        pl.shutdown()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "Index should be less than 256 and greater than or equall to 0 on line 29, column 28 in file 'tests/config/canfix/map_bad_input_index_low.yaml'"
    )

def test_mapfile_input_index_missing():
    with pytest.raises(ValueError) as excinfo:
        database.init("src/fixgw/config/database.yaml")
        cc = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_input_index_missing.yaml",
                bad_mapfile_config,
            )
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc)
        pl.start()
        pl.shutdown()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "Key 'index' is missing on line 29, column 5 in file 'tests/config/canfix/map_bad_input_index_missing.yaml'"
    )


def test_get_status(plugin):
    status = plugin.pl.get_status()
    assert status["CAN Interface"] == plugin.interface
    assert status["CAN Channel"] == plugin.channel


# We don't really have any of these yet
# def test_owned_outputs():
#     pass

# These aren't implemented yet
# def test_node_identification():
#     pass
#
# def test_node_report():
#     pass
#
# def test_parameter_disable_enable():
#     pass
#
# def test_node_id_set():
#     pass
