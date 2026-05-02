from pathlib import Path
from types import SimpleNamespace

import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.fgfs as fgfs


class FakeItem:
    def __init__(self, value=0.0):
        self.value = (value, False, False, False, False, False)


class FakeLog:
    def __init__(self):
        self.warnings = []
        self.criticals = []

    def warning(self, message):
        self.warnings.append(message)

    def critical(self, message):
        self.criticals.append(message)


class FakeParent:
    def __init__(self, config=None):
        self.config = config or {
            "send_host": "127.0.0.1",
            "send_port": "5500",
            "recv_host": "127.0.0.1",
            "recv_port": "5501",
            "rate": "10",
            "fg_root": "",
            "xml_file": "",
        }
        self.log = FakeLog()
        self.items = {"ALT": FakeItem(123.456), "IAS": FakeItem(98.7)}

    def db_get_item(self, key):
        return self.items.get(key)


class FakeSocket:
    def __init__(self, recv_values=None):
        self.recv_values = list(recv_values or [])
        self.sent = []
        self.options = []
        self.timeout = None
        self.bound = None

    def setsockopt(self, *args):
        self.options.append(args)

    def settimeout(self, timeout):
        self.timeout = timeout

    def bind(self, address):
        self.bound = address

    def recv(self, _size):
        value = self.recv_values.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def sendto(self, data, address):
        self.sent.append((bytes(data), address))


@pytest.fixture(autouse=True)
def reset_fgfs_globals():
    fgfs.recv_items.clear()
    fgfs.send_items.clear()
    yield
    fgfs.recv_items.clear()
    fgfs.send_items.clear()


def write_protocol(path, root_tag="PropertyList"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""<{root_tag}>
  <generic>
    <output>
      <chunk><name>ALT : altitude</name></chunk>
      <chunk><name>UNKNOWN : ignored</name></chunk>
    </output>
    <input>
      <chunk><name>IAS : airspeed</name><format>%.1f</format></chunk>
      <chunk><name>ALT : altitude</name></chunk>
    </input>
  </generic>
</{root_tag}>
""",
        encoding="utf-8",
    )


def test_item_value_passthrough_and_default_value():
    item = fgfs.Item("ALT")
    assert str(item) == "ALT"
    assert item.value == 0.0

    db_item = FakeItem(12.3)
    item.item = db_item
    assert item.value == 12.3
    item.value = "45.6"
    assert db_item.value == "45.6"


def test_parse_protocol_file_from_protocol_dir_and_fallback(tmp_path):
    protocol_file = tmp_path / "Protocol" / "test.xml"
    write_protocol(protocol_file)

    fgfs.parseProtocolFile(str(tmp_path), "test.xml")

    assert [str(item) for item in fgfs.recv_items] == ["ALT", "UNKNOWN"]
    assert [str(item) for item in fgfs.send_items] == ["IAS", "ALT"]
    assert fgfs.send_items[0].format == "%.1f"
    assert fgfs.send_items[1].format == "%.2f"

    fgfs.recv_items.clear()
    fgfs.send_items.clear()
    fallback = tmp_path / "fallback.xml"
    write_protocol(fallback)
    fgfs.parseProtocolFile(str(tmp_path), "fallback.xml")
    assert len(fgfs.recv_items) == 2


def test_parse_protocol_file_rejects_bad_root(tmp_path):
    protocol_file = tmp_path / "Protocol" / "bad.xml"
    write_protocol(protocol_file, root_tag="Wrong")

    with pytest.raises(ValueError, match="Root Tag is not PropertyList"):
        fgfs.parseProtocolFile(str(tmp_path), "bad.xml")


def test_udp_client_saves_packets_and_timeout_path(monkeypatch):
    fgfs.recv_items.extend([fgfs.Item("ALT"), fgfs.Item("IAS")])
    first = FakeItem()
    second = FakeItem()
    fgfs.recv_items[0].item = first
    fgfs.recv_items[1].item = second
    sock = FakeSocket([b"123,45\n", fgfs.socket.timeout(), b""])
    monkeypatch.setattr(fgfs.socket, "socket", lambda *_args: sock)
    client = fgfs.UDPClient("0.0.0.0", 9999)

    client.save_data("77,88")
    assert first.value == "77"
    assert second.value == "88"

    original_recv = sock.recv

    def stop_after_timeout(size):
        value = original_recv(size)
        if isinstance(value, bytes) and value == b"":
            client.getout = True
        return value

    sock.recv = stop_after_timeout
    client.run()
    client.stop()

    assert sock.bound == ("0.0.0.0", 9999)
    assert client.msg_recv == 1
    assert client.running is False
    assert client.getout is True


def test_main_thread_sends_formatted_values(monkeypatch):
    fgfs.send_items.extend([fgfs.Item("ALT"), fgfs.Item("IAS")])
    fgfs.send_items[0].item = FakeItem(123.456)
    fgfs.send_items[1].item = FakeItem(98.7)
    send_sock = FakeSocket()

    class DummyUDPClient:
        def __init__(self, host, port):
            self.host = host
            self.port = int(port)
            self.started = False
            self.stopped = False
            self.msg_recv = 3

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    sockets = [send_sock]
    monkeypatch.setattr(fgfs, "UDPClient", DummyUDPClient)
    monkeypatch.setattr(fgfs.socket, "socket", lambda *_args: sockets.pop(0))
    parent = FakeParent()
    thread = fgfs.MainThread(parent)

    def stop_after_sleep(_seconds):
        thread.getout = True

    monkeypatch.setattr(fgfs.time, "sleep", stop_after_sleep)
    thread.run()
    thread.stop()

    assert send_sock.sent == [(b"123.46,98.70\n", ("127.0.0.1", 5500))]
    assert thread.msg_sent == 1
    assert thread.clientThread.stopped is True


def test_plugin_run_maps_items_logs_missing_and_status(tmp_path, monkeypatch):
    protocol_file = tmp_path / "Protocol" / "test.xml"
    write_protocol(protocol_file)

    class DummyThread:
        def __init__(self, parent):
            self.parent = parent
            self.started = False
            self.host = parent.config["send_host"]
            self.port = int(parent.config["send_port"])
            self.msg_sent = 4
            self.clientThread = SimpleNamespace(host="recv", port=1111, msg_recv=2)
            self.alive = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

        def is_alive(self):
            return self.alive

        def join(self, timeout):
            self.joined = timeout

    monkeypatch.setattr(fgfs, "MainThread", DummyThread)
    config = FakeParent().config
    config.update({"fg_root": str(tmp_path), "xml_file": "test.xml"})
    plugin = fgfs.Plugin("fgfs", config, {})
    fake_parent = FakeParent()
    fake_parent.items = {"ALT": FakeItem(123.456)}
    plugin.log = fake_parent.log
    plugin.db_get_item = fake_parent.db_get_item
    plugin.run()

    assert plugin.thread.started is True
    assert "UNKNOWN found in protocol file" in plugin.log.warnings[0]
    assert "IAS found in protocol file" in plugin.log.warnings[1]
    status = plugin.get_status()
    assert status["Listening on"] == "recv:1111"
    assert status["Sending to"] == "127.0.0.1:5500"
    assert status["Properties"]["Receiving"] == 2
    assert status["Messages"]["Sent"] == 4
    plugin.stop()


def test_plugin_run_parse_failure_and_stop_failure(monkeypatch):
    class DummyThread:
        def __init__(self, parent):
            self.alive = False

        def stop(self):
            pass

        def is_alive(self):
            return self.alive

        def join(self, timeout):
            self.joined = timeout

    monkeypatch.setattr(fgfs, "MainThread", DummyThread)
    monkeypatch.setattr(fgfs, "parseProtocolFile", lambda *_args: (_ for _ in ()).throw(RuntimeError("bad xml")))
    plugin = fgfs.Plugin("fgfs", FakeParent().config, {})
    plugin.log = FakeLog()
    plugin.run()
    assert str(plugin.log.criticals[0]) == "bad xml"

    class MissingStopThread:
        def is_alive(self):
            return False

    plugin.thread = MissingStopThread()
    plugin.stop()
    assert plugin.get_status() == fgfs.OrderedDict()

    class AliveThread(DummyThread):
        def __init__(self, parent):
            super().__init__(parent)
            self.alive = True

    plugin.thread = AliveThread(plugin)
    with pytest.raises(plugin_base.PluginFail):
        plugin.stop()
