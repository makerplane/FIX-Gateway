import builtins

from fixgw.client.command import Command


class FakeClient:
    def __init__(self):
        self.reads = []
        self.writes = []
        self.subscriptions = []
        self.unsubscriptions = []
        self.callback = None

    def read(self, key):
        self.reads.append(key)
        return [key, "42", ""]

    def writeValue(self, *args):
        self.writes.append(args)

    def getReport(self, key):
        return [key, "Altitude", "float", "0", "100", "ft", "1000", ""]

    def setDataCallback(self, callback):
        self.callback = callback

    def clearDataCallback(self):
        self.callback = None

    def subscribe(self, key):
        self.subscriptions.append(key)

    def unsubscribe(self, key):
        self.unsubscriptions.append(key)

    def flag(self, key, flag, value):
        self.flag_call = (key, flag, value)


def test_read_requires_key(capsys):
    client = FakeClient()
    cmd = Command(client)

    cmd.do_read("   ")

    assert client.reads == []
    assert "Missing Argument" in capsys.readouterr().out


def test_write_collapses_whitespace_and_preserves_string_value():
    client = FakeClient()
    cmd = Command(client)

    cmd.do_write("  CALLSIGN   Experimental One  ")

    assert client.writes == [("CALLSIGN", "Experimental One  ")]


def test_report_requires_key(capsys):
    client = FakeClient()
    cmd = Command(client)

    cmd.do_report("")

    assert "Missing Argument" in capsys.readouterr().out


def test_poll_requires_key(capsys):
    client = FakeClient()
    cmd = Command(client)

    cmd.do_poll("  ")

    assert client.callback is None
    assert "Missing Argument" in capsys.readouterr().out


def test_poll_always_unsubscribes_and_clears_callback(monkeypatch):
    client = FakeClient()
    cmd = Command(client)
    monkeypatch.setattr(builtins, "input", lambda: (_ for _ in ()).throw(EOFError()))

    cmd.do_poll("ALT IAS")

    assert client.subscriptions == ["ALT", "IAS"]
    assert client.unsubscriptions == ["ALT", "IAS"]
    assert client.callback is None


def test_flag_rejects_missing_flag(capsys):
    client = FakeClient()
    cmd = Command(client)

    cmd.do_flag("ALT")

    assert not hasattr(client, "flag_call")
    assert "Missing Argument" in capsys.readouterr().out
