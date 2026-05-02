import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.db_persister as db_persister


class FakeLog:
    def __init__(self):
        self.infos = []
        self.debugs = []

    def info(self, message):
        self.infos.append(message)

    def debug(self, message):
        self.debugs.append(message)


class FakeParent:
    def __init__(self, config):
        self.config = config
        self.log = FakeLog()
        self.callbacks = []

    def db_callback_add(self, key, function):
        self.callbacks.append((key, function))


def test_main_thread_creates_tables_persists_rows_and_flushes(tmp_path, monkeypatch):
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        """
entries:
  - key: ALT
    type: float
  - key: COUNT
    type: int
  - key: ACTIVE
    type: bool
  - key: NAME
    type: string
  - key: SKIP
    type: float
""",
        encoding="utf-8",
    )
    h5_path = tmp_path / "data.h5"
    parent = FakeParent(
        {
            "CONFIGPATH": str(tmp_path),
            "db_schema": "schema.yaml",
            "h5f_file": "data.h5",
            "entries_regex": "^(ALT|COUNT|ACTIVE|NAME)$",
        }
    )
    monkeypatch.setattr(db_persister.time, "time", lambda: 123.45)

    thread = db_persister.MainThread(parent)
    try:
        assert [key for key, _callback in parent.callbacks] == [
            "ALT",
            "COUNT",
            "ACTIVE",
            "NAME",
        ]
        assert "create table ALT" in parent.log.debugs

        callbacks = dict(parent.callbacks)
        callbacks["ALT"]("ALT", (12.5, False, False, False, False, False))
        callbacks["COUNT"]("COUNT", (3, False, False, False, False, False))
        callbacks["ACTIVE"]("ACTIVE", (True, False, False, False, False, False))
        callbacks["NAME"]("NAME", ("OK", False, False, False, False, False))

        sleeps = 0

        def stop_after_flush(_seconds):
            nonlocal sleeps
            sleeps += 1
            thread.getout = True

        monkeypatch.setattr(db_persister.time, "sleep", stop_after_flush)
        thread.run()

        assert thread.running is False
        assert thread.h5f.root.ALT.nrows == 1
        assert thread.h5f.root.ALT[0]["value"] == 12.5
        assert thread.h5f.root.ALT[0]["timestamp"] == 123.45
        assert thread.h5f.root.COUNT[0]["value"] == 3
        assert bool(thread.h5f.root.ACTIVE[0]["value"]) is True
        assert thread.h5f.root.NAME[0]["value"] == b"OK"
        assert sleeps == 1
    finally:
        thread.h5f.close()

    parent = FakeParent(parent.config)
    thread = db_persister.MainThread(parent)
    try:
        assert "create table ALT" not in parent.log.debugs
    finally:
        thread.h5f.close()


def test_main_thread_stop_sets_getout(tmp_path):
    schema = tmp_path / "schema.yaml"
    schema.write_text("entries: []\n", encoding="utf-8")
    parent = FakeParent(
        {
            "CONFIGPATH": str(tmp_path),
            "db_schema": "schema.yaml",
            "h5f_file": "data.h5",
            "entries_regex": ".*",
        }
    )
    thread = db_persister.MainThread(parent)
    try:
        thread.stop()
        assert thread.getout is True
    finally:
        thread.h5f.close()


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

    monkeypatch.setattr(db_persister, "MainThread", DummyThread)
    plugin = db_persister.Plugin("db_persister", {}, {})

    plugin.run()
    plugin.stop()

    assert plugin.thread.started is True
    assert plugin.thread.stopped is True
    assert plugin.get_status() == db_persister.OrderedDict()

    failing = db_persister.Plugin("db_persister", {}, {})
    failing.thread.alive = True
    with pytest.raises(plugin_base.PluginFail):
        failing.stop()
