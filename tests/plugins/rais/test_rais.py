import sys
from types import SimpleNamespace

import fixgw.plugins.rais as rais


class FakeLog:
    def __init__(self):
        self.debugs = []

    def debug(self, message):
        self.debugs.append(message)


class FakeParent:
    def __init__(self, config=None):
        self.config = config or {"rais_server_module": "fake_rais"}
        self.log = FakeLog()
        self.writes = []

    def db_write(self, key, value):
        self.writes.append((key, value))


class FakeBarometer:
    def __init__(self, config):
        self.config = config
        self.sent = []

    def send(self, value):
        self.sent.append(value)


class FakeRAIS:
    def __init__(self, config_file=None):
        self.config_file = config_file
        self.pubsub_config = {"pub": "sub"}
        self.parameter_callback = None
        self.listen_calls = []

    def setParameterCallback(self, callback):
        self.parameter_callback = callback

    def listen(self, loop=False, timeout=0):
        self.listen_calls.append((loop, timeout))


def test_main_thread_imports_module_wires_callbacks_and_runs(monkeypatch):
    fake_module = SimpleNamespace(RAIS=FakeRAIS, GivenBarometer=FakeBarometer)
    monkeypatch.setattr(rais.importlib, "import_module", lambda name: fake_module)
    callbacks = []
    monkeypatch.setattr(
        rais,
        "callback_add",
        lambda owner, key, function, udata: callbacks.append((owner, key, function, udata)),
    )
    parent = FakeParent(
        {
            "rais_server_module": "fake_rais",
            "rais_config_path": "/tmp/rais.yaml",
        }
    )
    thread = rais.MainThread(parent)

    assert thread.rais.config_file == "/tmp/rais.yaml"
    assert thread.rais.parameter_callback == thread.callback
    assert thread.baro_publisher.config == {"pub": "sub"}

    thread.callback("ALT", 123)
    thread.baro_changed("BARO", (29.92, False, False, False, False, False), None)
    assert parent.writes == [("ALT", 123)]
    assert thread.baro_publisher.sent == [29.92]

    def stop_after_sleep(_seconds):
        thread.getout = True

    monkeypatch.setattr(rais.time, "sleep", stop_after_sleep)
    thread.run()

    assert callbacks == [("", "BARO", thread.baro_changed, "")]
    assert thread.rais.listen_calls == [(False, 0)]


def test_baro_changed_swallows_publisher_errors(monkeypatch):
    fake_module = SimpleNamespace(RAIS=FakeRAIS, GivenBarometer=FakeBarometer)
    monkeypatch.setattr(rais.importlib, "import_module", lambda name: fake_module)
    thread = rais.MainThread(FakeParent())
    thread.baro_publisher.send = lambda _value: (_ for _ in ()).throw(RuntimeError("lost"))

    thread.baro_changed("BARO", (30.01, False, False, False, False, False), None)
    thread.stop()
    assert thread.getout is True


def test_plugin_adds_rais_directory_and_stops_thread(monkeypatch):
    class DummyThread:
        def __init__(self, _parent):
            self.started = False
            self.stopped = False
            self.alive = True

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

        def is_alive(self):
            was_alive = self.alive
            self.alive = False
            return was_alive

        def join(self):
            self.joined = True

    monkeypatch.setattr(rais, "MainThread", DummyThread)
    new_path = "/tmp/fixgw-rais-test"
    if new_path in sys.path:
        sys.path.remove(new_path)

    plugin = rais.Plugin(
        "rais",
        {"rais_directory": new_path, "rais_server_module": "fake_rais"},
        {},
    )
    plugin.run()
    plugin.stop()

    assert new_path in sys.path
    assert plugin.thread.started is True
    assert plugin.thread.stopped is True
    assert plugin.thread.joined is True

    plugin = rais.Plugin(
        "rais",
        {"rais_directory": new_path, "rais_server_module": "fake_rais"},
        {},
    )
    plugin.thread.alive = False
    plugin.stop()
    assert plugin.thread.stopped is True

    plugin = rais.Plugin(
        "rais",
        {"rais_directory": new_path, "rais_server_module": "fake_rais"},
        {},
    )
    assert sys.path.count(new_path) == 1
