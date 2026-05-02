from dataclasses import dataclass

import pytest

import fixgw.netfix.db as netfixdb


class FakeClient:
    def __init__(self, connected=False):
        self.connected = connected
        self.write_values = []
        self.flags = []
        self.subscriptions = []
        self.unsubscriptions = []
        self.connect_callback = None
        self.data_callback = None
        self.list_response = []
        self.reports = {}
        self.reads = {}
        self.write_responses = {}
        self.flag_error = None

    def isConnected(self):
        return self.connected

    def setConnectCallback(self, callback):
        self.connect_callback = callback

    def setDataCallback(self, callback):
        self.data_callback = callback

    def writeValue(self, key, value):
        self.write_values.append((key, value))
        if key in self.write_responses:
            return self.write_responses[key]
        return f"{key};{value};00000"

    def flag(self, key, flag, setting):
        if self.flag_error is not None:
            raise self.flag_error
        self.flags.append((key, flag, setting))

    def getList(self):
        return self.list_response

    def getReport(self, key):
        return self.reports[key]

    def read(self, key):
        return self.reads[key]

    def subscribe(self, key):
        self.subscriptions.append(key)

    def unsubscribe(self, key):
        self.unsubscriptions.append(key)


@dataclass
class Report:
    desc: str = "Altitude"
    dtype: str = "float"
    min: str = "0"
    max: str = "50000"
    units: str = "ft"
    tol: str = "100"
    aux: tuple = ()


class DummyTimer:
    def __init__(self, function):
        self.function = function
        self.started = False
        self.stopped = False
        self.joined = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def join(self):
        self.joined = True


def test_db_item_rejects_null_key_and_unknown_dtype():
    client = FakeClient()

    with pytest.raises(ValueError, match="Null Item"):
        netfixdb.DB_Item(client, None)

    with pytest.raises(KeyError):
        netfixdb.DB_Item(client, "ALT", "unknown")


def test_db_item_aux_values_are_sorted_converted_written_and_reported():
    client = FakeClient()
    item = netfixdb.DB_Item(client, "ALT", "float")
    events = []
    item.auxChanged = lambda name, value: events.append((name, value))

    item.init_aux(["high", "", "low"])
    assert item.get_aux_list() == ["high", "low"]

    item.set_aux_value("low", "12.5")
    item.set_aux_value("high", "None")
    assert item.get_aux_value("low") == 12.5
    assert item.get_aux_value("high") is None
    assert events == [("low", "12.5")]
    assert client.write_values == [("ALT.low", 12.5)]

    with pytest.raises(KeyError):
        item.get_aux_value("missing")
    with pytest.raises(ValueError):
        item.set_aux_value("low", "bad-float")


def test_db_item_aux_server_error_returns_after_callback():
    client = FakeClient()
    client.write_responses["ALT.low"] = "ALT.low!003"
    item = netfixdb.DB_Item(client, "ALT", "float")
    item.init_aux(["low"])
    events = []
    item.auxChanged = lambda name, value: events.append((name, value))

    item.set_aux_value("low", "12")

    assert item.get_aux_value("low") == 12.0
    assert events == [("low", "12")]
    assert client.write_values == [("ALT.low", 12.0)]


def test_db_item_value_conversion_bounds_callbacks_and_server_flags():
    client = FakeClient()
    item = netfixdb.DB_Item(client, "ALT", "float")
    item.description = "Altitude"
    item.min = "10"
    item.max = "100"
    changed = []
    written = []
    item.valueChanged = changed.append
    item.valueWrite = written.append

    item.value = "250"

    assert item.value == 100.0
    assert changed == [100.0]
    assert written == [100.0]
    assert client.write_values == [("ALT", 100.0)]

    item.value = "-5"
    assert item.value == 10.0
    assert changed[-1] == 10.0
    assert written[-1] == 10.0


def test_db_item_value_uses_server_normalized_value_and_flags():
    client = FakeClient()
    client.write_responses["ALT"] = "ALT;75;10101"
    item = netfixdb.DB_Item(client, "ALT", "float")
    changed = []
    item.valueChanged = changed.append

    item.value = "70"

    assert item.value == 75.0
    assert changed == [70.0, 70.0]
    assert item.annunciate is True
    assert item.old is False
    assert item.bad is True
    assert item.fail is False
    assert item.secFail is True


def test_db_item_value_server_error_leaves_local_value():
    client = FakeClient()
    client.write_responses["ALT"] = "ALT!003"
    item = netfixdb.DB_Item(client, "ALT", "float")

    item.value = "44"

    assert item.value == 44.0


def test_db_item_bool_conversion_and_flag_writes():
    client = FakeClient()
    item = netfixdb.DB_Item(client, "SWITCH", "bool")
    events = []
    item.annunciateChanged = lambda value: events.append(("a", value))
    item.oldChanged = lambda value: events.append(("o", value))
    item.badChanged = lambda value: events.append(("b", value))
    item.failChanged = lambda value: events.append(("f", value))
    item.secFailChanged = lambda value: events.append(("s", value))

    item.value = "yes"
    events.clear()
    client.flags.clear()
    item.annunciate = "true"
    item.old = "1"
    item.bad = "false"
    item.fail = 0
    item.secFail = 1

    assert item.value is True
    assert item.annunciate is True
    assert item.old is True
    assert item.bad is False
    assert item.fail is False
    assert item.secFail is True
    assert events == [("a", True), ("o", True), ("s", True)]
    assert client.flags == [
        ("SWITCH", "a", True),
        ("SWITCH", "o", True),
        ("SWITCH", "s", True),
    ]


def test_db_item_bool_conversion_accepts_bool_and_non_string_values():
    client = FakeClient()
    item = netfixdb.DB_Item(client, "SWITCH", "bool")

    item.value = True
    assert item.value is True
    item.value = 0
    assert item.value is False


def test_db_item_string_values_skip_numeric_bounds():
    client = FakeClient()
    item = netfixdb.DB_Item(client, "LABEL", "str")

    item.value = "hello"

    assert item.value == "hello"


def test_db_item_invalid_property_inputs_are_logged(caplog):
    client = FakeClient()
    item = netfixdb.DB_Item(client, "ALT", "float")
    item.description = "Altitude"

    item.min = "bad"
    item.max = "bad"
    item.tol = "bad"

    assert "Bad minimum value 'bad' given for Altitude" in caplog.text
    assert "Bad maximum value 'bad' given for Altitude" in caplog.text
    assert "Time to live should be an integer for Altitude" in caplog.text


@pytest.mark.parametrize(
    "attr, flag",
    [
        ("annunciate", "a"),
        ("old", "o"),
        ("bad", "b"),
        ("fail", "f"),
        ("secFail", "s"),
    ],
)
def test_db_item_flag_write_errors_are_logged(attr, flag, caplog):
    client = FakeClient()
    client.flag_error = RuntimeError(f"{flag} boom")
    item = netfixdb.DB_Item(client, "ALT", "float")

    setattr(item, attr, not getattr(item, attr))

    assert f"{flag} boom" in caplog.text


def test_db_item_update_no_write_updates_value_and_flags_without_client_calls():
    client = FakeClient()
    item = netfixdb.DB_Item(client, "ALT", "float")
    item.updateNoWrite(["ALT", "12.5", "aos"])

    assert item.value == 12.5
    assert item.annunciate is True
    assert item.old is True
    assert item.bad is False
    assert item.fail is False
    assert item.secFail is True
    assert client.write_values == []
    assert client.flags == []
    assert item.supressWrite is False


def test_db_item_update_no_write_restores_suppress_write_after_error():
    client = FakeClient()
    item = netfixdb.DB_Item(client, "ALT", "float")

    with pytest.raises(IndexError):
        item.updateNoWrite(["ALT"])

    assert item.supressWrite is False


def test_db_item_str_and_age():
    item = netfixdb.DB_Item(FakeClient(), "ALT", "float")
    item.supressWrite = True
    item.value = 12
    item.supressWrite = False

    assert str(item) == "ALT = 12.0"
    assert item.age >= 0


def test_update_thread_runs_until_stopped(monkeypatch):
    calls = []
    thread = netfixdb.UpdateThread(lambda: calls.append("tick"), interval=0.01)

    def fake_sleep(_interval):
        thread.stop()

    monkeypatch.setattr(netfixdb.time, "sleep", fake_sleep)

    thread.run()

    assert calls == ["tick"]
    assert thread.getout is True


def test_database_initializes_defines_items_and_reads_aux(monkeypatch):
    monkeypatch.setattr(netfixdb, "UpdateThread", DummyTimer)
    client = FakeClient(connected=True)
    client.list_response = ["ALT"]
    client.reports = {
        "ALT": ["ALT", "Altitude", "float", "0", "50000", "deg", "250", "low,high"],
    }
    client.reads = {
        "ALT": ("ALT", "1234.5", "ab"),
        "ALT.low": ("ALT.low", "100"),
        "ALT.high": ("ALT.high", "200"),
    }

    database = netfixdb.Database(client)

    assert database.connected is True
    assert database.init_event.is_set()
    assert database.get_item_list() == ["ALT"]
    item = database.get_item("ALT")
    assert item.description == "Altitude"
    assert item.units == "°"
    assert item.tol == 250
    assert item.value == 1234.5
    assert item.annunciate is True
    assert item.bad is True
    assert item.get_aux_value("low") == 100.0
    assert item.get_aux_value("high") == 200.0
    assert client.subscriptions == ["ALT"]

    database.stop()
    assert database.timer.stopped
    assert database.timer.joined


def test_database_data_function_updates_values_and_aux_without_writes(monkeypatch):
    monkeypatch.setattr(netfixdb, "UpdateThread", DummyTimer)
    client = FakeClient()
    database = netfixdb.Database(client)
    item = database.get_item("ALT", create=True, wait=False)
    item.init_aux(["low"])

    database.dataFunction(["ALT", "88.5", "fs"])
    database.dataFunction(["ALT.low", "77.5"])

    assert item.value == 88.5
    assert item.fail is True
    assert item.secFail is True
    assert item.get_aux_value("low") == 77.5
    assert client.write_values == []
    assert client.flags == []


def test_database_update_initializes_on_connect_and_deletes_on_disconnect(monkeypatch):
    monkeypatch.setattr(netfixdb, "UpdateThread", DummyTimer)
    client = FakeClient()
    database = netfixdb.Database(client)
    database.initialize = lambda: database.get_item("ALT", create=True, wait=False)

    database.connectFunction(True)
    database.update()
    item = database.get_item("ALT", wait=False)
    destroyed = []
    item.destroyed = lambda: destroyed.append("ALT")

    database.connectFunction(False)
    database.update()

    assert destroyed == ["ALT"]
    assert client.unsubscriptions == ["ALT"]
    assert database.get_item_list() == []


def test_database_connect_callback_and_idle_update(monkeypatch):
    monkeypatch.setattr(netfixdb, "UpdateThread", DummyTimer)
    client = FakeClient()
    database = netfixdb.Database(client)
    states = []
    database.connectCallback = states.append

    database.connectFunction(True)
    database.update()

    assert states == [True]


def test_database_update_ignores_unsubscribe_errors(monkeypatch):
    monkeypatch.setattr(netfixdb, "UpdateThread", DummyTimer)
    client = FakeClient()
    client.unsubscribe = lambda key: (_ for _ in ()).throw(RuntimeError("down"))
    database = netfixdb.Database(client)
    item = database.get_item("ALT", create=True, wait=False)
    destroyed = []
    item.destroyed = lambda: destroyed.append(True)

    database.connectFunction(False)
    database.update()

    assert destroyed == [True]
    assert database.get_item_list() == []


def test_database_initialize_existing_items_warns(monkeypatch, caplog):
    monkeypatch.setattr(netfixdb, "UpdateThread", DummyTimer)
    database = netfixdb.Database(FakeClient())
    database.get_item("ALT", create=True, wait=False)

    database.initialize()

    assert "Trying to initialize an already initialized database" in caplog.text


def test_database_initialize_logs_and_reraises_errors(monkeypatch, caplog):
    monkeypatch.setattr(netfixdb, "UpdateThread", DummyTimer)
    client = FakeClient()
    client.getList = lambda: (_ for _ in ()).throw(RuntimeError("list failed"))
    database = netfixdb.Database(client)

    with pytest.raises(RuntimeError, match="list failed"):
        database.initialize()

    assert "list failed" in caplog.text


def test_database_define_item_redefines_existing_item_and_reports(monkeypatch):
    monkeypatch.setattr(netfixdb, "UpdateThread", DummyTimer)
    client = FakeClient()
    client.reads = {
        "ALT": ("ALT", "1000"),
        "ALT.low": ("ALT.low", "10"),
    }
    database = netfixdb.Database(client)
    item = database.get_item("ALT", create=True, wait=False)
    reports = []
    item.reportReceived = lambda: reports.append(True)

    result = database.define_item("ALT", Report(aux=("low",)))

    assert result is item
    assert reports == [True]
    assert client.subscriptions == ["ALT"]


def test_database_get_item_missing_without_create_raises(monkeypatch):
    monkeypatch.setattr(netfixdb, "UpdateThread", DummyTimer)
    database = netfixdb.Database(FakeClient())

    with pytest.raises(KeyError):
        database.get_item("MISSING", wait=False)


def test_database_helpers_set_get_and_mark_all_fail(monkeypatch):
    monkeypatch.setattr(netfixdb, "UpdateThread", DummyTimer)
    client = FakeClient()
    database = netfixdb.Database(client)
    database.get_item("ALT", create=True, wait=False)

    database.set_value("ALT", 77)
    assert database.get_value("ALT") == 77.0

    database.mark_all_fail()
    assert database.get_item("ALT", wait=False).fail is True
