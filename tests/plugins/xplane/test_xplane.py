import pytest
from unittest.mock import MagicMock, patch, call
from fixgw.plugins.xplane import MainThread, Plugin
import socket
import struct
import time

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


def senddata(self):
    """Function that sends data to X-Plane"""
    for each in self.inputkeys:
        data = b"DATA" + b"\x00"  # Start with bytes
        data += struct.pack("i", int(each))

        for i in range(8):
            if self.inputkeys[each][i].lower() == "x":
                data += b"\x00\xc0\x79\xc4"  # Append fixed bytes
            else:
                value = float(self.parent.db_read(self.inputkeys[each][i].upper()))
                data += struct.pack("f", value)  # Pack as float and append
        
        self.sock.sendto(data, ('127.0.0.1', 49200))



def test_plugin_lifecycle(mock_parent):
    plugin = Plugin("test_plugin", mock_parent.config)

    with patch.object(plugin.thread, "start") as mock_start, \
         patch.object(plugin.thread, "stop") as mock_stop, \
         patch.object(plugin.thread, "is_alive", return_value=False):
        plugin.run()
        mock_start.assert_called_once()

        plugin.stop()
        mock_stop.assert_called_once()

