from types import SimpleNamespace

import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.command as command_plugin


class FakeItem:
    def __init__(self):
        self.description = "Altitude"
        self.typestring = "float"
        self.value = (123.4, False, True, False, False, False)
        self.min = 0
        self.max = 1000
        self.units = "ft"
        self.tol = 100
        self.aux = {"low": 1, "": 2}
        self.callbacks = [("owner", object(), None)]
        self.bad = False
        self.fail = False
        self.annunciate = False
        self.secfail = False


class FakeParent:
    def __init__(self, config=None):
        self.config = config or {}
        self.log = SimpleNamespace(debug=lambda *_args: None)
        self.item = FakeItem()
        self.writes = []
        self.callbacks_added = []
        self.callbacks_deleted = []
        self.quit_called = False

    def db_read(self, key):
        if key == "MISSING":
            raise KeyError(key)
        return ("value", False, False, False, False, False)

    def db_write(self, key, value):
        if key == "MISSING":
            raise KeyError(key)
        self.writes.append((key, value))

    def db_list(self):
        return ["B", "A"]

    def db_get_item(self, key):
        if key == "MISSING":
            raise KeyError(key)
        return self.item

    def db_callback_add(self, key, callback):
        if key == "MISSING":
            raise KeyError(key)
        self.callbacks_added.append((key, callback))

    def db_callback_del(self, key, callback):
        if key == "MISSING":
            raise KeyError(key)
        self.callbacks_deleted.append((key, callback))

    def quit(self):
        self.quit_called = True


def make_command(parent=None):
    command = command_plugin.Command()
    command.setplugin(parent or FakeParent())
    return command


def test_command_read_write_list_report_status_and_quit(capsys, monkeypatch):
    parent = FakeParent()
    command = make_command(parent)
    monkeypatch.setattr(command_plugin.status, "get_string", lambda: "status text")

    command.do_read("ALT")
    command.do_read("MISSING")
    command.do_write("")
    command.do_write("ALT 42")
    command.do_write("MISSING 42")
    command.do_list("")
    empty_command = make_command(parent)
    parent.db_list = lambda: []
    empty_command.do_list("")
    command.do_report("ALT")
    command.do_report("MISSING")
    command.do_status("")
    command.callback_function("ALT", (1, False, False, False, False, False), None)

    output = capsys.readouterr().out
    assert "('value', False, False, False, False, False)" in output
    assert "Unknown Key MISSING" in output
    assert "Missing Argument" in output
    assert "A\nB\n" in output
    assert "Altitude" in output
    assert "Auxillary Data:" in output
    assert "  low = 1" in output
    assert "Callback function defined: owner" in output
    assert "status text" in output
    assert "ALT = (1, False, False, False, False, False)" in output
    assert parent.writes == [("ALT", "42")]
    assert command.do_quit("") is True
    assert command.do_exit("") is True
    assert command.do_EOF("") is True


def test_command_subscribe_unsubscribe_and_flag_paths(capsys):
    parent = FakeParent()
    command = make_command(parent)

    command.do_sub("ALT")
    command.do_sub("ALT")
    command.do_sub("MISSING")
    command.do_unsub("ALT")
    command.do_unsub("MISSING")
    command.do_flag("")
    with pytest.raises(UnboundLocalError):
        command.do_flag("MISSING bad yes")
    command.do_flag("ALT bad yes")
    command.do_flag("ALT fail true")
    command.do_flag("ALT annunciate 1")
    command.do_flag("ALT secfail high")
    command.do_flag("ALT unknown yes")

    output = capsys.readouterr().out
    assert "Already subscribed to ALT" in output
    assert "Unknown Key MISSING" in output
    assert "Not Enough Arguments" in output
    assert parent.callbacks_added == [("ALT", command.callback_function)]
    assert parent.callbacks_deleted == [("ALT", command.callback_function)]
    assert parent.item.bad is True
    assert parent.item.fail is True
    assert parent.item.annunciate is True
    assert parent.item.secfail is True


def test_main_thread_runs_command_loop_and_optionally_quits():
    parent = FakeParent({"prompt": "TEST>", "quit": True})
    thread = command_plugin.MainThread(parent)
    thread.cmd.cmdloop = lambda: None

    thread.run()

    assert thread.cmd.prompt == "TEST>"
    assert parent.quit_called is True

    parent = FakeParent({"quit": False})
    thread = command_plugin.MainThread(parent)
    thread.cmd.cmdloop = lambda: None
    thread.run()
    thread.stop()

    assert parent.quit_called is False
    assert thread.getout is True


def test_plugin_lifecycle_and_failures(monkeypatch):
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

    monkeypatch.setattr(command_plugin, "MainThread", DummyThread)
    plugin = command_plugin.Plugin("command", {}, {})
    plugin.run()
    plugin.stop()

    assert plugin.thread.started is True
    assert plugin.thread.stopped is True
    assert plugin.is_running() is False

    failing = command_plugin.Plugin("command", {}, {})
    failing.thread.alive = True
    with pytest.raises(plugin_base.PluginFail):
        failing.stop()
