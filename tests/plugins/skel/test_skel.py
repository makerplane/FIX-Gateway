from types import SimpleNamespace

import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.skel as skel


class FakeLog:
    def __init__(self):
        self.debugs = []

    def debug(self, message):
        self.debugs.append(message)


def test_main_thread_counts_until_stopped(monkeypatch):
    parent = SimpleNamespace(log=FakeLog())
    thread = skel.MainThread(parent)

    def stop_after_sleep(_seconds):
        thread.getout = True

    monkeypatch.setattr(skel.time, "sleep", stop_after_sleep)

    thread.run()
    thread.stop()

    assert thread.count == 1
    assert thread.running is False
    assert thread.getout is True
    assert parent.log.debugs == ["Yep"]


def test_plugin_lifecycle_status_and_failure(monkeypatch):
    class DummyThread:
        def __init__(self, _parent):
            self.count = 7
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

    monkeypatch.setattr(skel, "MainThread", DummyThread)
    plugin = skel.Plugin("skel", {}, {})

    plugin.run()
    plugin.stop()

    assert plugin.thread.started is True
    assert plugin.thread.stopped is True
    assert plugin.get_status() == skel.OrderedDict({"Count": 7})

    failing = skel.Plugin("skel", {}, {})
    failing.thread.alive = True
    with pytest.raises(plugin_base.PluginFail):
        failing.stop()
