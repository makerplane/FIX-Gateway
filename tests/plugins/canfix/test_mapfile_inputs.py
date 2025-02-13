import pytest
import can
import time
from unittest.mock import MagicMock, patch
from fixgw import cfg
import canfix
import re
import fixgw.plugins.canfix


def button_data(data_type, data_code, index, button_bits, canid, nodeid, ns):
    bytes_array = []
    for x in range(5):
        bytes_array.append(button_bits[8 * x : 8 * (x + 1)])  # noqa: E203
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


def test_switch_inputs(plugin,database):
    msg = can.Message(arbitration_id=776, is_extended_id=False)
    # Set TSBTN112 True
    msg.data = bytearray(b"\x91\x00\x00\x01\x00\x00\x00\x00")
    plugin.bus.send(msg)
    time.sleep(0.03)
    assert database.read("TSBTN112")[0] is True
    # Set TSBTN112 False and TBTN212 True
    msg.data = bytearray(b"\x91\x00\x00\x02\x00\x00\x00\x00")
    plugin.bus.send(msg)
    time.sleep(0.03)
    assert database.read("TSBTN112")[0] is False
    assert database.read("TSBTN212")[0] is True
    assert database.read("TSBTN124")[0] is False
    # Set TSBTN124, a Toggle button, to True
    # All other buttons are False
    msg.data = bytearray(b"\x91\x00\x00\x00\x01\x00\x00\x00")
    plugin.bus.send(msg)
    time.sleep(0.03)
    # TSBTN124 wss toggeled False to True
    assert database.read("TSBTN124")[0] is True
    # Set all buttons False
    msg.data = bytearray(b"\x91\x00\x00\x00\x00\x00\x00\x00")
    plugin.bus.send(msg)
    time.sleep(0.03)
    # Sending false on a toggle button does not change its state
    assert database.read("TSBTN124")[0] is True
    # Set TSBTN124 to True
    msg.data = bytearray(b"\x91\x00\x00\x00\x01\x00\x00\x00")
    plugin.bus.send(msg)
    time.sleep(0.03)
    # Button toggled from True to False
    assert database.read("TSBTN124")[0] is False
    # Set all buttons False
    msg.data = bytearray(b"\x91\x00\x00\x00\x00\x00\x00\x00")
    plugin.bus.send(msg)
    time.sleep(0.03)
    # Sending false for toggle does not change state
    assert database.read("TSBTN124")[0] is False
    status = plugin.pl.get_status()
    assert status["Received Frames"] == 6
    assert status["Ignored Frames"] == 0
    assert status["Invalid Frames"] == 0
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


def test_nodespecific_switch_inputs(plugin,database):
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
    assert database.read("MAVADJ")[0] is True
    assert database.read("MAVWPVALID")[0] is True
    assert database.read("MAVREQADJ")[0] is False
    assert database.read("MAVREQAUTOTUNE")[0] is False

    # Reset all buttons to False
    button_bits = [False] * 40
    msg = can.Message(arbitration_id=0x6E0 + nodeid, is_extended_id=False)
    # Set the message data
    msg.data = button_data("BYTE[5]", code, index, button_bits, canid, nodeid, True)
    plugin.bus.send(msg)
    time.sleep(0.03)
    assert database.read("MAVADJ")[0] is False
    assert database.read("MAVWPVALID")[0] is False
    assert database.read("MAVREQADJ")[0] is False
    assert database.read("MAVREQAUTOTUNE")[0] is False
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


def test_bad_parse(plugin,database):
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


def test_mapfile_inputs_canid_too_low(bad_mapfile_config_data,database):
    with pytest.raises(ValueError) as excinfo:
        cc,cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_inputs_canid_low.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "canid must be >= to 256 (0x100) on line 70, column 14 in file 'tests/config/canfix/map_bad_inputs_canid_low.yaml'"
    )


def test_mapfile_inputs_canid_too_high(bad_mapfile_config_data,database):
    with pytest.raises(ValueError) as excinfo:
        cc,cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_inputs_canid_high.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "canid must be <= to 2015 (0x7df) on line 81, column 14 in file 'tests/config/canfix/map_bad_inputs_canid_high.yaml'"  # noqa: E501
    )


def test_mapfile_inputs_canid_missing(bad_mapfile_config_data,database):
    with pytest.raises(ValueError) as excinfo:
        cc,cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_inputs_canid_missing.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "Key 'canid' is missing on line 65, column 5 in file 'tests/config/canfix/map_bad_inputs_canid_missing.yaml'"
    )


def test_mapfile_inputs_not_dict(bad_mapfile_config_data,database):
    with pytest.raises(ValueError) as excinfo:
        cc, cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_inputs_not_dict.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "Inputs should be dictionaries on line 71, column 5 in file 'tests/config/canfix/map_bad_inputs_not_dict.yaml'"
    )

def test_mapfile_inputs_nodespecific_not_bool(bad_mapfile_config_data,database):
    with pytest.raises(ValueError) as excinfo:
        cc, cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_inputs_nodespecific_not_bool.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "nodespecific should be true or false without quotes on line 42, column 73 in file 'tests/config/canfix/map_bad_inputs_nodespecific_not_bool.yaml'"  # noqa: E501
    )


def test_mapfile_inputs_index_high(bad_mapfile_config_data,database):
    with pytest.raises(ValueError) as excinfo:
        cc, cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_inputs_index_high.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "Index should be less than 256 and greater than or equall to 0 on line 51, column 28 in file 'tests/config/canfix/map_bad_inputs_index_high.yaml'"  # noqa: E501
    )


def test_mapfile_inputs_index_low(bad_mapfile_config_data,database):
    with pytest.raises(ValueError) as excinfo:
        cc, cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_inputs_index_low.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "Index should be less than 256 and greater than or equall to 0 on line 69, column 28 in file 'tests/config/canfix/map_bad_inputs_index_low.yaml'"  # noqa: E501
    )


def test_mapfile_inputs_index_missing(bad_mapfile_config_data,database):
    with pytest.raises(ValueError) as excinfo:
        cc, cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_inputs_index_missing.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "Key 'index' is missing on line 50, column 5 in file 'tests/config/canfix/map_bad_inputs_index_missing.yaml'"
    )


def test_mapfile_inputs_fixid_missing(bad_mapfile_config_data,database):
    with pytest.raises(ValueError) as excinfo:
        cc, cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_inputs_fixid_missing.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "Key 'fixid' is missing on line 47, column 5 in file 'tests/config/canfix/map_bad_inputs_fixid_missing.yaml'"
    )


def test_mapfile_inputs_fixid_invalid(bad_mapfile_config_data,database):
    with pytest.raises(ValueError) as excinfo:
        cc, cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_inputs_fixid_invalid.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "fixid 'alt' is not a valid fixid on line 38, column 38 in file 'tests/config/canfix/map_bad_inputs_fixid_invalid.yaml'"  # noqa: E501
    )


def test_mapfile_inputs_fixid_invalid_but_allowed(bad_mapfile_config_data,database):
    try:
        cc, cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_bad_inputs_fixid_invalid_but_allowed.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()
        #time.sleep(0.03)

    # Verify no exception
    except Exception as e:
        pytest.fail(
            f"Using 'tests/config/canfix/map_bad_inputs_fixid_invalid_but_allowed.yaml' should not have caused exception: {e}"
        )



def test_mapfile_ignore_fixid_missing_is_invalid(bad_mapfile_config_data,database):
    with pytest.raises(ValueError) as excinfo:
        cc, cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_ignore_fixid_missing_is_invalid.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "ignore_fixid_missing must be true or false on line 8, column 23 in file 'tests/config/canfix/map_ignore_fixid_missing_is_invalid.yaml'"  # noqa: E501
    )


def test_mapfile_ignore_fixid_missing_is_missing(bad_mapfile_config_data,database):
    try:
        cc, cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_ignore_fixid_missing_is_missing.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        time.sleep(0.1)
        pl.stop()
    # Verify no exception
    except Exception as e:
        pytest.fail(
            f"Using 'tests/config/canfix/map_bad_inputs_fixid_invalid_but_allowed.yaml' should not have caused exception: {e}"
        )


def test_mapfile_ignore_fixid_missing_is_invalid(bad_mapfile_config_data,database):
    with pytest.raises(ValueError) as excinfo:
        cc, cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_ignore_fixid_missing_is_invalid.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "ignore_fixid_missing must be true or false on line 8, column 23 in file 'tests/config/canfix/map_ignore_fixid_missing_is_invalid.yaml'"  # noqa: E501
    )

def test_mapfile_no_meta_replacements(bad_mapfile_config_data,database):
    with pytest.raises(ValueError) as excinfo:
        cc, cc_meta = cfg.from_yaml(
            re.sub(
                "missing_map_file.yaml",
                "tests/config/canfix/map_no_meta_replacements.yaml",
                bad_mapfile_config_data,
            ), metadata=True
        )
        pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
        pl.start()
        pl.stop()

    # Verify the exception message
    assert (
        str(excinfo.value)
        == "The mapfile 'tests/config/canfix/map_no_meta_replacements.yaml' must provide a valid 'meta replacements' section"  # noqa: E501
    )


