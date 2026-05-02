import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.grand_rapids_eis as eis


class FakeSerial:
    def __init__(self, frames):
        self.frames = list(frames)
        self.closed = False

    def read_until(self, _terminator, size=0):
        return self.frames.pop(0)

    def close(self):
        self.closed = True


class FakeLog:
    pass


class FakeParent:
    def __init__(self, model):
        self.config = {"port": "/dev/eis", "model": model}
        self.log = FakeLog()
        self.writes = []

    def db_write(self, key, value):
        self.writes.append((key, value))


def put(frame, offset, value, size=2):
    frame[offset : offset + size] = int(value).to_bytes(size, "big")


def frame_2004(oat=90):
    frame = bytearray(48)
    put(frame, 0, 2500)
    put(frame, 2, 212)
    put(frame, 4, 230)
    put(frame, 6, 932)
    put(frame, 8, 950)
    put(frame, 12, 1234)
    put(frame, 14, 137)
    put(frame, 21, 194)
    put(frame, 23, 212)
    frame[20] = oat
    frame[25] = 55
    put(frame, 30, 123)
    put(frame, 32, 42)
    put(frame, 39, 2992)
    return bytes(frame)


def frame_4000(oat=200):
    frame = bytearray(73)
    put(frame, 0, 2400)
    for offset in range(2, 14, 2):
        put(frame, offset, 212)
    for offset in range(14, 26, 2):
        put(frame, offset, 932)
    put(frame, 32, 4321)
    put(frame, 34, 128)
    frame[41] = oat
    put(frame, 42, 230)
    frame[44] = 66
    put(frame, 53, 194)
    put(frame, 55, 321)
    put(frame, 57, 24)
    put(frame, 64, 3001)
    return bytes(frame)


def test_main_thread_parses_2004_frames_and_bad_length(monkeypatch, capsys):
    fake_serial = FakeSerial([b"bad", frame_2004()])
    monkeypatch.setattr(eis.serial, "Serial", lambda *_args, **_kwargs: fake_serial)
    parent = FakeParent(2004)
    thread = eis.MainThread(parent)

    def stop_after_good_write(key, value):
        parent.writes.append((key, value))
        if key == "H2OT1":
            thread.getout = True

    parent.db_write = stop_after_good_write
    thread.run()
    thread.stop()

    output = capsys.readouterr().out
    assert "EIS model: 2004" in output
    assert "bad frame" in output
    assert ("TACH1", 2500) in parent.writes
    assert ("CHT11", 100) in parent.writes
    assert ("EGT12", 510) in parent.writes
    assert ("VOLT", 13.7) in parent.writes
    assert ("OAT", 32) in parent.writes
    assert fake_serial.closed is True


def test_main_thread_parses_4000_frames_negative_oat_and_unsupported_model(monkeypatch, capsys):
    fake_serial = FakeSerial([frame_4000()])
    monkeypatch.setattr(eis.serial, "Serial", lambda *_args, **_kwargs: fake_serial)
    parent = FakeParent(4000)
    thread = eis.MainThread(parent)

    def stop_after_good_write(key, value):
        parent.writes.append((key, value))
        if key == "H2OT1":
            thread.getout = True

    parent.db_write = stop_after_good_write
    thread.run()

    assert ("TACH1", 2400) in parent.writes
    assert ("CHT16", 100) in parent.writes
    assert ("EGT16", 500) in parent.writes
    assert ("VOLT", 12.8) in parent.writes
    assert ("OAT", -48) in parent.writes
    assert ("ALT", 4321) in parent.writes

    eis.MainThread(FakeParent(1234))
    assert "Unsupported EIS model" in capsys.readouterr().out


def test_main_thread_2004_negative_oat_and_4000_bad_frame_normal_oat(monkeypatch, capsys):
    fake_serial = FakeSerial([frame_2004(oat=200)])
    monkeypatch.setattr(eis.serial, "Serial", lambda *_args, **_kwargs: fake_serial)
    parent = FakeParent(2004)
    thread = eis.MainThread(parent)
    parent.db_write = lambda key, value: parent.writes.append((key, value)) or (
        setattr(thread, "getout", True) if key == "H2OT1" else None
    )
    thread.run()
    assert ("OAT", -48) in parent.writes

    fake_serial = FakeSerial([b"bad", frame_4000(oat=90)])
    monkeypatch.setattr(eis.serial, "Serial", lambda *_args, **_kwargs: fake_serial)
    parent = FakeParent(6000)
    thread = eis.MainThread(parent)
    parent.db_write = lambda key, value: parent.writes.append((key, value)) or (
        setattr(thread, "getout", True) if key == "H2OT1" else None
    )
    thread.run()
    assert "bad frame" in capsys.readouterr().out
    assert ("OAT", 32) in parent.writes


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

    monkeypatch.setattr(eis, "MainThread", DummyThread)
    plugin = eis.Plugin("eis", {"port": "/dev/eis", "model": 2004}, {})

    plugin.run()
    plugin.stop()

    assert plugin.thread.started is True
    assert plugin.thread.stopped is True
    assert plugin.get_status() == eis.OrderedDict()

    failing = eis.Plugin("eis", {"port": "/dev/eis", "model": 2004}, {})
    failing.thread.alive = True
    with pytest.raises(plugin_base.PluginFail):
        failing.stop()
