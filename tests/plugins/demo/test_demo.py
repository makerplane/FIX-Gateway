import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.demo as demo


class FakeLog:
    def __init__(self):
        self.debugs = []

    def debug(self, message):
        self.debugs.append(message)


class FakeParent:
    def __init__(self):
        self.log = FakeLog()
        self.values = {}
        self.writes = []

    def db_write(self, key, value):
        self.values[key] = value
        self.writes.append((key, value))

    def db_read(self, key):
        return (self.values[key], False, False, False, False, False)


def test_main_thread_initializes_points_and_runs_script_paths(monkeypatch):
    parent = FakeParent()
    thread = demo.MainThread(parent)
    assert parent.values["IAS"] == 113.0
    assert parent.values["LAT"] == 40.000200

    sleeps = 0

    def stop_after_script_progress(_seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps >= 25:
            thread.getout = True

    monkeypatch.setattr(demo.time, "sleep", stop_after_script_progress)

    thread.run()

    assert thread.running is False
    assert ("MAVMSG", "NO DATA") in parent.writes
    assert any(
        key == "ROLL" and isinstance(value, (int, float)) and value > 0
        for key, value in parent.writes
    )
    assert any(key == "LAT" and value != 40.000200 for key, value in parent.writes)


def test_main_thread_wraps_single_entry_script_and_stop(monkeypatch):
    parent = FakeParent()
    thread = demo.MainThread(parent)
    thread.script = [{"MAVMSG": "NO DATA"}]

    def stop_after_sleep(_seconds):
        thread.getout = True

    monkeypatch.setattr(demo.time, "sleep", stop_after_sleep)
    thread.run()
    thread.stop()

    assert ("MAVMSG", "NO DATA") in parent.writes
    assert thread.running is False
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

    monkeypatch.setattr(demo, "MainThread", DummyThread)
    plugin = demo.Plugin("demo", {}, {})

    plugin.run()
    plugin.stop()

    assert plugin.thread.started is True
    assert plugin.thread.stopped is True
    assert plugin.get_status() == demo.OrderedDict()

    failing = demo.Plugin("demo", {}, {})
    failing.thread.alive = True
    with pytest.raises(plugin_base.PluginFail):
        failing.stop()
