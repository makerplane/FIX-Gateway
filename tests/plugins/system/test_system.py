import time

import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.system as system_plugin


class FakeItem:
    def __init__(self):
        self.value = None


class FakePlugin:
    def __init__(self, config):
        self.config = config
        self.items = {}

    def db_get_item(self, key):
        item = FakeItem()
        self.items[key] = item
        return item


def test_time_function_writes_configured_gmt_and_local_items(monkeypatch):
    plugin = FakePlugin(
        {
            "time": {
                "keys": {
                    "gmt_string": "GMTS",
                    "gmt_hours": "GMTH",
                    "gmt_minutes": "GMTM",
                    "gmt_seconds": "GMTSS",
                    "local_string": "LOCS",
                    "local_hours": "LOCH",
                    "local_minutes": "LOCM",
                    "local_seconds": "LOCS2",
                },
                "gmt_format": "%H-%M-%S",
                "local_format": "%H/%M/%S",
            }
        }
    )
    gmt = time.struct_time((2024, 1, 1, 3, 4, 5, 0, 1, 0))
    local = time.struct_time((2024, 1, 1, 13, 14, 15, 0, 1, 0))
    monkeypatch.setattr(system_plugin.time, "gmtime", lambda: gmt)
    monkeypatch.setattr(system_plugin.time, "localtime", lambda: local)

    update_time = system_plugin.timeFunctionFactory(plugin)
    update_time()

    assert plugin.items["GMTS"].value == "03-04-05"
    assert plugin.items["GMTH"].value == 3
    assert plugin.items["GMTM"].value == 4
    assert plugin.items["GMTSS"].value == 5
    assert plugin.items["LOCS"].value == "13/14/15"
    assert plugin.items["LOCH"].value == 13
    assert plugin.items["LOCM"].value == 14
    assert plugin.items["LOCS2"].value == 15


def test_time_function_uses_defaults_and_ignores_missing_items(monkeypatch):
    plugin = FakePlugin({"time": {"keys": {}}})
    gmt = time.struct_time((2024, 1, 1, 3, 4, 5, 0, 1, 0))
    monkeypatch.setattr(system_plugin.time, "gmtime", lambda: gmt)
    monkeypatch.setattr(system_plugin.time, "localtime", lambda: gmt)

    update_time = system_plugin.timeFunctionFactory(plugin)
    update_time()

    assert plugin.items == {}


def test_main_thread_runs_registered_functions_until_stopped(monkeypatch):
    parent = type("Parent", (), {"log": object()})()
    thread = system_plugin.MainThread(parent)
    calls = []
    thread.functions.append(lambda: calls.append("called"))

    def stop_after_sleep(_seconds):
        thread.getout = True

    monkeypatch.setattr(system_plugin.time, "sleep", stop_after_sleep)

    thread.run()
    thread.stop()

    assert calls == ["called"]
    assert thread.running is False
    assert thread.getout is True


def test_plugin_lifecycle_with_and_without_time_function(monkeypatch):
    class DummyThread:
        def __init__(self, _parent):
            self.functions = []
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

    monkeypatch.setattr(system_plugin, "MainThread", DummyThread)
    monkeypatch.setattr(system_plugin, "timeFunctionFactory", lambda plugin: "time-func")
    plugin = system_plugin.Plugin("system", {"time": {"enable": True}}, {})

    plugin.run()
    plugin.stop()

    assert plugin.thread.functions == ["time-func"]
    assert plugin.thread.started is True
    assert plugin.thread.stopped is True
    assert plugin.get_status() == system_plugin.OrderedDict()

    plugin = system_plugin.Plugin("system", {"time": {"enable": False}}, {})
    plugin.run()
    assert plugin.thread.functions == []

    plugin = system_plugin.Plugin("system", {}, {})
    plugin.run()
    assert plugin.thread.functions == []

    failing = system_plugin.Plugin("system", {}, {})
    failing.thread.alive = True
    with pytest.raises(plugin_base.PluginFail):
        failing.stop()
