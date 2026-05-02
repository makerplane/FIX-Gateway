import fixgw.plugins.test as test_plugin


class FakeLog:
    def __init__(self):
        self.debugs = []

    def debug(self, message):
        self.debugs.append(message)


class FakeParent:
    def __init__(self):
        self.config = {"low": 10, "high": 20, "key": "ALT"}
        self.log = FakeLog()
        self.writes = []

    def db_write(self, key, value):
        self.writes.append((key, value))


def test_test_thread_writes_random_value_in_configured_range(monkeypatch):
    parent = FakeParent()
    thread = test_plugin.TestThread(parent)
    monkeypatch.setattr(test_plugin.random, "random", lambda: 0.25)

    writes = parent.writes

    def stop_after_write(key, value):
        writes.append((key, value))
        thread.getout = True

    parent.db_write = stop_after_write

    thread.run()

    assert parent.log.debugs == ["Starting Thread"]
    assert parent.writes == [("ALT", 12.5)]


def test_plugin_starts_and_stops_thread(monkeypatch):
    class DummyThread:
        def __init__(self, parent):
            self.parent = parent
            self.started = False
            self.getout = False
            self.joined = False

        def start(self):
            self.started = True

        def join(self):
            self.joined = True

    monkeypatch.setattr(test_plugin, "TestThread", DummyThread)
    plugin = test_plugin.Plugin("test", {}, {})

    plugin.run()
    plugin.stop()

    assert plugin.t.started is True
    assert plugin.t.getout is True
    assert plugin.t.joined is True
