import pytest

pytest.importorskip("PyQt6")

import fixgw.netfix.QtDb as qtdb


class PlainItem:
    def __init__(self):
        self.valueChanged = None
        self.valueWrite = None
        self.annunciateChanged = None
        self.oldChanged = None
        self.badChanged = None
        self.failChanged = None
        self.secFailChanged = None
        self.auxChanged = None
        self.reportReceived = None
        self.destroyed = None
        self.description = "Altitude"
        self.value = 10
        self.dtype = float
        self.typestring = "float"
        self.units = "ft"
        self.min = 0
        self.max = 50000
        self.tol = 100
        self.annunciate = False
        self.old = False
        self.bad = False
        self.fail = False
        self.secFail = False
        self.age = 12.5
        self.aux = {"low": 1.0}

    def get_aux_list(self):
        return sorted(self.aux)

    def set_aux_value(self, name, value):
        self.aux[name] = value

    def get_aux_value(self, name):
        return self.aux[name]


class FakeInnerDatabase:
    def __init__(self, connected=True):
        self.connected = connected
        self.item = PlainItem()
        self.values = {}

    def get_item_list(self):
        return ["ALT"]

    def get_item(self, key):
        assert key == "ALT"
        return self.item


def test_qt_item_forwards_core_properties_and_aux_values():
    item = PlainItem()
    qt_item = qtdb.QtDB_Item("ALT", item)

    assert qt_item.key == "ALT"
    assert qt_item.description == "Altitude"
    assert qt_item.value == 10
    assert qt_item.dtype is float
    assert qt_item.typestring == "float"
    assert qt_item.units == "ft"
    assert qt_item.min == 0
    assert qt_item.max == 50000
    assert qt_item.tol == 100
    assert qt_item.age == 12.5
    assert qt_item.annunciate is False
    assert qt_item.old is False
    assert qt_item.bad is False
    assert qt_item.fail is False
    assert qt_item.secFail is False
    assert qt_item.get_aux_list() == ["low"]
    assert qt_item.get_aux_value("low") == 1.0

    qt_item.value = 25
    qt_item.annunciate = True
    qt_item.old = True
    qt_item.bad = True
    qt_item.fail = True
    qt_item.secFail = True
    qt_item.set_aux_value("high", 99)

    assert item.value == 25
    assert item.annunciate is True
    assert item.old is True
    assert item.bad is True
    assert item.fail is True
    assert item.secFail is True
    assert item.aux["high"] == 99


def test_qt_item_str_uses_cached_value_attribute():
    qt_item = qtdb.QtDB_Item("ALT", PlainItem())
    qt_item._value = 123

    assert str(qt_item) == "ALT = 123"


def test_qt_item_emits_signals_from_core_callbacks(qtbot):
    item = PlainItem()
    qt_item = qtdb.QtDB_Item("ALT", item)

    with qtbot.waitSignal(qt_item.valueChanged) as blocker:
        item.valueChanged(11)
    assert blocker.args == [11]

    with qtbot.waitSignal(qt_item.valueWrite) as blocker:
        item.valueWrite(12)
    assert blocker.args == [12]

    with qtbot.waitSignal(qt_item.annunciateChanged) as blocker:
        item.annunciateChanged(True)
    assert blocker.args == [True]

    with qtbot.waitSignal(qt_item.oldChanged) as blocker:
        item.oldChanged(True)
    assert blocker.args == [True]

    with qtbot.waitSignal(qt_item.badChanged) as blocker:
        item.badChanged(True)
    assert blocker.args == [True]

    with qtbot.waitSignal(qt_item.failChanged) as blocker:
        item.failChanged(True)
    assert blocker.args == [True]

    with qtbot.waitSignal(qt_item.secFailChanged) as blocker:
        item.secFailChanged(True)
    assert blocker.args == [True]

    with qtbot.waitSignal(qt_item.auxChanged) as blocker:
        item.auxChanged("low", 2.0)
    assert blocker.args == ["low", 2.0]

    with qtbot.waitSignal(qt_item.reportReceived) as blocker:
        item.reportReceived(True)
    assert blocker.args == [True]

    with qtbot.waitSignal(qt_item.destroyed):
        item.destroyed()


def test_qt_item_rejects_null_key():
    with pytest.raises(ValueError, match="Null Item"):
        qtdb.QtDB_Item(None, PlainItem())


def test_qt_database_initializes_and_forwards_value_access(monkeypatch):
    inner = FakeInnerDatabase(connected=True)
    monkeypatch.setattr(qtdb.fixgw.netfix.db, "Database", lambda client: inner)

    database = qtdb.Database(client=object())

    assert database.get_item_list() == ["ALT"]
    assert database.get_item("ALT").key == "ALT"
    assert database.get_value("ALT") == 10
    database.set_value("ALT", 42)
    assert inner.item.value == 42


def test_qt_database_connect_function_rebuilds_after_disconnect(monkeypatch):
    inner = FakeInnerDatabase(connected=False)
    monkeypatch.setattr(qtdb.fixgw.netfix.db, "Database", lambda client: inner)
    database = qtdb.Database(client=object())
    assert database.get_item_list() == []

    database.connectFunction(False)
    assert database.get_item_list() == ["ALT"]

    database.connectFunction(True)
    assert database.get_item_list() == []


def test_qt_database_initialize_warns_when_already_initialized(monkeypatch, caplog):
    inner = FakeInnerDatabase(connected=True)
    monkeypatch.setattr(qtdb.fixgw.netfix.db, "Database", lambda client: inner)
    database = qtdb.Database(client=object())

    database.initialize()

    assert "Trying to initialize an already initialized database" in caplog.text


def test_qt_database_initialize_logs_inner_database_errors(monkeypatch, caplog):
    class FailingInnerDatabase(FakeInnerDatabase):
        def get_item(self, key):
            raise RuntimeError(f"{key} failed")

    inner = FailingInnerDatabase(connected=False)
    monkeypatch.setattr(qtdb.fixgw.netfix.db, "Database", lambda client: inner)
    database = qtdb.Database(client=object())

    database.initialize()

    assert "ALT failed" in caplog.text
