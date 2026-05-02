import logging

import pytest

import fixgw.netfix as netfix


class DoneRunning(Exception):
    pass


class FakeSocket:
    def __init__(self):
        self.sent = []

    def send(self, data):
        self.sent.append(data)


class ScriptedSocket:
    def __init__(self, recv_results=None, connect_error=None):
        self.recv_results = list(recv_results or [])
        self.connect_error = connect_error
        self.closed = False
        self.options = []
        self.timeout = None
        self.connected_to = None

    def setsockopt(self, *args):
        self.options.append(args)

    def settimeout(self, timeout):
        self.timeout = timeout

    def connect(self, addr):
        if self.connect_error is not None:
            raise self.connect_error
        self.connected_to = addr

    def recv(self, _size):
        result = self.recv_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        self.closed = True


class FakeClientThread:
    def __init__(self, responses=None, connected=True):
        self.responses = list(responses or [])
        self.sent = []
        self.connected = connected
        self.started = False
        self.stopped = False
        self.dataCallback = None
        self.connectCallback = None
        self.timeout = None
        self.daemon = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def connectWait(self):
        return self.connected

    def isConnected(self):
        return self.connected

    def send(self, data):
        self.sent.append(data)

    def getResponse(self, command):
        if not self.responses:
            raise netfix.ResponseError("empty")
        actual, payload = self.responses.pop(0)
        assert actual == command
        return [actual, payload]


def make_client(responses=None):
    client = netfix.Client("example.test", 3490)
    client.cthread = FakeClientThread(responses)
    return client


def test_report_parses_metadata_and_aux_fields():
    report = netfix.Report(
        ["ALT", "Altitude", "float", "-1000", "50000", "ft", "500", "low,high"]
    )

    assert report.desc == "Altitude"
    assert report.dtype == "float"
    assert report.min == "-1000"
    assert report.max == "50000"
    assert report.units == "ft"
    assert report.tol == "500"
    assert report.aux == ["low", "high"]
    assert str(report) == "Altitude:ft"


def test_report_handles_empty_aux_fields():
    report = netfix.Report(["ALT", "Altitude", "float", "0", "1", "ft", "100", ""])

    assert report.aux == []


@pytest.mark.parametrize(
    "message, expected",
    [
        ("ALT;1234;10101", ("ALT", "1234", "abs")),
        ("ALT;1234;01010", ("ALT", "1234", "of")),
        ("ALT;1234;11111", ("ALT", "1234", "aobfs")),
        ("IAS;98", ("IAS", "98")),
        ("ALT!001", 1),
    ],
)
def test_decode_data_string(message, expected):
    assert netfix.decodeDataString(message) == expected


def test_client_thread_routes_command_and_data_messages(caplog):
    thread = netfix.ClientThread("example.test", 3490)
    data = []
    thread.dataCallback = data.append

    thread.handle_request("@rALT;1200;00000")
    thread.handle_request("ALT;1200;10101")
    thread.handle_request("IAS;99")
    thread.handle_request("bad;sentence;with;extra")

    assert thread.cmdqueue.get_nowait() == ["r", "ALT;1200;00000"]
    assert data == [
        ["ALT", "1200", "abs"],
        ["IAS", "99"],
        ["bad", "sentence", "with", "extra"],
    ]
    assert "Bad Data Sentence Received" in caplog.text


def test_client_thread_routes_each_data_flag_individually():
    thread = netfix.ClientThread("example.test", 3490)
    data = []
    thread.dataCallback = data.append

    thread.handle_request("ALT;1200;01010")

    assert data == [["ALT", "1200", "of"]]


def test_client_thread_data_message_without_callback_is_ignored():
    thread = netfix.ClientThread("example.test", 3490)

    thread.handle_request("ALT;1200;11111")

    assert thread.cmdqueue.empty()


def test_client_thread_run_handles_receive_data_disconnect_and_reconnect(monkeypatch):
    first_socket = ScriptedSocket([b"@rALT;1200;00000\nALT;99;11111\n", b""])
    sockets = [first_socket]
    data = []
    thread = netfix.ClientThread("example.test", 3490)
    thread.dataCallback = data.append

    monkeypatch.setattr(netfix.socket, "socket", lambda *_args: sockets.pop(0))

    def stop_after_disconnect(_seconds):
        raise DoneRunning()

    monkeypatch.setattr(netfix.time, "sleep", stop_after_disconnect)

    with pytest.raises(DoneRunning):
        thread.run()

    assert first_socket.connected_to == ("example.test", 3490)
    assert thread.cmdqueue.get_nowait() == ["r", "ALT;1200;00000"]
    assert data == [["ALT", "99", "aobfs"]]
    assert not thread.isConnected()


def test_client_thread_run_exits_when_timeout_occurs_after_stop(monkeypatch):
    fake_socket = ScriptedSocket([netfix.socket.timeout()])
    thread = netfix.ClientThread("example.test", 3490)
    thread.stop()

    monkeypatch.setattr(netfix.socket, "socket", lambda *_args: fake_socket)

    thread.run()

    assert fake_socket.closed
    assert not thread.isConnected()


def test_client_thread_run_logs_connection_failures(monkeypatch, caplog):
    fake_socket = ScriptedSocket(connect_error=OSError("refused"))
    thread = netfix.ClientThread("example.test", 3490)
    thread.stop()

    caplog.set_level(logging.DEBUG, logger="fixgw.netfix")
    monkeypatch.setattr(netfix.socket, "socket", lambda *_args: fake_socket)

    thread.run()

    assert "Failed to connect refused" in caplog.text
    assert fake_socket.closed


def test_client_thread_run_logs_receive_failure_and_reconnects(monkeypatch, caplog):
    first_socket = ScriptedSocket([RuntimeError("receive failed")])
    second_socket = ScriptedSocket([netfix.socket.timeout()])
    sockets = [first_socket, second_socket]
    thread = netfix.ClientThread("example.test", 3490)

    caplog.set_level(logging.DEBUG, logger="fixgw.netfix")
    monkeypatch.setattr(netfix.socket, "socket", lambda *_args: sockets.pop(0))

    def stop_before_reconnect(_seconds):
        thread.stop()

    monkeypatch.setattr(netfix.time, "sleep", stop_before_reconnect)

    thread.run()

    assert "Receive Failure receive failed" in caplog.text
    assert "Attempting to Reconnect to example.test:3490" in caplog.text
    assert second_socket.closed


def test_client_thread_run_bad_utf8_uses_legacy_error_path(monkeypatch):
    fake_socket = ScriptedSocket([b"\xff\n"])
    thread = netfix.ClientThread("example.test", 3490)

    monkeypatch.setattr(netfix.socket, "socket", lambda *_args: fake_socket)

    with pytest.raises(AttributeError, match="'ClientThread' object has no attribute 'log'"):
        thread.run()


def test_client_thread_run_logs_handle_request_errors(monkeypatch, caplog):
    fake_socket = ScriptedSocket([b"ALT;1200\n", b""])
    thread = netfix.ClientThread("example.test", 3490)
    thread.dataCallback = lambda _data: (_ for _ in ()).throw(RuntimeError("callback failed"))

    caplog.set_level(logging.ERROR, logger="fixgw.netfix")
    monkeypatch.setattr(netfix.socket, "socket", lambda *_args: fake_socket)

    def stop_after_disconnect(_seconds):
        raise DoneRunning()

    monkeypatch.setattr(netfix.time, "sleep", stop_after_disconnect)

    with pytest.raises(DoneRunning):
        thread.run()

    assert "Error handling request ALT;1200 - callback failed" in caplog.text


def test_client_thread_connection_state_callbacks_and_waits():
    thread = netfix.ClientThread("example.test", 3490)
    states = []
    thread.connectCallback = states.append

    thread.connectedState(True)
    assert thread.connectWait(0)
    assert thread.isConnected()

    thread.connectedState(False)
    assert not thread.connectWait(0)
    assert not thread.isConnected()
    assert states == [True, False]


def test_client_thread_get_response_skips_other_command_responses():
    thread = netfix.ClientThread("example.test", 3490)
    thread.connectedState(True)
    thread.cmdqueue.put(["x", "ignored"])
    thread.cmdqueue.put(["r", "ALT;1200"])

    assert thread.getResponse("r") == ["r", "ALT;1200"]


def test_client_thread_get_response_errors_when_disconnected_or_timed_out():
    thread = netfix.ClientThread("example.test", 3490)

    with pytest.raises(netfix.ResponseError, match="Not Connected"):
        thread.getResponse("r")

    thread.connectedState(True)
    with pytest.raises(netfix.ResponseError, match="Timeout"):
        thread.getResponse("r")


def test_client_thread_send_requires_connection():
    thread = netfix.ClientThread("example.test", 3490)

    with pytest.raises(netfix.NotConnectedError):
        thread.send(b"@rALT\n")

    thread.connectedState(True)
    thread.s = FakeSocket()
    thread.send(b"@rALT\n")
    assert thread.s.sent == [b"@rALT\n"]


def test_client_connect_disconnect_and_callbacks():
    client = make_client()
    data_callback = object()
    connect_callback = object()

    assert client.connect()
    assert client.cthread.started
    assert client.isConnected()

    client.setDataCallback(data_callback)
    client.setConnectCallback(connect_callback)
    assert client.cthread.dataCallback is data_callback
    assert client.cthread.connectCallback is connect_callback

    client.clearDataCallback()
    client.clearConnectCallback()
    assert client.cthread.dataCallback is None
    assert client.cthread.connectCallback is None

    client.disconnect()
    assert client.cthread.stopped


def test_client_sends_protocol_commands_and_decodes_responses():
    client = make_client(
        [
            ("l", "0;2;ALT,IAS"),
            ("l", "done"),
            ("q", "ALT;Altitude;float;0;50000;ft;100;"),
            ("r", "ALT;1200;10101"),
            ("s", "ALT"),
            ("u", "ALT"),
            ("f", "ALT"),
            ("w", "ALT;1300;00000"),
            ("x", "status:ready"),
            ("x", "kill"),
        ]
    )

    assert client.getList() == ["ALT", "IAS"]
    assert client.getReport("ALT") == [
        "ALT",
        "Altitude",
        "float",
        "0",
        "50000",
        "ft",
        "100",
        "",
    ]
    assert client.read("ALT") == ("ALT", "1200", "abs")
    client.write("ALT", 1300, "abs")
    client.subscribe("ALT")
    client.unsubscribe("ALT")
    client.flag("ALT", "A", True)
    assert client.writeValue("ALT", 1300) == "ALT;1300;00000"
    assert client.getStatus() == "ready"
    client.stop()

    assert client.cthread.sent == [
        b"@l<built-in function id>\n",
        b"@qALT\n",
        b"@rALT\n",
        b"ALT;1300;1101\n",
        b"@sALT\n",
        b"@uALT\n",
        b"@fALT;a;1\n",
        b"@wALT;1300\n",
        b"@xstatus\n",
        b"@xkill\n",
    ]


@pytest.mark.parametrize(
    "payload, message",
    [
        ("ALT!001", "Key Not Found ALT"),
        ("ALT!999", "Response Error 999 for ALT"),
    ],
)
def test_client_get_report_raises_response_errors(payload, message):
    client = make_client([("q", payload)])

    with pytest.raises(netfix.ResponseError, match=message):
        client.getReport("ALT")


@pytest.mark.parametrize(
    "payload, message",
    [
        ("ALT!001", "Key Not Found ALT"),
        ("ALT!002", "Unknown Flag a"),
        ("ALT!999", "Response Error 999 for ALT"),
    ],
)
def test_client_flag_raises_response_errors(payload, message):
    client = make_client([("f", payload)])

    with pytest.raises(netfix.ResponseError, match=message):
        client.flag("ALT", "a", False)
