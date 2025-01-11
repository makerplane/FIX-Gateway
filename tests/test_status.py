import pytest
from unittest.mock import MagicMock, patch
from collections import OrderedDict

from fixgw.status import (
    Status,
    initialize,
    get_dict,
    dict2string,
    get_object,
    get_string,
)


@pytest.fixture
def mock_database():
    with patch("fixgw.database.listkeys") as mock_listkeys:
        mock_listkeys.return_value = ["key1", "key2"]
        yield mock_listkeys


@pytest.fixture
def mock_plugins():
    mock_plugin = MagicMock()
    mock_plugin.is_running.return_value = True
    mock_plugin.get_status.return_value = {"uptime": "5m"}
    return {"plugin1": mock_plugin}


@pytest.fixture
def mock_fixgw():
    with patch("fixgw.__version__", "1.0.0") as mock_version:
        yield mock_version


@patch("psutil.Process", autospec=True)
def test_get_system_status(mock_process):
    mock_process_instance = mock_process.return_value
    mock_process_instance.cpu_percent.return_value = 15.5
    mock_process_instance.memory_percent.return_value = 25.3

    from fixgw.status import get_system_status

    expected = {
        "Performance": OrderedDict({"CPU Percent": "15.50", "Memory Percent": "25.30"})
    }
    assert get_system_status() == expected


def test_status_initialization(mock_database, mock_plugins, mock_fixgw):
    config_status = {"Config": "Loaded"}
    status = Status(mock_plugins, config_status)

    assert status.db_item_count == 2
    assert status.config_status == config_status
    assert status.plugins == mock_plugins


def test_status_get_dict(mock_database, mock_plugins, mock_fixgw):
    config_status = {"Config": "Loaded"}
    status = Status(mock_plugins, config_status)

    expected = OrderedDict(
        {
            "Version": "1.0.0",
            "Config": "Loaded",
            "Performance": {},
            "Database Statistics": {"Item Count": 2},
            "Connection: plugin1": OrderedDict({"Running": True, "uptime": "5m"}),
        }
    )

    with patch("fixgw.status.get_system_status", return_value={"Performance": {}}):
        assert status.get_dict() == expected


def test_dict2string():
    data = {"Level1": {"Level2": {"Key": "Value"}, "AnotherKey": "AnotherValue"}}
    expected = (
        "Level1\n" "   Level2\n" "      Key: Value\n" "   AnotherKey: AnotherValue\n"
    )
    result = dict2string(data)
    assert result == expected


def test_initialize(mock_plugins, mock_fixgw):
    config_status = {"Config": "Loaded"}

    initialize(mock_plugins, config_status)

    obj = get_object()
    assert obj.plugins == mock_plugins
    assert obj.config_status == config_status


def test_get_string(mock_database, mock_plugins, mock_fixgw):
    config_status = {"Config": "Loaded"}
    initialize(mock_plugins, config_status)

    result = get_string()

    expected_substr = "Version: 1.0.0"
    assert expected_substr in result


def test_get_dict(mock_database, mock_plugins, mock_fixgw):
    config_status = {"Config": "Loaded"}
    initialize(mock_plugins, config_status)

    result = get_dict()

    assert result["Version"] == "1.0.0"


def test_status_get_dict_plugin_edge_cases():
    mock_plugin_error = MagicMock()
    mock_plugin_error.is_running.side_effect = Exception("Plugin error")
    mock_plugin_error.get_status.return_value = None

    plugins = {"plugin_error": mock_plugin_error}
    config_status = {"Config": "Loaded"}
    status = Status(plugins, config_status)

    with patch("fixgw.status.get_system_status", return_value={"Performance": {}}):
        result = status.get_dict()
        assert "Connection: plugin_error" in result
        assert result["Connection: plugin_error"]["Error"] == "Plugin error"


def test_psutil_import_error():
    original_import = __import__  # Save the actual built-in __import__ function

    def side_effect(name, *args, **kwargs):
        if name == "psutil":
            raise ImportError
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=side_effect):
        import importlib
        from fixgw import status

        importlib.reload(status)

        assert status.psutil is None
        assert status.get_system_status() == {}


def test_dict2string_empty_dict():
    from fixgw.status import dict2string

    # Test with an empty dictionary
    result = dict2string({})
    assert result == ""


def test_psutil_import_failure():
    with patch("fixgw.status.psutil", None):
        # Explicitly redefine get_system_status to simulate psutil absence
        from fixgw import status

        def mock_get_system_status():
            return {}

        status.get_system_status = mock_get_system_status

        # Test the behavior
        assert status.get_system_status() == {}
        assert get_dict() == {}


def test_initialize_without_psutil(mock_plugins):
    with patch.dict("sys.modules", {"psutil": None}):
        initialize(mock_plugins, {"Config": "Loaded"})
        obj = get_object()
        assert obj is not None


def test_status_get_dict_with_plugin_variations(mock_fixgw):
    mock_plugin_running = MagicMock()
    mock_plugin_running.is_running.return_value = True
    mock_plugin_running.get_status.return_value = {}

    mock_plugin_stopped = MagicMock()
    mock_plugin_stopped.is_running.return_value = False
    mock_plugin_stopped.get_status.return_value = None

    plugins = {
        "plugin_running": mock_plugin_running,
        "plugin_stopped": mock_plugin_stopped,
    }
    config_status = {"Config": "Loaded"}
    status = Status(plugins, config_status)

    with patch("fixgw.status.get_system_status", return_value={"Performance": {}}):
        result = status.get_dict()
        assert result["Connection: plugin_running"]["Running"] is True
        assert result["Connection: plugin_stopped"]["Running"] is False


def test_dict2string_non_dict_values():
    data = {"Key": "Value", "Number": 42, "Nested": {"SubKey": "SubValue"}}
    expected = "Key: Value\n" "Number: 42\n" "Nested\n" "   SubKey: SubValue\n"
    assert dict2string(data) == expected
