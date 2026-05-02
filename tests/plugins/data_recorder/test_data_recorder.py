import json
from collections import OrderedDict
from unittest.mock import MagicMock, patch

import pytest

from fixgw import plugin as plugin_base
from fixgw.plugins import data_recorder


def _parent(config=None, values=None):
    parent = MagicMock()
    parent.config = {
        "CONFIGPATH": "",
        "filepath": "{CONFIG}",
        "frequency": 1000,
        "key_prefixes": ["ENG", "FUEL"],
    }
    if config:
        parent.config.update(config)
    parent.log = MagicMock()
    parent.db_callback_add = MagicMock()
    parent.db_read = MagicMock(side_effect=lambda key: values[key])
    return parent


def _value(value, old=False, bad=False, fail=False, secfail=False):
    return (value, old, bad, fail, secfail, 0)


def _make_thread(parent, keys):
    with patch.object(data_recorder.database, "listkeys", return_value=keys):
        return data_recorder.MainThread(parent)


def test_init_registers_callbacks_for_matching_prefixes_only():
    parent = _parent()

    _make_thread(parent, ["ENG1", "FUELQTY", "ALT", "ENGINE2"])

    assert [call.args[0] for call in parent.db_callback_add.call_args_list] == [
        "ENG1",
        "FUELQTY",
        "ENGINE2",
    ]
    assert all(
        call.args[1].__self__ is parent.db_callback_add.call_args_list[0].args[1].__self__
        for call in parent.db_callback_add.call_args_list
    )


def test_init_registers_all_callbacks_when_key_prefixes_is_all():
    parent = _parent({"key_prefixes": "all"})

    _make_thread(parent, ["ENG1", "ALT"])

    assert [call.args[0] for call in parent.db_callback_add.call_args_list] == [
        "ENG1",
        "ALT",
    ]


def test_non_all_string_prefix_registers_no_callbacks():
    parent = _parent({"key_prefixes": "ENG"})

    _make_thread(parent, ["ENG1", "ALT"])

    parent.db_callback_add.assert_not_called()


def test_persist_stores_only_tuple_database_values():
    parent = _parent()
    thread = _make_thread(parent, [])

    thread.persist("ENG1", _value(123.4, old=True, bad=False, fail=True, secfail=False))
    thread.persist("ENG1.Aux", 22.0)

    assert thread.data == {"ENG1": [123.4, 1, 0, 1, 0, 0]}


def test_get_all_data_snapshots_matching_keys_without_callbacks():
    parent = _parent(values={"ENG1": _value(10.0), "FUELQTY": _value(25.5)})
    thread = _make_thread(parent, ["ENG1", "FUELQTY", "ALT"])

    with patch.object(data_recorder.database, "listkeys", return_value=["ENG1", "FUELQTY", "ALT"]):
        thread.get_all_data(callbacks=False)

    assert thread.data == {
        "ENG1": [10.0, 0, 0, 0, 0, 0],
        "FUELQTY": [25.5, 0, 0, 0, 0, 0],
    }
    assert parent.db_read.call_count == 2


def test_get_all_data_snapshots_all_keys_without_callbacks():
    parent = _parent(
        {"key_prefixes": "all"},
        values={"ENG1": _value(10.0), "ALT": _value(2500.0, bad=True)},
    )
    thread = _make_thread(parent, ["ENG1", "ALT"])

    with patch.object(data_recorder.database, "listkeys", return_value=["ENG1", "ALT"]):
        thread.get_all_data(callbacks=False)

    assert thread.data == {
        "ENG1": [10.0, 0, 0, 0, 0, 0],
        "ALT": [2500.0, 0, 1, 0, 0, 0],
    }


def test_run_writes_header_and_data_snapshot(tmp_path):
    parent = _parent(
        {
            "CONFIGPATH": str(tmp_path),
            "filepath": "{CONFIG}/records",
            "frequency": 1000,
            "key_prefixes": ["ENG"],
        },
        values={"ENG1": _value(123.4, old=True)},
    )
    thread = _make_thread(parent, ["ENG1"])

    def stop_after_first_interval(_duration):
        thread.getout = True

    with patch.object(data_recorder.database, "listkeys", return_value=["ENG1"]), patch.object(
        data_recorder.time, "sleep", side_effect=stop_after_first_interval
    ):
        thread.run()

    [record_file] = tmp_path.glob("records/*/*/*/*.json")
    lines = record_file.read_text().splitlines()

    header = json.loads(lines[0])
    assert header["frequency"] == "1000"
    assert "starttime" in header
    assert json.loads(lines[1]) == {"ENG1": [123.4, 1, 0, 0, 0, 0]}


def test_run_reuses_current_file_within_same_hour(tmp_path):
    parent = _parent(
        {
            "CONFIGPATH": str(tmp_path),
            "filepath": "{CONFIG}/records",
            "frequency": 1000,
            "key_prefixes": ["ENG"],
        },
        values={"ENG1": _value(123.4)},
    )
    thread = _make_thread(parent, ["ENG1"])
    sleep_calls = 0

    def stop_after_second_interval(_duration):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            thread.persist("ENG1", _value(222.2))
        else:
            thread.getout = True

    with patch.object(data_recorder.database, "listkeys", return_value=["ENG1"]), patch.object(
        data_recorder.time, "sleep", side_effect=stop_after_second_interval
    ):
        thread.run()

    [record_file] = tmp_path.glob("records/*/*/*/*.json")
    lines = record_file.read_text().splitlines()

    assert len(lines) == 3
    assert json.loads(lines[1]) == {"ENG1": [123.4, 0, 0, 0, 0, 0]}
    assert json.loads(lines[2]) == {"ENG1": [222.2, 0, 0, 0, 0, 0]}


def test_run_swaps_buffers_before_writing_interval_data(tmp_path):
    parent = _parent(
        {
            "CONFIGPATH": str(tmp_path),
            "filepath": "{CONFIG}/records",
            "frequency": 1000,
            "key_prefixes": ["ENG"],
        },
        values={"ENG1": _value(123.4)},
    )
    thread = _make_thread(parent, ["ENG1"])
    captured = {}
    real_json_dumps = json.dumps

    def update_next_interval_before_json_dump(data, *args, **kwargs):
        if "frequency" not in data:
            captured["written_data"] = data
            thread.persist("ENG2", _value(222.2))
        return real_json_dumps(data, *args, **kwargs)

    def stop_after_first_interval(_duration):
        thread.getout = True

    with patch.object(data_recorder.database, "listkeys", return_value=["ENG1"]), patch.object(
        data_recorder.json, "dumps", side_effect=update_next_interval_before_json_dump
    ), patch.object(data_recorder.time, "sleep", side_effect=stop_after_first_interval):
        thread.run()

    assert captured["written_data"] == {"ENG1": [123.4, 0, 0, 0, 0, 0]}
    assert thread.data == {"ENG2": [222.2, 0, 0, 0, 0, 0]}


def test_run_logs_exceptions_when_file_cannot_be_opened(tmp_path):
    parent = _parent(
        {
            "CONFIGPATH": str(tmp_path),
            "filepath": "{CONFIG}/records",
            "frequency": 1000,
            "key_prefixes": ["ENG"],
        },
        values={"ENG1": _value(123.4)},
    )
    thread = _make_thread(parent, ["ENG1"])

    def stop_after_first_interval(_duration):
        thread.getout = True

    with patch.object(data_recorder.database, "listkeys", return_value=["ENG1"]), patch(
        "builtins.open", side_effect=OSError("disk full")
    ), patch.object(data_recorder.time, "sleep", side_effect=stop_after_first_interval):
        thread.run()

    messages = [call.args[0] for call in parent.log.exception.call_args_list]
    assert len(messages) == 2
    assert messages[0].startswith("Unable to write frequency to the file:")
    assert messages[1].startswith("Unable to write data to the file:")


def test_run_throttles_repeated_file_open_errors(tmp_path):
    parent = _parent(
        {
            "CONFIGPATH": str(tmp_path),
            "filepath": "{CONFIG}/records",
            "frequency": 1000,
            "key_prefixes": ["ENG"],
        },
        values={"ENG1": _value(123.4)},
    )
    thread = _make_thread(parent, ["ENG1"])
    sleep_calls = 0

    def stop_after_second_interval(_duration):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 2:
            thread.getout = True

    with patch.object(data_recorder.database, "listkeys", return_value=["ENG1"]), patch(
        "builtins.open", side_effect=OSError("disk full")
    ), patch.object(data_recorder.time, "sleep", side_effect=stop_after_second_interval):
        thread.run()

    assert parent.log.exception.call_count == 2


def test_stop_sets_getout_flag():
    thread = _make_thread(_parent(), [])

    thread.stop()

    assert thread.getout is True


def test_plugin_lifecycle_starts_and_stops_thread():
    with patch.object(data_recorder, "MainThread") as thread_cls:
        thread = thread_cls.return_value
        thread.is_alive.return_value = False
        plugin = data_recorder.Plugin("data_recorder", {}, None)

        plugin.run()
        plugin.stop()

    thread.start.assert_called_once()
    thread.stop.assert_called_once()
    thread.join.assert_not_called()
    assert plugin.get_status() == OrderedDict()


def test_plugin_stop_raises_when_thread_will_not_stop():
    with patch.object(data_recorder, "MainThread") as thread_cls:
        thread = thread_cls.return_value
        thread.is_alive.return_value = True
        plugin = data_recorder.Plugin("data_recorder", {}, None)

        with pytest.raises(plugin_base.PluginFail):
            plugin.stop()

    thread.stop.assert_called_once()
    thread.join.assert_called_once_with(1.0)
