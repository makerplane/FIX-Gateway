from types import SimpleNamespace

import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.shadin as shadin


class FakeLog:
    def __init__(self):
        self.debugs = []
        self.errors = []

    def debug(self, message):
        self.debugs.append(message)

    def error(self, message):
        self.errors.append(message)


class FakeParent:
    def __init__(self):
        self.config = {"port": "/dev/null", "baud": 9600}
        self.log = FakeLog()
        self.keys = ["FUELF1", "FUELF2", "FUELQT"]
        self.writes = []

    def db_list(self):
        return self.keys

    def db_write(self, key, value):
        self.writes.append((key, value))


def test_parse_ignores_empty_incomplete_and_missing_start():
    parent = FakeParent()
    thread = shadin.MainThread(parent)

    thread._parse(b"")
    thread._parse(b"ZO123")
    thread._parse(b"noise\n")

    assert parent.log.debugs == [
        "Incomplete message received",
        "Beginning of message was not found",
    ]
    assert parent.writes == []


def test_parse_writes_fuel_messages_and_handles_optional_second_engine():
    parent = FakeParent()
    thread = shadin.MainThread(parent)

    thread._parse(b"noiseZO012\n")
    thread._parse(b"ZM034\n")
    thread._parse(b"ZR12.5\n")
    parent.keys.remove("FUELF2")
    thread._parse(b"ZM099\n")

    assert parent.writes == [
        ("FUELF1", 120.0),
        ("FUELF2", 340.0),
        ("FUELQT", 12.5),
    ]


def test_parse_logs_bad_numeric_data():
    parent = FakeParent()
    thread = shadin.MainThread(parent)

    thread._parse(b"ZOabc\n")
    thread._parse(b"ZMabc\n")
    thread._parse(b"ZRabc\n")

    assert parent.log.errors == [
        "Bad data received: ZOabc\n",
        "Bad data received: ZMabc\n",
        "Bad data received: ZRabc\n",
    ]


def test_run_handles_open_and_read_errors(monkeypatch):
    parent = FakeParent()
    thread = shadin.MainThread(parent)

    monkeypatch.setattr(
        shadin.serial,
        "Serial",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(shadin.serial.serialutil.SerialException()),
    )
    thread.run()
    assert parent.log.errors == ["Could not open port: /dev/null"]

    class FakeSerial:
        def __init__(self):
            self.calls = 0

        def read_until(self):
            self.calls += 1
            if self.calls == 1:
                return b"ZO001\n"
            thread.getout = True
            raise shadin.serial.SerialException()

    parent = FakeParent()
    thread = shadin.MainThread(parent)
    fake_serial = FakeSerial()
    monkeypatch.setattr(shadin.serial, "Serial", lambda *_args, **_kwargs: fake_serial)
    thread.run()
    thread.stop()

    assert ("FUELF1", 10.0) in parent.writes
    assert "Serial port error" in parent.log.errors
    assert thread.getout is True


def test_plugin_lifecycle_status_and_failure(monkeypatch):
    class DummyThread:
        def __init__(self, _parent):
            self.started = False
            self.stopped = False
            self.alive = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

        def is_alive(self):
            return self.alive

        def join(self, timeout):
            self.joined = timeout

    monkeypatch.setattr(shadin, "MainThread", DummyThread)
    plugin = shadin.Plugin("shadin", {}, {})

    plugin.run()
    plugin.stop()

    assert plugin.thread.started is True
    assert plugin.thread.stopped is True
    assert plugin.get_status() == shadin.OrderedDict()

    failing = shadin.Plugin("shadin", {}, {})
    failing.thread.alive = True
    with pytest.raises(plugin_base.PluginFail):
        failing.stop()
