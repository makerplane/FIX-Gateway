import logging

import fixgw.client as client_main


class FakeNetfixClient:
    instances = []

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.connected = False
        self.disconnected = False
        FakeNetfixClient.instances.append(self)

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.disconnected = True


class FakeCommand:
    instances = []

    def __init__(self, client):
        self.client = client
        self.commands = []
        self.looped = False
        self.prompt = None
        FakeCommand.instances.append(self)

    def onecmd(self, command):
        self.commands.append(command)
        return command == "quit"

    def cmdloop(self):
        self.looped = True


def install_fakes(monkeypatch):
    FakeNetfixClient.instances = []
    FakeCommand.instances = []
    monkeypatch.setattr(client_main.netfix, "Client", FakeNetfixClient)
    monkeypatch.setattr(client_main.command, "Command", FakeCommand)
    monkeypatch.setattr(client_main.sys.stdin, "isatty", lambda: True)


def test_execute_disconnects_without_starting_interactive_loop(monkeypatch):
    install_fakes(monkeypatch)
    monkeypatch.setattr(client_main.sys, "argv", ["fixgwc", "-x", "read", "ALT"])

    result = client_main.main()

    assert result == 0
    assert FakeCommand.instances[0].commands == ["read ALT"]
    assert not FakeCommand.instances[0].looped
    assert FakeNetfixClient.instances[0].connected
    assert FakeNetfixClient.instances[0].disconnected


def test_file_commands_are_executed_and_disconnect(tmp_path, monkeypatch):
    install_fakes(monkeypatch)
    commands = tmp_path / "commands.fixgwc"
    commands.write_text("read ALT\n\nwrite ALT 123\n", encoding="utf-8")
    monkeypatch.setattr(client_main.sys, "argv", ["fixgwc", "-f", str(commands)])

    result = client_main.main()

    assert result == 0
    assert FakeCommand.instances[0].commands == ["read ALT", "write ALT 123"]
    assert FakeNetfixClient.instances[0].disconnected


def test_interactive_execute_continues_to_cmdloop(monkeypatch):
    install_fakes(monkeypatch)
    monkeypatch.setattr(
        client_main.sys, "argv", ["fixgwc", "-x", "read", "ALT", "--interactive"]
    )

    result = client_main.main()

    assert result == 0
    assert FakeCommand.instances[0].commands == ["read ALT"]
    assert FakeCommand.instances[0].looped
    assert FakeNetfixClient.instances[0].disconnected


def test_debug_sets_root_logger_level(monkeypatch):
    install_fakes(monkeypatch)
    monkeypatch.setattr(client_main.sys, "argv", ["fixgwc", "--debug", "-x", "quit"])
    logging.getLogger().setLevel(logging.WARNING)

    client_main.main()

    assert logging.getLogger().level == logging.DEBUG
