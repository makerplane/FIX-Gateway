from PyQt6.QtWidgets import QApplication

from fixgw.client import connection, gui, statusModel


class FakeStatusClient:
    def __init__(self, response):
        self.response = response

    def isConnected(self):
        return True

    def getStatus(self):
        return self.response


def test_status_view_ignores_invalid_json(qtbot, capsys):
    connection.client = FakeStatusClient("{broken")
    view = statusModel.StatusView()
    qtbot.addWidget(view)

    view.update()

    assert view.textBox.text() == ""
    assert "statusModel.update()" in capsys.readouterr().out


def test_status_view_formats_valid_json(qtbot):
    connection.client = FakeStatusClient('{"running": true}')
    view = statusModel.StatusView()
    qtbot.addWidget(view)

    view.update()

    assert "running" in view.textBox.text()
    assert "True" in view.textBox.text()


def test_gui_main_reuses_existing_qapplication(monkeypatch, qtbot):
    initialized = []
    shown = []

    class FakeWindow:
        def __init__(self):
            shown.append(True)

    app = QApplication.instance()
    monkeypatch.setattr(gui.connection, "initialize", initialized.append)
    monkeypatch.setattr(gui, "MainWindow", FakeWindow)
    monkeypatch.setattr(app, "exec", lambda: 7)

    result = gui.main("client")

    assert result == 7
    assert initialized == ["client"]
    assert shown == [True]
