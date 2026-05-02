from collections import deque
from types import SimpleNamespace

import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.netfix as netfix_plugin


class FakeLog:
    def __init__(self):
        self.debug_messages = []
        self.info_messages = []

    def debug(self, message):
        self.debug_messages.append(message)

    def info(self, message):
        self.info_messages.append(message)


class FakeItem:
    description = "Altitude"
    typestring = "float"
    min = -1000.0
    max = 60000.0
    units = "ft"
    tol = 2000

    def __init__(self, aux=None):
        self.aux = aux or []
        self.annunciate = False
        self.old = False
        self.bad = False
        self.fail = False
        self.secfail = False


class FakeParent:
    def __init__(self):
        self.config = {"buffer_size": 64}
        self.log = FakeLog()
        self.item = FakeItem(["Min", "Max"])
        self.reads = {"ALT": (123.0, False, False, False, False, False)}
        self.writes = []
        self.callbacks_added = []
        self.callbacks_deleted = []
        self.quit_called = False

    def db_get_item(self, key):
        if key == "MISSING":
            raise KeyError(key)
        if key == "NONE":
            return None
        return self.item

    def db_read(self, key):
        try:
            return self.reads[key]
        except KeyError:
            raise KeyError(key)

    def db_write(self, key, value):
        if key == "MISSING":
            raise KeyError(key)
        if value == "bad":
            raise ValueError(value)
        self.writes.append((key, value))

    def db_list(self):
        return ["ALT", "IAS", "AOA", "BARO"]

    def db_callback_add(self, key, function, udata=None):
        if key == "MISSING":
            raise KeyError(key)
        self.callbacks_added.append((key, function, udata))

    def db_callback_del(self, key, function, udata=None):
        if key == "MISSING":
            raise KeyError(key)
        self.callbacks_deleted.append((key, function, udata))

    def quit(self):
        self.quit_called = True


class FakeSocket:
    def __init__(self, recv_values=None):
        self.recv_values = deque(recv_values or [])
        self.sent = []
        self.closed = False
        self.shutdown_calls = []

    def recv(self, _size):
        value = self.recv_values.popleft()
        if isinstance(value, Exception):
            raise value
        return value

    def sendall(self, data):
        self.sent.append(data)

    def shutdown(self, how):
        self.shutdown_calls.append(how)

    def close(self):
        self.closed = True


def make_connection(parent=None):
    parent = parent or FakeParent()
    return netfix_plugin.Connection(parent, FakeSocket(), ("10.0.0.1", 12345))


def drain_queue(connection):
    values = []
    while not connection.queue.empty():
        values.append(connection.queue.get())
    return values


def test_query_command_reports_item_metadata_and_missing_items():
    connection = make_connection()

    connection.handle_request("@qALT")
    connection.handle_request("@qMISSING")
    connection.handle_request("@qNONE")

    assert drain_queue(connection) == [
        b"@qALT;Altitude;float;-1000.0;60000.0;ft;2000;Min,Max\n",
        b"@qMISSING!001\n",
        b"@qNONE!001\n",
    ]


def test_server_specific_commands_return_status_kill_and_errors(monkeypatch):
    parent = FakeParent()
    connection = make_connection(parent)
    monkeypatch.setattr(netfix_plugin.status, "get_dict", lambda: {"ok": True})

    connection.handle_request("@xstatus")
    connection.handle_request("@xkill")
    connection.handle_request("@xwat")

    assert drain_queue(connection) == [
        b'@xstatus;{"ok": true}\n',
        b"@xkill\n",
        b"@xwat!001",
    ]
    assert parent.quit_called is True


@pytest.mark.parametrize(
    "flag,attribute",
    [
        ("a", "annunciate"),
        ("o", "old"),
        ("b", "bad"),
        ("f", "fail"),
        ("s", "secfail"),
    ],
)
def test_flag_command_sets_and_clears_each_flag(flag, attribute):
    parent = FakeParent()
    connection = make_connection(parent)

    connection.handle_request(f"@fALT;{flag};1")
    connection.handle_request(f"@fALT;{flag};0")

    assert getattr(parent.item, attribute) is False
    assert drain_queue(connection) == [
        f"@fALT;{flag};1\n".encode(),
        f"@fALT;{flag};0\n".encode(),
    ]


def test_flag_command_reports_bad_key_flag_and_value():
    connection = make_connection()

    connection.handle_request("@fMISSING;a;1")
    connection.handle_request("@fALT;x;1")
    connection.handle_request("@fALT;a;2")

    assert drain_queue(connection) == [b"@fM!001\n", b"@fA!002\n", b"@fA!003\n"]


def test_list_command_splits_responses_when_buffer_is_small():
    parent = FakeParent()
    parent.config["buffer_size"] = 24
    connection = make_connection(parent)

    connection.handle_request("@l")

    assert drain_queue(connection) == [
        b"@l4;0;ALT\n",
        b"@l4;1;IAS\n",
        b"@l4;2;AOA\n",
        b"@l4;3;BARO\n",
    ]


def test_unknown_command_returns_protocol_error():
    connection = make_connection()

    connection.handle_request("@zALT")

    assert drain_queue(connection) == [b"@zALT!004\n"]


def test_value_update_sets_false_flags_and_logs_bad_frames():
    parent = FakeParent()
    parent.item.annunciate = True
    parent.item.bad = True
    parent.item.fail = True
    parent.item.secfail = True
    connection = make_connection(parent)

    connection.handle_request("ALT;321;000")
    connection.handle_request("bad-frame")

    assert parent.writes == [("ALT", "321")]
    assert parent.item.annunciate is False
    assert parent.item.bad is False
    assert parent.item.fail is False
    assert parent.item.secfail is False
    assert netfix_plugin.client_block["10.0.0.1"] == {"ALT"}
    assert parent.log.debug_messages


def test_subscription_handler_suppresses_one_inhibited_update_then_sends_values():
    connection = make_connection()
    connection.output_inhibit = True

    connection.subscription_handler("ALT", (1.0, True, False, True, False, True), None)
    connection.subscription_handler("IAS", 99.0, None)

    assert drain_queue(connection) == [b"IAS;99.0\n"]


def test_receive_thread_handles_recv_exception_and_cleans_up():
    parent = FakeParent()
    parent.thread = SimpleNamespace(buffer_size=32)
    connection = netfix_plugin.Connection(parent, FakeSocket([RuntimeError("boom")]), ("host", 7))
    thread = netfix_plugin.ReceiveThread(connection)

    thread.run()

    assert connection.queue.get() == "exit"
    assert parent.callbacks_deleted == [("*", connection.subscription_handler, None)]
    assert connection.conn.closed is True
    assert thread.running is False


def test_receive_thread_stop_logs_shutdown_errors():
    parent = FakeParent()
    parent.thread = SimpleNamespace(buffer_size=32)
    sock = FakeSocket()

    def fail_shutdown(_how):
        raise OSError("closed")

    sock.shutdown = fail_shutdown
    thread = netfix_plugin.ReceiveThread(
        netfix_plugin.Connection(parent, sock, ("host", 7))
    )

    thread.stop()

    assert thread.getout is True
    assert "Problem shutting down connection" in parent.log.debug_messages[0]


def test_send_thread_sends_until_exit_and_closes_socket():
    connection = make_connection()
    connection.queue.put(b"one")
    connection.queue.put(b"two")
    connection.queue.put("exit")
    thread = netfix_plugin.SendThread(connection)

    thread.run()

    assert connection.conn.sent == [b"one", b"two"]
    assert thread.msg_sent == 2
    assert thread.running is False
    assert connection.conn.closed is True


class FakeNetfixClient:
    instances = []

    def __init__(self, host, port):
        self.cthread = SimpleNamespace(host=host)
        self.host = host
        self.port = port
        self.isConnected = True
        self.writes = []
        self.disconnect_called = False
        FakeNetfixClient.instances.append(self)

    def connect(self):
        self.connected = True

    def writeValue(self, key, value):
        if value == "retry":
            raise RuntimeError("retry")
        self.writes.append((key, value))

    def disconnect(self):
        self.disconnect_called = True


class FakeClientParent:
    def __init__(self):
        self.log = FakeLog()
        self.config = {
            "clients": [{"host": "peer-a", "port": 4000}, {"host": "peer-b"}],
            "outputs": ["alt"],
        }
        self.callbacks_added = []
        self.reads = {"ALT": (55.0, False, False, False, False, False)}

    def db_callback_add(self, key, function):
        self.callbacks_added.append((key, function))

    def db_read(self, key):
        return self.reads[key]


def test_client_thread_initializes_clients_callbacks_status_and_stop(monkeypatch):
    FakeNetfixClient.instances = []
    monkeypatch.setattr(netfix_plugin.netfix, "Client", FakeNetfixClient)
    parent = FakeClientParent()

    thread = netfix_plugin.ClientThread(parent)
    FakeNetfixClient.instances[1].isConnected = False
    thread.stop()

    assert [(c.host, c.port) for c in thread.clients] == [
        ("peer-a", 4000),
        ("peer-b", 3490),
    ]
    assert parent.callbacks_added[0][0] == "ALT"
    assert thread.get_status() == {
        "Current Clients": 2,
        "Connected": 1,
        "Disonnected": 1,
    }
    assert [c.disconnect_called for c in thread.clients] == [True, True]


def test_client_output_callback_queues_unique_value_only_updates(monkeypatch):
    monkeypatch.setattr(netfix_plugin.netfix, "Client", FakeNetfixClient)
    thread = netfix_plugin.ClientThread(FakeClientParent())
    callback = thread.getOutputFunction("ALT")

    callback("ALT", (1.0, False, False, False, False, False), None)
    callback("ALT", (2.0, False, False, False, False, False), None)
    callback("ALT", (3.0, True, False, False, False, False), None)

    assert list(thread.queue) == ["ALT"]


def test_client_thread_run_writes_unblocked_keys_and_requeues_failures(monkeypatch):
    monkeypatch.setattr(netfix_plugin.netfix, "Client", FakeNetfixClient)
    parent = FakeClientParent()
    parent.reads["ALT"] = (55.0, False, False, False, False, False)
    thread = netfix_plugin.ClientThread(parent)
    thread.queue.append("ALT")
    netfix_plugin.client_block["peer-b"].add("ALT")

    sleeps = []

    def fake_sleep(duration):
        sleeps.append(duration)
        thread.getout = True

    monkeypatch.setattr(netfix_plugin.time, "sleep", fake_sleep)

    thread.run()

    assert thread.clients[0].writes == [("ALT", 55.0)]
    assert thread.clients[1].writes == []
    assert "ALT" not in netfix_plugin.client_block["peer-b"]


def test_client_thread_run_requeues_failed_writes_once(monkeypatch):
    monkeypatch.setattr(netfix_plugin.netfix, "Client", FakeNetfixClient)
    parent = FakeClientParent()
    parent.reads["ALT"] = ("retry", False, False, False, False, False)
    thread = netfix_plugin.ClientThread(parent)
    thread.queue.append("ALT")
    sleep_calls = 0

    def fake_sleep(_duration):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls > 1:
            thread.queue.clear()
            thread.getout = True

    monkeypatch.setattr(netfix_plugin.time, "sleep", fake_sleep)

    thread.run()

    assert sleep_calls >= 2


def test_plugin_lifecycle_for_client_server_both_and_invalid_types(monkeypatch):
    events = []

    class FakeThread:
        def __init__(self, parent):
            self.parent = parent
            self.alive = False

        def start(self):
            events.append(("start", type(self).__name__))

        def stop(self):
            events.append(("stop", type(self).__name__))

        def is_alive(self):
            return self.alive

        def join(self, timeout=None):
            events.append(("join", type(self).__name__, timeout))

        def get_status(self):
            return {"thread": type(self).__name__}

    class AliveThread(FakeThread):
        def stop(self):
            super().stop()
            self.alive = True

    monkeypatch.setattr(netfix_plugin, "ServerThread", FakeThread)
    monkeypatch.setattr(netfix_plugin, "ClientThread", FakeThread)

    server = netfix_plugin.Plugin("netfix", {"type": "server"}, {})
    assert server.get_status() == {"thread": "FakeThread"}
    server.run()
    server.stop()

    client = netfix_plugin.Plugin("netfix", {"type": "client"}, {})
    client.client.alive = True
    client.run()
    client.stop()

    both = netfix_plugin.Plugin("netfix", {"type": "both"}, {})
    both.run()
    both.stop()

    with pytest.raises(ValueError):
        netfix_plugin.Plugin("netfix", {"type": "wat"}, {})

    monkeypatch.setattr(netfix_plugin, "ServerThread", AliveThread)
    failing = netfix_plugin.Plugin("netfix", {"type": "server"}, {})
    with pytest.raises(plugin_base.PluginFail):
        failing.stop()

    assert ("start", "FakeThread") in events
