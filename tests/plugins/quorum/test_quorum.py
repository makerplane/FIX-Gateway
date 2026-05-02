from types import SimpleNamespace

import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.quorum as quorum_plugin


class FakeLog:
    def debug(self, _message):
        pass


class FakeParent:
    def __init__(self, config=None):
        self.config = config or {"nodeid": 2, "total_nodes": 3}
        self.log = FakeLog()
        self.quorum = SimpleNamespace(
            enabled=False, leader=True, nodeid=None, vote_key=None, total_nodes=None
        )
        self.writes = []
        self.reads = {
            "QVOTE1": (1, False, False, False, False, False),
            "QVOTE2": (2, False, False, False, False, False),
            "QVOTE3": (3, False, False, False, False, False),
        }

    def db_write(self, key, value):
        self.writes.append((key, value))

    def db_read(self, key):
        return self.reads[key]


def test_main_thread_initializes_quorum_state():
    parent = FakeParent({"nodeid": 4, "total_nodes": 5})

    thread = quorum_plugin.MainThread(parent)

    assert thread.vote_key == "QVOTE4"
    assert thread.vote_value == 4
    assert parent.quorum.enabled is True
    assert parent.quorum.nodeid == 4
    assert parent.quorum.vote_key == "QVOTE4"
    assert parent.quorum.total_nodes == 5


def test_main_thread_run_elects_leader_and_handles_no_quorum(monkeypatch):
    parent = FakeParent({"nodeid": 3, "total_nodes": 3})
    thread = quorum_plugin.MainThread(parent)
    sleeps = 0

    def stop_after_second_sleep(_seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps > 1:
            thread.getout = True

    monkeypatch.setattr(quorum_plugin.time, "sleep", stop_after_second_sleep)

    thread.run()

    assert ("QVOTE3", 3) in parent.writes
    assert ("LEADER", True) in parent.writes
    assert parent.quorum.leader is True

    parent = FakeParent({"nodeid": 2, "total_nodes": 3})
    parent.reads["QVOTE1"] = (1, False, True, False, False, False)
    parent.reads["QVOTE2"] = (2, False, False, False, False, False)
    parent.reads["QVOTE3"] = (3, False, True, False, False, False)
    thread = quorum_plugin.MainThread(parent)
    sleeps = 0
    monkeypatch.setattr(quorum_plugin.time, "sleep", stop_after_second_sleep)

    thread.run()

    assert ("LEADER", False) in parent.writes
    assert parent.quorum.leader is False


def test_main_thread_run_two_nodes_does_not_require_majority(monkeypatch):
    parent = FakeParent({"nodeid": 1, "total_nodes": 2})
    parent.reads = {
        "QVOTE1": (1, False, False, False, False, False),
        "QVOTE2": (2, False, True, False, False, False),
    }
    thread = quorum_plugin.MainThread(parent)
    sleeps = 0

    def stop_after_second_sleep(_seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps > 1:
            thread.getout = True

    monkeypatch.setattr(quorum_plugin.time, "sleep", stop_after_second_sleep)

    thread.run()
    thread.stop()

    assert ("LEADER", True) in parent.writes
    assert thread.getout is True


def test_main_thread_keeps_existing_highest_vote(monkeypatch):
    parent = FakeParent({"nodeid": 1, "total_nodes": 2})
    parent.reads = {
        "QVOTE1": (5, False, False, False, False, False),
        "QVOTE2": (3, False, False, False, False, False),
    }
    thread = quorum_plugin.MainThread(parent)
    sleeps = 0

    def stop_after_second_sleep(_seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps > 1:
            thread.getout = True

    monkeypatch.setattr(quorum_plugin.time, "sleep", stop_after_second_sleep)

    thread.run()

    assert ("LEADER", False) in parent.writes


def test_plugin_lifecycle_status_and_failure(monkeypatch):
    class DummyThread:
        def __init__(self, parent):
            self.parent = parent
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

    monkeypatch.setattr(quorum_plugin, "MainThread", DummyThread)
    plugin = quorum_plugin.Plugin("quorum", {"nodeid": 1, "total_nodes": 2}, {})
    plugin.run()
    plugin.stop()

    assert plugin.thread.started is True
    assert plugin.thread.stopped is True
    assert plugin.get_status() == quorum_plugin.OrderedDict()

    failing = quorum_plugin.Plugin("quorum", {"nodeid": 1, "total_nodes": 2}, {})
    failing.thread.alive = True
    with pytest.raises(plugin_base.PluginFail):
        failing.stop()
