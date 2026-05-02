import pytest
from PyQt6.QtCore import QObject, pyqtSignal

from fixgw.client import common


class FakeItem(QObject):
    valueChanged = pyqtSignal(object)

    def __init__(self, dtype, value=None, min_value=0, max_value=1):
        super().__init__()
        self.dtype = dtype
        self.value = value
        self.min = min_value
        self.max = max_value
        self.values = []

    def setValue(self, value):
        self.values.append(value)
        self.value = value


def test_bool_control_sends_boolean_values(qtbot):
    item = FakeItem(bool, False)

    control = common.getValueControl(item, None)
    qtbot.addWidget(control)

    control.setChecked(True)

    assert item.values == [True]
    assert type(item.values[0]) is bool


def test_bool_control_updates_from_item_signal(qtbot):
    item = FakeItem(bool, False)

    control = common.getValueControl(item, None)
    qtbot.addWidget(control)
    item.valueChanged.emit(True)

    assert control.isChecked()


def test_unsupported_dtype_raises_clear_error():
    item = FakeItem(bytes, b"")

    with pytest.raises(TypeError, match="Unsupported item dtype"):
        common.getValueControl(item, None)
