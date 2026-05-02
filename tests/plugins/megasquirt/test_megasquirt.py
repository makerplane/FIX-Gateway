from types import SimpleNamespace

import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.megasquirt as megasquirt_plugin
from fixgw.plugins.megasquirt import megasquirt


class FakeLog:
    def __init__(self):
        self.debugs = []

    def debug(self, message):
        self.debugs.append(message)


class FakeParent:
    def __init__(self):
        self.log = FakeLog()
        self.recvcount = 0
        self.writes = []
        self.bus = None

    def db_write(self, key, value):
        self.writes.append((key, value))


class FakeBus:
    def __init__(self, messages):
        self.messages = list(messages)

    def recv(self, _timeout):
        return self.messages.pop(0)


def test_get_builds_message_map_and_converts_units():
    parent = FakeParent()
    config = {
        "EAEfcor1": "COR",
        "baro": "BARO",
        "fuelflow": "FUELF",
        "AFR1": "AFR",
    }
    getter = megasquirt.Get(parent, config)
    parent.bus = FakeBus(
        [
            SimpleNamespace(arbitration_id=1549, data=bytes([0x01, 0xF4, 0, 0, 0, 0, 0, 0])),
            SimpleNamespace(arbitration_id=1522, data=bytes([0x03, 0xE8, 0, 0, 0, 0, 0, 0])),
            SimpleNamespace(arbitration_id=1572, data=bytes([0, 0, 0, 0, 0x03, 0xE8, 0, 0])),
            SimpleNamespace(arbitration_id=1551, data=bytes([123, 0, 0, 0, 0, 0, 0, 0])),
            None,
        ]
    )

    original_recv = parent.bus.recv

    def stop_after_none(timeout):
        msg = original_recv(timeout)
        if msg is None:
            getter.getout = True
        return msg

    parent.bus.recv = stop_after_none
    getter.run()

    assert parent.recvcount == 4
    assert ("COR", 0.5) in parent.writes
    assert ("BARO", 29.61) in parent.writes
    assert ("FUELF", 15.85) in parent.writes
    assert ("AFR", 12.3) in parent.writes


def test_get_ignores_unwanted_messages_and_stop_swallows_join_errors():
    parent = FakeParent()
    getter = megasquirt.Get(parent, {"AFR1": "AFR"})
    getter.getout = True
    parent.bus = FakeBus([SimpleNamespace(arbitration_id=999, data=b"\0" * 8)])

    getter.run()

    assert parent.recvcount == 1
    assert parent.writes == []

    getter.join = lambda: (_ for _ in ()).throw(RuntimeError("already stopped"))
    getter.stop()
    assert getter.getout is True


def test_plugin_lifecycle_status_bus_and_failure(monkeypatch):
    class DummyGet:
        def __init__(self, parent, items):
            self.parent = parent
            self.items = items
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

    monkeypatch.setattr(megasquirt_plugin.megasquirt, "Get", DummyGet)
    buses = []
    monkeypatch.setattr(
        megasquirt_plugin.can,
        "ThreadSafeBus",
        lambda channel, interface: buses.append((channel, interface)) or "bus",
    )
    plugin = megasquirt_plugin.Plugin(
        "megasquirt",
        {"interface": "socketcan", "channel": "can0", "items": {"AFR1": "AFR"}},
        {},
    )

    plugin.run()
    plugin.stop()

    assert plugin.bus == "bus"
    assert buses == [("can0", "socketcan")]
    assert plugin.thread.started is True
    assert plugin.thread.stopped is True
    assert plugin.get_status() == megasquirt_plugin.OrderedDict(
        [
            ("CAN Interface", "socketcan"),
            ("CAN Channel", "can0"),
            ("Received Frames", 0),
            ("Wanted Frames", 0),
            ("Error Count", 0),
        ]
    )

    failing = megasquirt_plugin.Plugin(
        "megasquirt",
        {"interface": "socketcan", "channel": "can0", "items": {"AFR1": "AFR"}},
        {},
    )
    failing.thread.alive = True
    with pytest.raises(plugin_base.PluginFail):
        failing.stop()

    joining = megasquirt_plugin.Plugin(
        "megasquirt",
        {"interface": "socketcan", "channel": "can0", "items": {"AFR1": "AFR"}},
        {},
    )
    joining.thread.alive = True
    joining.thread.join = lambda _timeout: (_ for _ in ()).throw(RuntimeError("join"))
    with pytest.raises(plugin_base.PluginFail):
        joining.stop()


def test_plugin_without_items_leaves_thread_none():
    plugin = megasquirt_plugin.Plugin(
        "megasquirt",
        {"interface": "socketcan", "channel": "can0"},
        {},
    )

    assert plugin.thread is None
