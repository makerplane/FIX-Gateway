import datetime
import json
from collections import OrderedDict
from unittest.mock import MagicMock, patch

import pytest

from fixgw import plugin as plugin_base
from fixgw.plugins import data_playback


def _parent(tmp_path, files, config=None):
    parent = MagicMock()
    parent.config = {
        "CONFIGPATH": str(tmp_path),
        "files": files,
    }
    if config:
        parent.config.update(config)
    parent.log = MagicMock()
    parent.quit = MagicMock()
    return parent


def _write_playback_file(path, frequency=1000, starttime=None, snapshots=None):
    if starttime is None:
        starttime = datetime.datetime(2026, 5, 1, 12, 0, 0)
    if snapshots is None:
        snapshots = []

    lines = [
        {
            "frequency": str(frequency),
            "starttime": starttime.isoformat(),
        }
    ]
    lines.extend(snapshots)
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    return starttime


def _raw_item():
    item = MagicMock()
    item.value = None
    return item


def test_run_replays_snapshot_values_from_config_relative_file(tmp_path):
    playback_file = tmp_path / "playback.json"
    _write_playback_file(
        playback_file,
        frequency=250,
        snapshots=[
            {"ENG1": [100.0, 0, 0, 0, 0, 0]},
            {"ENG1": [101.5, 1, 0, 0, 0, 0], "ALT": [2500, 0, 0, 0, 0, 0]},
        ],
    )
    parent = _parent(tmp_path, ["{CONFIG}/playback.json"])
    thread = data_playback.MainThread(parent)
    items = {"ENG1": _raw_item(), "ALT": _raw_item()}
    sleeps = []

    def stop_after_second_snapshot(duration):
        sleeps.append(duration)
        if len(sleeps) == 2:
            thread.getout = True

    with patch.object(data_playback.database, "get_raw_item", side_effect=lambda key: items[key]), patch.object(
        data_playback.time, "sleep", side_effect=stop_after_second_snapshot
    ):
        thread.run()

    assert items["ENG1"].value == (101.5, 1, 0, 0, 0, 0)
    assert items["ALT"].value == (2500, 0, 0, 0, 0, 0)
    assert len(sleeps) == 2
    parent.quit.assert_not_called()


def test_run_skips_snapshots_until_start_time(tmp_path):
    playback_file = tmp_path / "playback.json"
    start = _write_playback_file(
        playback_file,
        frequency=1000,
        snapshots=[
            {"ENG1": [100.0, 0, 0, 0, 0, 0]},
            {"ENG1": [200.0, 0, 0, 0, 0, 0]},
            {"ENG1": [300.0, 0, 0, 0, 0, 0]},
        ],
    )
    parent = _parent(
        tmp_path,
        ["{CONFIG}/playback.json"],
        {"start_time": start + datetime.timedelta(seconds=2)},
    )
    thread = data_playback.MainThread(parent)
    item = _raw_item()
    sleeps = []

    def stop_after_playback_or_quit_wait(duration):
        sleeps.append(duration)
        if duration == 5:
            thread.getout = True

    with patch.object(data_playback.database, "get_raw_item", return_value=item), patch.object(
        data_playback.time, "sleep", side_effect=stop_after_playback_or_quit_wait
    ):
        thread.run()

    assert item.value == (300.0, 0, 0, 0, 0, 0)
    parent.quit.assert_called_once()
    assert sleeps[-1] == 5


def test_run_with_start_time_after_file_quits_without_writing_values(tmp_path):
    playback_file = tmp_path / "playback.json"
    start = _write_playback_file(
        playback_file,
        frequency=1000,
        snapshots=[{"ENG1": [100.0, 0, 0, 0, 0, 0]}],
    )
    parent = _parent(
        tmp_path,
        ["{CONFIG}/playback.json"],
        {"start_time": start + datetime.timedelta(minutes=5)},
    )
    thread = data_playback.MainThread(parent)

    def stop_after_quit_wait(duration):
        if duration == 5:
            thread.getout = True

    with patch.object(data_playback.database, "get_raw_item") as get_raw_item, patch.object(
        data_playback.time, "sleep", side_effect=stop_after_quit_wait
    ):
        thread.run()

    get_raw_item.assert_not_called()
    parent.quit.assert_called_once()


def test_stop_sets_getout_flag():
    thread = data_playback.MainThread(_parent(None, []))

    thread.stop()

    assert thread.getout is True


def test_plugin_lifecycle_starts_and_stops_thread():
    with patch.object(data_playback, "MainThread") as thread_cls:
        thread = thread_cls.return_value
        thread.is_alive.return_value = False
        plugin = data_playback.Plugin("data_playback", {}, None)

        plugin.run()
        plugin.stop()

    thread.start.assert_called_once()
    thread.stop.assert_called_once()
    thread.join.assert_not_called()
    assert plugin.get_status() == OrderedDict()


def test_plugin_stop_raises_when_thread_will_not_stop():
    with patch.object(data_playback, "MainThread") as thread_cls:
        thread = thread_cls.return_value
        thread.is_alive.return_value = True
        plugin = data_playback.Plugin("data_playback", {}, None)

        with pytest.raises(plugin_base.PluginFail):
            plugin.stop()

    thread.stop.assert_called_once()
    thread.join.assert_called_once_with(1.0)
