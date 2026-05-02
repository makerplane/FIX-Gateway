from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QCheckBox

from fixgw.client import connection, dbItemDialog


class FakeItem(QObject):
    valueChanged = pyqtSignal(object)
    annunciateChanged = pyqtSignal(bool)
    oldChanged = pyqtSignal(bool)
    badChanged = pyqtSignal(bool)
    failChanged = pyqtSignal(bool)
    secFailChanged = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.description = "Altitude"
        self.dtype = bool
        self.value = False
        self.tol = 1000
        self.annunciate = False
        self.old = False
        self.bad = False
        self.fail = False
        self.secFail = False
        self.flags = []

    def setValue(self, value):
        self.value = value

    def setAnnunciate(self, value):
        self.flags.append(("annunciate", value, type(value)))

    def setOld(self, value):
        self.flags.append(("old", value, type(value)))

    def setBad(self, value):
        self.flags.append(("bad", value, type(value)))

    def setFail(self, value):
        self.flags.append(("fail", value, type(value)))

    def setSecFail(self, value):
        self.flags.append(("secFail", value, type(value)))

    def get_aux_list(self):
        return []


class FakeDb:
    def __init__(self, item):
        self.item = item

    def get_item(self, key):
        assert key == "ALT"
        return self.item


def test_item_dialog_constructs_and_boolean_flags_emit_bool(qtbot):
    item = FakeItem()
    connection.db = FakeDb(item)
    dialog = dbItemDialog.ItemDialog()
    qtbot.addWidget(dialog)

    dialog.setKey("ALT")
    for checkbox in dialog.findChildren(QCheckBox):
        checkbox.setChecked(True)

    assert item.flags
    assert all(value is True and value_type is bool for _, value, value_type in item.flags)
