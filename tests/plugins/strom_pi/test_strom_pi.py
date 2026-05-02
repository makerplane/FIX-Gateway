import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.strom_pi as strom_pi


class FakeLog:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, message):
        self.errors.append(message)

    def warning(self, message):
        self.warnings.append(message)


class FakeParent:
    def __init__(self, config=None):
        self.config = config or {"port": "/dev/strom"}
        self.log = FakeLog()
        self.writes = []

    def db_write(self, key, value):
        self.writes.append((key, value))


class FakeSerial:
    def __init__(self, lines=None, read_error=False):
        self.lines = list(lines or [])
        self.read_error = read_error
        self.writes = []
        self.reset_count = 0

    def reset_input_buffer(self):
        self.reset_count += 1
        if self.read_error and self.reset_count == 1:
            raise strom_pi.serial.SerialException()

    def write(self, data):
        self.writes.append(data)

    def readline(self):
        return self.lines.pop(0)


def status_lines(bat=b"4", charging=b"1", output=b"0"):
    lines = [b"0"] * 38
    lines[22] = bat
    lines[23] = charging
    lines[31] = b"1.0"
    lines[32] = b"2.0"
    lines[33] = b"3.0"
    lines[34] = b"4.0"
    lines[35] = output
    return lines


def test_main_thread_logs_open_read_float_and_integer_errors(monkeypatch):
    parent = FakeParent()
    monkeypatch.setattr(
        strom_pi.serial,
        "Serial",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(strom_pi.serial.SerialException()),
    )
    strom_pi.MainThread(parent).run()
    assert parent.log.errors == ["Serial port error"]

    parent = FakeParent()
    fake_serial = FakeSerial(status_lines(), read_error=True)
    thread = strom_pi.MainThread(parent)
    monkeypatch.setattr(strom_pi.serial, "Serial", lambda *_args, **_kwargs: fake_serial)
    monkeypatch.setattr(strom_pi.time, "sleep", lambda _seconds: setattr(thread, "getout", True))
    thread.run()
    assert parent.log.errors == ["Serial port error"]

    parent = FakeParent()
    bad_float = status_lines()
    bad_float[31] = b"not-a-float"
    fake_serial = FakeSerial(bad_float)
    monkeypatch.setattr(strom_pi.serial, "Serial", lambda *_args, **_kwargs: fake_serial)
    strom_pi.MainThread(parent).run()
    assert parent.log.errors == ["Bad data"]

    parent = FakeParent()
    bad_int = status_lines(bat=b"not-int")
    good = status_lines(bat=b"9", output=b"0")
    fake_serial = FakeSerial(bad_int + good)
    thread = strom_pi.MainThread(parent)
    monkeypatch.setattr(strom_pi.serial, "Serial", lambda *_args, **_kwargs: fake_serial)

    def stop_after_second_sleep(_seconds):
        if fake_serial.reset_count >= 2:
            thread.getout = True

    monkeypatch.setattr(strom_pi.time, "sleep", stop_after_second_sleep)
    thread.run()
    assert parent.log.errors == ["Bad data", "Bad data"]


def test_main_thread_tracks_power_failure_restore_and_shutdown(monkeypatch):
    parent = FakeParent({"port": "/dev/strom", "shutdown_after": 0})
    fake_serial = FakeSerial(
        status_lines(bat=b"1", charging=b"0", output=b"3")
        + status_lines(bat=b"2", charging=b"1", output=b"0")
    )
    thread = strom_pi.MainThread(parent)
    monkeypatch.setattr(strom_pi.serial, "Serial", lambda *_args, **_kwargs: fake_serial)
    times = iter([100.0, 101.0, 102.0])
    monkeypatch.setattr(strom_pi.time, "time", lambda: next(times))
    shutdowns = []
    monkeypatch.setattr(strom_pi.os, "system", lambda command: shutdowns.append(command))

    def stop_after_second_loop(_seconds):
        if fake_serial.reset_count >= 2:
            thread.getout = True

    monkeypatch.setattr(strom_pi.time, "sleep", stop_after_second_loop)

    thread.run()
    thread.stop()

    assert ("POWER_FAIL", True) in parent.writes
    assert ("POWER_FAIL", False) in parent.writes
    assert ("BAT_CHARGING", 0) in parent.writes
    assert ("BAT_REMAINING", 10) in parent.writes
    assert ("BAT_REMAINING", 25) in parent.writes
    assert parent.log.warnings == ["Power has failed", "Power has been restored"]
    assert b"quit\n" in fake_serial.writes
    assert b"poweroff\n" in fake_serial.writes
    assert shutdowns == ["sudo shutdown -h now"]
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

    monkeypatch.setattr(strom_pi, "MainThread", DummyThread)
    plugin = strom_pi.Plugin("strom_pi", {"port": "/dev/strom"}, {})

    plugin.run()
    plugin.stop()

    assert plugin.thread.started is True
    assert plugin.thread.stopped is True
    assert plugin.get_status() == strom_pi.OrderedDict()

    failing = strom_pi.Plugin("strom_pi", {"port": "/dev/strom"}, {})
    failing.thread.alive = True
    with pytest.raises(plugin_base.PluginFail):
        failing.stop()
