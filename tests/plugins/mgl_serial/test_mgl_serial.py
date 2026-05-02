import struct
from unittest.mock import MagicMock

import pytest

import fixgw.plugins.mgl_serial as mgl_serial
from fixgw.plugins.mgl_serial import MainThread, Plugin


def make_parent():
    parent = MagicMock()
    parent.config = {"port": "/dev/null", "baud": 9600, "engine_no": 1}
    parent.log = MagicMock()
    return parent


def build_message(type_hi, type_lo, value_hi, value_lo, msg_type=8, end=b"\x03"):
    return struct.pack(
        ">BBBBBBhhhhBB",
        0x02,
        1,
        msg_type,
        10,
        0,
        type_hi,
        value_hi,
        0,
        0,
        0,
        0,
        end[0],
    )


def test_parse_ignores_bad_lengths_and_incomplete_messages():
    parent = make_parent()
    thread = MainThread(parent)

    thread._parse(b"short")
    thread._parse(build_message(1, 0, 10, 0, end=b"\x00"))

    parent.db_write.assert_not_called()
    parent.log.debug.assert_called_once_with("Incomplete message received")


def test_parse_logs_missing_start_but_processes_supported_message():
    parent = make_parent()
    thread = MainThread(parent)
    message = bytearray(build_message(1, 0, 25, 0))
    message[0] = 0

    thread._parse(bytes(message))

    parent.log.debug.assert_called_once_with("Beginning of message was not found")
    parent.db_write.assert_called_once_with("OILP1", 2.5)


def test_parse_rejects_unsupported_message_type():
    parent = make_parent()
    thread = MainThread(parent)

    thread._parse(build_message(1, 0, 10, 0, msg_type=7))

    parent.log.warning.assert_called_once_with("Unsupported message")
    parent.db_write.assert_not_called()


def test_parse_writes_each_supported_channel_type(capsys):
    parent = make_parent()
    thread = MainThread(parent)
    message = struct.pack(
        ">BBBBBBhhhhBB",
        0x02,
        1,
        8,
        10,
        (4 << 4) | 5,
        (2 << 4) | 3,
        321,
        456,
        789,
        654,
        0,
        0x03,
    )

    thread._parse(message)

    parent.db_write.assert_any_call("CURRNT", 32.1)
    parent.db_write.assert_any_call("OILT1", 456)
    parent.db_write.assert_any_call("VOLT", 78.9)
    parent.db_write.assert_any_call("FUELQT", 654)
    assert "CURRNT" in capsys.readouterr().out


def test_parse_writes_blank_key_for_unknown_channel_type():
    parent = make_parent()
    thread = MainThread(parent)
    message = build_message(6, 0, 99, 0)

    thread._parse(message)

    parent.db_write.assert_called_once_with("", 99)


def test_stop_sets_getout():
    parent = make_parent()
    thread = MainThread(parent)

    thread.stop()

    assert thread.getout is True


def test_run_logs_open_failure(monkeypatch):
    parent = make_parent()
    thread = MainThread(parent)

    def serial_factory(*args, **kwargs):
        raise mgl_serial.serial.serialutil.SerialException("no port")

    monkeypatch.setattr(mgl_serial.serial, "Serial", serial_factory)

    thread.run()

    parent.log.error.assert_called_once_with("Could not open port: /dev/null")


def test_run_reads_and_parses_until_stopped(monkeypatch):
    parent = make_parent()
    thread = MainThread(parent)
    message = build_message(1, 0, 42, 0)

    class FakeSerial:
        def read_until(self, marker):
            assert marker == b"\x03"
            thread.getout = True
            return message

    monkeypatch.setattr(mgl_serial.serial, "Serial", MagicMock(return_value=FakeSerial()))

    thread.run()

    parent.db_write.assert_called_once_with("OILP1", 4.2)


def test_run_logs_serial_errors(monkeypatch):
    parent = make_parent()
    thread = MainThread(parent)

    class FakeSerial:
        calls = 0

        def read_until(self, marker):
            self.calls += 1
            if self.calls == 1:
                raise mgl_serial.serial.SerialException("read failed")
            thread.getout = True
            return b"short"

    monkeypatch.setattr(mgl_serial.serial, "Serial", MagicMock(return_value=FakeSerial()))

    thread.run()

    parent.log.error.assert_called_once_with("Serial port error")


def test_plugin_run_stop_and_status():
    plugin = Plugin("mgl-serial-test", {"port": "/dev/null", "baud": 9600, "engine_no": 1}, {})
    thread = MagicMock()
    thread.is_alive.return_value = False
    plugin.thread = thread

    plugin.run()
    thread.start.assert_called_once_with()

    plugin.stop()
    thread.stop.assert_called_once_with()
    thread.join.assert_not_called()
    assert plugin.get_status() is plugin.status


def test_plugin_stop_joins_live_thread():
    plugin = Plugin("mgl-serial-test", {"port": "/dev/null", "baud": 9600, "engine_no": 1}, {})
    thread = MagicMock()
    thread.is_alive.side_effect = [True, False]
    plugin.thread = thread

    plugin.stop()

    thread.join.assert_called_once_with(1.0)


def test_plugin_stop_raises_when_thread_survives_join():
    plugin = Plugin("mgl-serial-test", {"port": "/dev/null", "baud": 9600, "engine_no": 1}, {})
    thread = MagicMock()
    thread.is_alive.return_value = True
    plugin.thread = thread

    with pytest.raises(mgl_serial.plugin.PluginFail):
        plugin.stop()

    thread.join.assert_called_once_with(1.0)
