import struct
from unittest.mock import MagicMock, call, patch

import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.xplane as xplane
from fixgw.plugins.xplane import MainThread, Plugin

@pytest.fixture
def mock_parent():
    mock = MagicMock()
    mock.config = {
        "idx3": "IAS,X,X,TAS,X,X,X,X",
        "idx20": "LAT,LONG,ALT,X,X,X,X,X",
    }
    mock.log = MagicMock()
    mock.db_write = MagicMock()
    mock.db_read = MagicMock(side_effect=lambda key: 123.45 if key == "IAS" else 0.0)
    return mock


@pytest.fixture
def main_thread(mock_parent):
    with patch("socket.socket") as mock_socket:
        mock_socket.return_value.recvfrom = MagicMock(return_value=(b"DATA" + b"\x00" * 40, ("127.0.0.1", 12345)))
        return MainThread(mock_parent)


def test_writedata(mock_parent, main_thread):
    main_thread.writedata(3, [100.0, 0.0, 200.0])
    mock_parent.db_write.assert_has_calls([
        call("IAS", 100.0),
        call("TAS", 200.0),
    ], any_order=True)

    main_thread.writedata(20, [40.7128, -74.0060, 1000.0])
    mock_parent.db_write.assert_has_calls([
        call("LAT", 40.7128),
        call("LONG", -74.0060),
        call("ALT", 1000.0),
    ], any_order=True)

    main_thread.writedata(99, [0.0, 0.0, 0.0])
    mock_parent.log.debug.assert_called_with("Dunno Index:99")


def test_senddata_packs_configured_indexes(mock_parent, main_thread):
    main_thread.parent.db_read.side_effect = lambda key: {
        "IAS": (101.0, False, False, False, False, False),
        "TAS": 202.0,
        "LAT": 40.0,
        "LONG": -83.0,
        "ALT": 1234.0,
    }[key]

    main_thread.senddata()

    packets = [call_args.args[0] for call_args in main_thread.sock.sendto.call_args_list]
    assert len(packets) == 2
    assert packets[0].startswith(b"DATA\0" + struct.pack("i", 3))
    assert struct.unpack("f", packets[0][9:13])[0] == pytest.approx(101.0)
    assert packets[0][13:17] == b"\x00\xc0\x79\xc4"
    assert packets[0][17:21] == b"\x00\xc0\x79\xc4"
    assert struct.unpack("f", packets[0][21:25])[0] == pytest.approx(202.0)
    assert packets[1].startswith(b"DATA\0" + struct.pack("i", 20))


def build_packet(index, values):
    packet = b"DATA\0" + struct.pack("i", index)
    for value in values:
        packet += struct.pack("f", value)
    return packet


def test_run_handles_bad_packets_and_decodes_data(monkeypatch, mock_parent, main_thread):
    packets = [
        b"NOPE\0",
        b"DATA\0bad",
        build_packet(3, [55.0, 0.0, 66.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
    ]

    def fake_select(_read, _write, _error, _timeout):
        return ([main_thread.sock], [], []) if packets else ([], [], [])

    def fake_recvfrom(_size):
        packet = packets.pop(0)
        if not packets:
            main_thread.getout = True
        return packet, ("127.0.0.1", 1)

    monkeypatch.setattr(xplane.select, "select", fake_select)
    main_thread.sock.recvfrom.side_effect = fake_recvfrom
    main_thread.senddata = lambda: None

    main_thread.run()

    mock_parent.log.error.assert_has_calls(
        [call("Bad data packet"), call("Bad packet length")]
    )
    mock_parent.db_write.assert_has_calls(
        [call("IAS", pytest.approx(55.0)), call("TAS", pytest.approx(66.0))]
    )


def test_thread_stop_and_close_are_idempotent(main_thread):
    main_thread.stop()
    main_thread.close()
    main_thread.close()

    assert main_thread.getout is True
    assert main_thread.sock.close.call_count == 1
    assert main_thread.sock_closed is True


def test_plugin_lifecycle(mock_parent):
    with patch("socket.socket"):
        plugin = Plugin("test_plugin", mock_parent.config, MagicMock())

    with patch.object(plugin.thread, "start") as mock_start, \
         patch.object(plugin.thread, "stop") as mock_stop, \
         patch.object(plugin.thread, "is_alive", return_value=False):
        plugin.run()
        mock_start.assert_called_once()

        plugin.stop()
        mock_stop.assert_called_once()

    with patch("socket.socket"):
        plugin = Plugin("test_plugin", mock_parent.config, MagicMock())
        plugin.thread.is_alive = MagicMock(return_value=True)
        plugin.thread.join = MagicMock()
        with pytest.raises(plugin_base.PluginFail):
            plugin.stop()
