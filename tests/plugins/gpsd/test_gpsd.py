from types import SimpleNamespace

import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.gpsd as gpsd_plugin


class FakeLog:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, message):
        self.errors.append(message)

    def warning(self, message):
        self.warnings.append(message)


class FakeParent:
    def __init__(self):
        self.log = FakeLog()
        self.writes = []

    def db_write(self, key, value):
        self.writes.append((key, value))


def test_main_thread_logs_connect_failure(monkeypatch):
    parent = FakeParent()
    thread = gpsd_plugin.MainThread(parent)
    monkeypatch.setattr(gpsd_plugin.gpsd2, "connect", lambda: (_ for _ in ()).throw(RuntimeError()))

    thread.run()

    assert parent.log.errors == ["Can't connect to gpsd"]


def test_main_thread_writes_2d_and_3d_fix_data_and_warning_path(monkeypatch):
    parent = FakeParent()
    thread = gpsd_plugin.MainThread(parent)
    reports = [
        UserWarning("no fix yet"),
        SimpleNamespace(
            sats=9,
            mode=2,
            lat=40.0,
            lon=-83.0,
            track=123.4,
            hspeed=50.0,
            alt=1000.0,
            error={"x": 2.0, "v": 3.0, "s": 4.0},
        ),
        SimpleNamespace(
            sats=10,
            mode=3,
            lat=41.0,
            lon=-84.0,
            track=222.0,
            hspeed=60.0,
            alt=1000.0,
            error={"x": 1.0, "v": 2.0, "s": 3.0},
        ),
    ]
    monkeypatch.setattr(gpsd_plugin.gpsd2, "connect", lambda: None)

    def get_current():
        report = reports.pop(0)
        if isinstance(report, Exception):
            raise report
        if not reports:
            thread.getout = True
        return report

    monkeypatch.setattr(gpsd_plugin.gpsd2, "get_current", get_current)
    monkeypatch.setattr(gpsd_plugin.time, "sleep", lambda _seconds: None)

    thread.run()
    thread.stop()

    assert parent.log.warnings == ["gpsd warning: no fix yet"]
    assert ("GPS_SATS_VISIBLE", 9) in parent.writes
    assert ("GPS_FIX_TYPE", 2) in parent.writes
    assert ("LAT", 40.0) in parent.writes
    assert ("LONG", -83.0) in parent.writes
    assert ("TRACK", 123.4) in parent.writes
    assert ("GS", 50.0 * 1.94384) in parent.writes
    assert ("GPS_ACCURACY_HORIZ", 2.0 * 3.28084) in parent.writes
    assert ("GPS_ELLIPSOID_ALT", 1000.0 * 3.28084) in parent.writes
    assert ("GPS_ACCURACY_VERTICAL", 2.0 * 3.28084) in parent.writes
    assert ("GPS_ACCURACY_SPEED", 3.0 * 1.94384) in parent.writes


def test_main_thread_writes_satellite_status_without_position_for_no_fix(monkeypatch):
    parent = FakeParent()
    thread = gpsd_plugin.MainThread(parent)
    report = SimpleNamespace(sats=4, mode=1)
    monkeypatch.setattr(gpsd_plugin.gpsd2, "connect", lambda: None)
    monkeypatch.setattr(gpsd_plugin.gpsd2, "get_current", lambda: setattr(thread, "getout", True) or report)
    monkeypatch.setattr(gpsd_plugin.time, "sleep", lambda _seconds: None)

    thread.run()

    assert parent.writes == [("GPS_SATS_VISIBLE", 4), ("GPS_FIX_TYPE", 1)]


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

    monkeypatch.setattr(gpsd_plugin, "MainThread", DummyThread)
    plugin = gpsd_plugin.Plugin("gpsd", {}, {})

    plugin.run()
    plugin.stop()

    assert plugin.thread.started is True
    assert plugin.thread.stopped is True
    assert plugin.get_status() == gpsd_plugin.OrderedDict()

    failing = gpsd_plugin.Plugin("gpsd", {}, {})
    failing.thread.alive = True
    with pytest.raises(plugin_base.PluginFail):
        failing.stop()
