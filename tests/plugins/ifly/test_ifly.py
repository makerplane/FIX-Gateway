from unittest.mock import MagicMock

import pytest

import fixgw.plugins.ifly as ifly
from fixgw.plugins.ifly import MainThread, Plugin


class FakeSocket:
    def __init__(self, messages=None):
        self.messages = list(messages or [])
        self.bound = None
        self.owner = None

    def bind(self, address):
        self.bound = address

    def recvfrom(self, size):
        assert size == 8192
        message = self.messages.pop(0)
        if not self.messages and self.owner is not None:
            self.owner.getout = True
        return message, ("127.0.0.1", 2000)


def make_thread(monkeypatch, messages=None, leader=True):
    fake_socket = FakeSocket(messages)
    monkeypatch.setattr(ifly.socket, "socket", MagicMock(return_value=fake_socket))
    parent = MagicMock()
    parent.log = MagicMock()
    parent.quorum.leader = leader
    thread = MainThread(parent)
    fake_socket.owner = thread
    return thread, parent, fake_socket


def test_thread_initializes_udp_socket(monkeypatch, capsys):
    thread, parent, fake_socket = make_thread(monkeypatch)

    assert thread.parent is parent
    assert thread.log is parent.log
    assert fake_socket.bound == ("192.168.1.1", 2000)
    assert "running ifly plugin" in capsys.readouterr().out


def test_run_skips_empty_messages_and_non_leader(monkeypatch):
    thread, parent, _fake_socket = make_thread(
        monkeypatch,
        [b"", b"$GPRMB,ignored"],
        leader=False,
    )

    thread.run()

    parent.db_write.assert_not_called()


def test_run_skips_messages_without_nmea_parse_errors_and_missing_sentence_type(
    monkeypatch,
):
    thread, parent, _fake_socket = make_thread(
        monkeypatch,
        [b"noise only", b"$BAD", b"$NOSENTENCE"],
    )
    parsed_without_type = object()

    def parse(sentence):
        if sentence == "$BAD":
            raise ValueError("bad nmea")
        return parsed_without_type

    monkeypatch.setattr(ifly.pynmea2, "parse", parse)

    thread.run()

    parent.db_write.assert_not_called()


@pytest.mark.parametrize(
    "lat_dir,lon_dir,expected_lat,expected_lon",
    [
        ("N", "E", 40.0, 88.0),
        ("S", "W", -40.0, -88.0),
    ],
)
def test_run_writes_rmb_destination(monkeypatch, lat_dir, lon_dir, expected_lat, expected_lon):
    thread, parent, _fake_socket = make_thread(monkeypatch, [b"prefix $GPRMB,data"])
    msg = MagicMock()
    msg.sentence_type = "RMB"
    msg.dest_lat_dir = lat_dir
    msg.dest_lon_dir = lon_dir
    msg.dest_lat = "4000.000"
    msg.dest_lon = "08800.000"
    msg.dest_waypoint_id = "KOSHARRIVAL"
    monkeypatch.setattr(ifly.pynmea2, "parse", MagicMock(return_value=msg))

    thread.run()

    parent.db_write.assert_any_call("WPLAT", expected_lat)
    parent.db_write.assert_any_call("WPLON", expected_lon)
    parent.db_write.assert_any_call("WPNAME", "KOSHA")


@pytest.mark.parametrize(
    "heading_type,expected",
    [
        ("T", "123.4 True"),
        ("M", "123.4 Mag"),
        ("", "123.4"),
    ],
)
def test_run_writes_apb_heading(monkeypatch, heading_type, expected):
    thread, parent, _fake_socket = make_thread(monkeypatch, [b"$GPAPB,data"])
    msg = MagicMock()
    msg.sentence_type = "APB"
    msg.heading_to_dest = "123.4"
    msg.heading_to_dest_type = heading_type
    monkeypatch.setattr(ifly.pynmea2, "parse", MagicMock(return_value=msg))

    thread.run()

    parent.db_write.assert_called_once_with("WPHEAD", expected)


def test_run_ignores_other_sentence_types_and_marks_not_running(monkeypatch):
    thread, parent, _fake_socket = make_thread(monkeypatch, [b"$GPRMC,data"])
    msg = MagicMock()
    msg.sentence_type = "RMC"
    monkeypatch.setattr(ifly.pynmea2, "parse", MagicMock(return_value=msg))

    thread.run()

    parent.db_write.assert_not_called()
    assert thread.running is False


def test_stop_sets_getout(monkeypatch):
    thread, _parent, _fake_socket = make_thread(monkeypatch)

    thread.stop()

    assert thread.getout is True


def test_plugin_run_stop_and_status(monkeypatch):
    fake_socket = FakeSocket()
    monkeypatch.setattr(ifly.socket, "socket", MagicMock(return_value=fake_socket))
    pl = Plugin("ifly-test", {}, {})
    thread = MagicMock()
    thread.is_alive.return_value = False
    pl.thread = thread

    pl.run()
    thread.start.assert_called_once_with()

    pl.stop()
    thread.stop.assert_called_once_with()
    thread.join.assert_not_called()
    assert pl.get_status() is pl.status


def test_plugin_stop_joins_live_thread(monkeypatch):
    fake_socket = FakeSocket()
    monkeypatch.setattr(ifly.socket, "socket", MagicMock(return_value=fake_socket))
    pl = Plugin("ifly-test", {}, {})
    thread = MagicMock()
    thread.is_alive.side_effect = [True, False]
    pl.thread = thread

    pl.stop()

    thread.join.assert_called_once_with(1.0)


def test_plugin_stop_raises_when_thread_survives_join(monkeypatch):
    fake_socket = FakeSocket()
    monkeypatch.setattr(ifly.socket, "socket", MagicMock(return_value=fake_socket))
    pl = Plugin("ifly-test", {}, {})
    thread = MagicMock()
    thread.is_alive.return_value = True
    pl.thread = thread

    with pytest.raises(ifly.plugin.PluginFail):
        pl.stop()

    thread.join.assert_called_once_with(1.0)
