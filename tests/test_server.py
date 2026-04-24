import argparse
import datetime
import queue
import runpy
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

import fixgw.server as server


@pytest.fixture(autouse=True)
def reset_server_globals():
    old_config_path = server.config_path
    old_preferences = server.preferences
    old_plugin_mods = server.plugin_mods
    old_plugins = server.plugins
    old_log = server.log
    old_leader = server.quorum.leader

    server.config_path = None
    server.preferences = {}
    server.plugin_mods = {}
    server.plugins = {}
    server.log = MagicMock()
    server.quorum.leader = True

    yield

    server.config_path = old_config_path
    server.preferences = old_preferences
    server.plugin_mods = old_plugin_mods
    server.plugins = old_plugins
    server.log = old_log
    server.quorum.leader = old_leader


def make_args(**overrides):
    values = {
        "debug": False,
        "verbose": False,
        "daemonize": False,
        "config_file": None,
        "log_config": None,
        "playback_start_time": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def make_config_file(tmp_path):
    config_file = tmp_path / "default.yaml"
    config_file.write_text("unused: true\n")
    return config_file


def write_preferences(tmp_path, contents="{}\n"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    pref_file = tmp_path / "preferences.yaml"
    pref_file.write_text(contents)
    return pref_file


def test_load_plugin_removes_internal_keys_and_sets_config_path():
    plugin_class = MagicMock()
    module = SimpleNamespace(Plugin=plugin_class)
    config = {"module": "fake.module", "load": True, "port": 3490}

    with patch("fixgw.server.importlib.import_module", return_value=module) as importer:
        server.config_path = "/tmp/fixgw-config"
        server.load_plugin("netfix", "fake.module", config, {"meta": True})

    importer.assert_called_once_with("fake.module")
    assert config == {"port": 3490, "CONFIGPATH": "/tmp/fixgw-config"}
    plugin_class.assert_called_once_with(
        "netfix", {"port": 3490, "CONFIGPATH": "/tmp/fixgw-config"}, {"meta": True}
    )
    assert server.plugin_mods["netfix"] is module
    assert server.plugins["netfix"] is plugin_class.return_value


def test_sig_int_handler_queues_quit():
    with patch.object(server.plugin.jobQueue, "put") as put:
        server.sig_int_handler(None, None)

    put.assert_called_once_with("QUIT")


def test_merge_dict_recursively_overrides_nested_values():
    dest = {"top": {"left": 1, "keep": True}, "plain": "old"}
    override = {"top": {"left": 2, "right": 3}, "plain": "new"}

    server.merge_dict(dest, override)

    assert dest == {"top": {"left": 2, "keep": True, "right": 3}, "plain": "new"}


def test_import_falls_back_to_legacy_queue_module(monkeypatch):
    original_import = __import__
    fake_queue_module = SimpleNamespace(Empty=RuntimeError, Queue=MagicMock())

    def fake_import(name, *args, **kwargs):
        if name == "queue":
            raise ImportError("no queue")
        if name == "Queue":
            return fake_queue_module
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    module_globals = runpy.run_path(server.__file__, run_name="fixgw_server_queue_fallback")

    assert module_globals["queue"] is fake_queue_module


def test_create_config_dir_copies_missing_updated_and_dist_files(tmp_path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "new.txt").write_text("new")
    (source_root / "same.txt").write_text("fresh")
    (source_root / "samehash.txt").write_text("same")
    (source_root / "edited.txt").write_text("edited-source")
    (source_root / "subdir").mkdir()
    (source_root / "subdir" / "inner.txt").write_text("inner")

    dest_root = tmp_path / "dest"
    config_dir = dest_root / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "same.txt").write_text("stale")
    (config_dir / "samehash.txt").write_text("same")
    (config_dir / "edited.txt").write_text("user-edited")
    old_timestamp = 350039106.789
    newer_timestamp = old_timestamp + 1
    (config_dir / "same.txt").touch()
    (config_dir / "samehash.txt").touch()
    (config_dir / "edited.txt").touch()
    server.os.utime(config_dir / "same.txt", (old_timestamp, old_timestamp))
    server.os.utime(config_dir / "samehash.txt", (old_timestamp, old_timestamp))
    server.os.utime(config_dir / "edited.txt", (newer_timestamp, newer_timestamp))

    class FakeDir:
        def __init__(self, name, children):
            self.name = name
            self._children = children

        def is_dir(self):
            return True

        def iterdir(self):
            return iter(self._children)

    class FakeFile:
        def __init__(self, path):
            self._path = path
            self.name = path.name

        def is_dir(self):
            return False

        def as_posix(self):
            return self._path.as_posix()

    fake_tree = {
        "fixgw.config": FakeDir(
            "config",
            [
                FakeFile(source_root / "new.txt"),
                FakeFile(source_root / "same.txt"),
                FakeFile(source_root / "samehash.txt"),
                FakeFile(source_root / "edited.txt"),
                FakeDir("subdir", [FakeFile(source_root / "subdir" / "inner.txt")]),
            ],
        ),
        "fixgw.config.subdir": FakeDir(
            "subdir", [FakeFile(source_root / "subdir" / "inner.txt")]
        ),
    }

    with patch("importlib.resources.files", side_effect=fake_tree.__getitem__):
        server.create_config_dir(str(dest_root))

    assert (config_dir / "new.txt").read_text() == "new"
    assert (config_dir / "same.txt").read_text() == "fresh"
    assert (config_dir / "samehash.txt").read_text() == "same"
    assert (config_dir / "edited.txt").read_text() == "user-edited"
    assert (config_dir / "edited.txt.dist").read_text() == "edited-source"
    assert (config_dir / "subdir" / "inner.txt").read_text() == "inner"


def test_main_setup_loads_connections_and_initialization_files(tmp_path):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path, "enabled:\n  optional_plugin: false\n")
    (tmp_path / "preferences.yaml.custom").write_text(
        "enabled:\n  optional_plugin: true\nextra: yes\n"
    )
    init_file = tmp_path / "init.txt"
    init_file.write_text("# comment\n FIRST = 1 \nINVALID\nSECOND=2\n")

    config = {
        "database file": "{CONFIG}/db.yaml",
        "initialization files": [str(init_file)],
        "connections": {
            "quorum": {"module": "fixgw.plugins.quorum", "load": True},
            "optional": {"module": "custom.optional", "load": "optional_plugin"},
            "skip_me": {"module": "custom.skip", "load": False},
        },
    }
    config_meta = {
        "connections": {
            "quorum": {"source": "quorum"},
            "optional": {"source": "optional"},
            "skip_me": {"source": "skip_me"},
        }
    }
    args = make_args(config_file=open(config_file))
    fake_log = MagicMock()

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(args, [])
        ),
        patch("fixgw.server.cfg.from_yaml", return_value=(config, config_meta)) as from_yaml,
        patch("fixgw.server.database.init") as database_init,
        patch("fixgw.server.database.write") as database_write,
        patch("fixgw.server.load_plugin") as load_plugin,
        patch("fixgw.server.status.initialize") as initialize,
        patch("fixgw.server.signal.signal") as signal_handler,
        patch("fixgw.server.logging.getLogger", return_value=fake_log),
        patch("fixgw.server.logging.basicConfig") as basic_config,
        patch("fixgw.server.logging.config.fileConfig") as file_config,
        patch("fixgw.server.logging.config.dictConfig") as dict_config,
    ):
        try:
            result = server.main_setup()
        finally:
            args.config_file.close()

    assert result is args
    from_yaml.assert_called_once_with(
        str(config_file), preferences=server.preferences, metadata=True
    )
    database_init.assert_called_once_with(f"{tmp_path}/db.yaml")
    database_write.assert_has_calls(
        [
            call("GATEWAY_VERSION", server.__version__),
            call("FIRST", "1"),
            call("SECOND", "2"),
        ]
    )
    load_plugin.assert_has_calls(
        [
            call("quorum", "fixgw.plugins.quorum", config["connections"]["quorum"], {"source": "quorum"}),
            call("optional", "custom.optional", config["connections"]["optional"], {"source": "optional"}),
        ]
    )
    initialize.assert_called_once_with(
        server.plugins,
        {"Configuration File": str(config_file), "Configuration Path": str(tmp_path)},
    )
    signal_handler.assert_has_calls(
        [
            call(server.signal.SIGINT, server.sig_int_handler),
            call(server.signal.SIGTERM, server.sig_int_handler),
        ]
    )
    basic_config.assert_called_once()
    file_config.assert_not_called()
    dict_config.assert_not_called()
    fake_log.info.assert_any_call("Starting FIX Gateway")
    assert server.config_path == str(tmp_path)
    assert server.preferences["enabled"]["optional_plugin"] is True
    assert server.preferences["extra"] is True
    assert server.quorum.leader is False


def test_main_setup_uses_log_config_and_skips_signal_handlers_when_daemonized(tmp_path):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path)
    log_config = tmp_path / "logging.ini"
    log_config.write_text("[loggers]\n")

    config = {"database file": "{CONFIG}/db.yaml", "connections": {}}
    args = make_args(
        daemonize=True,
        config_file=open(config_file),
        log_config=open(log_config),
    )

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(args, [])
        ),
        patch("fixgw.server.cfg.from_yaml", return_value=(config, {"connections": {}})),
        patch("fixgw.server.database.init"),
        patch("fixgw.server.database.write"),
        patch("fixgw.server.status.initialize"),
        patch("fixgw.server.signal.signal") as signal_handler,
        patch("fixgw.server.logging.getLogger", return_value=MagicMock()),
        patch("fixgw.server.logging.config.fileConfig") as file_config,
    ):
        try:
            server.main_setup()
        finally:
            args.config_file.close()
            args.log_config.close()

    file_config.assert_called_once_with(args.log_config)
    signal_handler.assert_not_called()


def test_main_setup_uses_default_config_copy_when_no_config_file_is_provided(tmp_path, monkeypatch):
    write_preferences(tmp_path / "makerplane" / "fixgw" / "config")
    config = {"database file": "{CONFIG}/db.yaml", "connections": {}}
    fake_log = MagicMock()

    monkeypatch.setattr(server, "user_home", str(tmp_path))
    monkeypatch.setattr(server, "path_options", [])

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(make_args(), [])
        ),
        patch("fixgw.server.create_config_dir") as create_config_dir,
        patch("fixgw.server.cfg.from_yaml", return_value=(config, {"connections": {}})),
        patch("fixgw.server.database.init"),
        patch("fixgw.server.database.write"),
        patch("fixgw.server.status.initialize"),
        patch("fixgw.server.signal.signal"),
        patch("fixgw.server.logging.getLogger", return_value=fake_log),
        patch("fixgw.server.logging.basicConfig"),
    ):
        args = server.main_setup()

    create_config_dir.assert_called_once_with(f"{tmp_path}/makerplane/fixgw")
    assert args.config_file is None
    assert server.config_path == f"{tmp_path}/makerplane/fixgw/config"


def test_main_setup_exits_under_systemd_when_auto_start_disabled(tmp_path):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path)
    args = make_args(config_file=open(config_file))

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(args, [])
        ),
        patch(
            "fixgw.server.cfg.from_yaml",
            return_value=({"database file": "{CONFIG}/db.yaml"}, {"connections": {}}),
        ),
        patch("fixgw.server.environ.get", return_value="systemd"),
        patch("fixgw.server.os._exit", side_effect=SystemExit(0)) as os_exit,
    ):
        with pytest.raises(SystemExit) as excinfo:
            try:
                server.main_setup()
            finally:
                args.config_file.close()

    os_exit.assert_called_once_with(0)
    assert excinfo.value.code == 0


def test_main_setup_continues_under_systemd_when_auto_start_enabled_and_uses_dict_logging(
    tmp_path,
):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path)
    args = make_args(config_file=open(config_file), verbose=True)
    fake_log = MagicMock()
    config = {
        "database file": "{CONFIG}/db.yaml",
        "auto start": True,
        "logging": {"version": 1},
        "connections": {},
    }

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(args, [])
        ),
        patch("fixgw.server.cfg.from_yaml", return_value=(config, {"connections": {}})),
        patch("fixgw.server.environ.get", return_value="systemd"),
        patch("fixgw.server.os._exit") as os_exit,
        patch("fixgw.server.database.init"),
        patch("fixgw.server.database.write"),
        patch("fixgw.server.status.initialize"),
        patch("fixgw.server.signal.signal"),
        patch("fixgw.server.logging.getLogger", return_value=fake_log),
        patch("fixgw.server.logging.config.dictConfig") as dict_config,
    ):
        try:
            server.main_setup()
        finally:
            args.config_file.close()

    os_exit.assert_not_called()
    dict_config.assert_called_once_with({"version": 1})
    fake_log.setLevel.assert_called_once_with(server.logging.INFO)


def test_main_setup_skips_quorum_disable_when_connection_has_no_module_or_disabled_preference(
    tmp_path,
):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path, "enabled:\n  quorum_pref: false\n")
    args = make_args(config_file=open(config_file))
    config = {
        "database file": "{CONFIG}/db.yaml",
        "connections": {
            "missing_module": {"load": False},
            "quorum": {"module": "fixgw.plugins.quorum", "load": "quorum_pref"},
        },
    }
    config_meta = {"connections": {"missing_module": {}, "quorum": {}}}

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(args, [])
        ),
        patch("fixgw.server.cfg.from_yaml", return_value=(config, config_meta)),
        patch("fixgw.server.database.init"),
        patch("fixgw.server.database.write"),
        patch("fixgw.server.status.initialize"),
        patch("fixgw.server.signal.signal"),
        patch("fixgw.server.logging.getLogger", return_value=MagicMock()),
        patch("fixgw.server.logging.basicConfig"),
    ):
        try:
            server.main_setup()
        finally:
            args.config_file.close()

    assert server.quorum.leader is True


def test_main_setup_playback_mode_loads_existing_hour_files(tmp_path):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path)
    start_time = datetime.datetime(2026, 4, 24, 11, 0, 0)
    args = make_args(config_file=open(config_file), playback_start_time=start_time)

    config = {
        "database file": "{CONFIG}/db.yaml",
        "connections": {
            "recorder": {
                "module": "fixgw.plugins.data_recorder",
                "filepath": "{CONFIG}/logs",
            }
        },
    }
    existing = {
        str(tmp_path / "logs" / "2026" / "04" / "24" / "2026-04-24.11.json"),
        str(tmp_path / "logs" / "2026" / "04" / "24" / "2026-04-24.12.json"),
    }

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(args, [])
        ),
        patch("fixgw.server.cfg.from_yaml", return_value=(config, {"connections": {}})),
        patch("fixgw.server.database.init"),
        patch("fixgw.server.database.write"),
        patch("fixgw.server.status.initialize"),
        patch("fixgw.server.logging.getLogger", return_value=MagicMock()),
        patch("fixgw.server.signal.signal"),
        patch("fixgw.server.load_plugin") as load_plugin,
        patch("fixgw.server.os.path.isfile", side_effect=lambda path: path in existing),
    ):
        try:
            server.main_setup()
        finally:
            args.config_file.close()

    playback_call = load_plugin.call_args_list[1]
    assert load_plugin.call_args_list[0] == call(
        "netfix",
        "fixgw.plugins.netfix",
        {
            "module": "fixgw.plugins.netfix",
            "load": True,
            "type": "server",
            "host": "0.0.0.0",
            "port": "3490",
            "buffer_size": 1024,
        },
        {},
    )
    assert playback_call.args[0:2] == ("data_playback", "fixgw.plugins.data_playback")
    assert playback_call.args[2]["files"] == sorted(existing)
    assert playback_call.args[2]["start_time"] == start_time


def test_main_setup_playback_mode_logs_plugin_load_error_without_raising_when_not_debug(
    tmp_path,
):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path)
    start_time = datetime.datetime(2026, 4, 24, 11, 0, 0)
    args = make_args(config_file=open(config_file), playback_start_time=start_time)
    config = {
        "database file": "{CONFIG}/db.yaml",
        "connections": {
            "other": {"module": "custom.other", "filepath": "{CONFIG}/ignored"},
            "recorder": {
                "module": "fixgw.plugins.data_recorder",
                "filepath": "{CONFIG}/logs",
            },
        },
    }
    existing = {str(tmp_path / "logs" / "2026" / "04" / "24" / "2026-04-24.11.json")}

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(args, [])
        ),
        patch("fixgw.server.cfg.from_yaml", return_value=(config, {"connections": {}})),
        patch("fixgw.server.database.init"),
        patch("fixgw.server.database.write"),
        patch("fixgw.server.status.initialize") as initialize,
        patch("fixgw.server.logging.getLogger", return_value=MagicMock()),
        patch("fixgw.server.signal.signal"),
        patch("fixgw.server.os.path.isfile", side_effect=lambda path: path in existing),
        patch("fixgw.server.load_plugin", side_effect=RuntimeError("playback fail")),
        patch("fixgw.server.logging.critical") as critical,
    ):
        try:
            server.main_setup()
        finally:
            args.config_file.close()

    critical.assert_called_once()
    initialize.assert_called_once()


def test_main_setup_playback_mode_reraises_plugin_load_error_in_debug(tmp_path):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path)
    start_time = datetime.datetime(2026, 4, 24, 11, 0, 0)
    args = make_args(
        config_file=open(config_file), playback_start_time=start_time, debug=True
    )
    config = {
        "database file": "{CONFIG}/db.yaml",
        "connections": {
            "recorder": {
                "module": "fixgw.plugins.data_recorder",
                "filepath": "{CONFIG}/logs",
            }
        },
    }
    existing = {str(tmp_path / "logs" / "2026" / "04" / "24" / "2026-04-24.11.json")}

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(args, [])
        ),
        patch("fixgw.server.cfg.from_yaml", return_value=(config, {"connections": {}})),
        patch("fixgw.server.database.init"),
        patch("fixgw.server.database.write"),
        patch("fixgw.server.status.initialize"),
        patch("fixgw.server.logging.getLogger", return_value=MagicMock()),
        patch("fixgw.server.os.path.isfile", side_effect=lambda path: path in existing),
        patch("fixgw.server.load_plugin", side_effect=RuntimeError("playback fail")),
    ):
        with pytest.raises(RuntimeError, match="playback fail"):
            try:
                server.main_setup()
            finally:
                args.config_file.close()


def test_main_setup_playback_mode_raises_when_no_logs_exist(tmp_path):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path)
    args = make_args(
        config_file=open(config_file),
        playback_start_time=datetime.datetime(2026, 4, 24, 11, 0, 0),
    )
    config = {
        "database file": "{CONFIG}/db.yaml",
        "connections": {
            "recorder": {
                "module": "fixgw.plugins.data_recorder",
                "filepath": "{CONFIG}/logs",
            }
        },
    }

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(args, [])
        ),
        patch("fixgw.server.cfg.from_yaml", return_value=(config, {"connections": {}})),
        patch("fixgw.server.database.init"),
        patch("fixgw.server.database.write"),
        patch("fixgw.server.status.initialize"),
        patch("fixgw.server.logging.getLogger", return_value=MagicMock()),
        patch("fixgw.server.os.path.isfile", return_value=False),
    ):
        with pytest.raises(Exception, match="No logs found for the date and time provided"):
            try:
                server.main_setup()
            finally:
                args.config_file.close()


def test_main_setup_raises_and_logs_when_database_init_fails(tmp_path):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path)
    args = make_args(config_file=open(config_file))
    fake_log = MagicMock()

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(args, [])
        ),
        patch(
            "fixgw.server.cfg.from_yaml",
            return_value=({"database file": "{CONFIG}/db.yaml"}, {}),
        ),
        patch("fixgw.server.database.init", side_effect=RuntimeError("db fail")),
        patch("fixgw.server.logging.getLogger", return_value=fake_log),
        patch("fixgw.server.logging.basicConfig"),
    ):
        with pytest.raises(RuntimeError, match="db fail"):
            try:
                server.main_setup()
            finally:
                args.config_file.close()

    fake_log.error.assert_any_call("Database failure, Exiting:db fail")


def test_main_setup_raises_and_logs_when_initialization_file_fails(tmp_path):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path)
    args = make_args(config_file=open(config_file))
    fake_log = MagicMock()
    config = {
        "database file": "{CONFIG}/db.yaml",
        "initialization files": [str(tmp_path / "missing.txt")],
    }

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(args, [])
        ),
        patch("fixgw.server.cfg.from_yaml", return_value=(config, {})),
        patch("fixgw.server.database.init"),
        patch("fixgw.server.database.write"),
        patch("fixgw.server.logging.getLogger", return_value=fake_log),
        patch("fixgw.server.logging.basicConfig"),
    ):
        with pytest.raises(FileNotFoundError):
            try:
                server.main_setup()
            finally:
                args.config_file.close()

    fake_log.error.assert_any_call(
        "Problem setting initial values from configuration - "
        f"[Errno 2] No such file or directory: '{tmp_path / 'missing.txt'}'"
    )


def test_main_setup_logs_plugin_load_error_without_raising_when_not_debug(tmp_path):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path)
    args = make_args(config_file=open(config_file))
    config = {
        "database file": "{CONFIG}/db.yaml",
        "connections": {"bad": {"module": "custom.bad", "load": True}},
    }
    config_meta = {"connections": {"bad": {"source": "bad"}}}

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(args, [])
        ),
        patch("fixgw.server.cfg.from_yaml", return_value=(config, config_meta)),
        patch("fixgw.server.database.init"),
        patch("fixgw.server.database.write"),
        patch("fixgw.server.status.initialize") as initialize,
        patch("fixgw.server.signal.signal"),
        patch("fixgw.server.logging.getLogger", return_value=MagicMock()),
        patch("fixgw.server.logging.basicConfig"),
        patch("fixgw.server.load_plugin", side_effect=RuntimeError("load fail")),
        patch("fixgw.server.logging.critical") as critical,
    ):
        try:
            server.main_setup()
        finally:
            args.config_file.close()

    critical.assert_called_once_with("Unable to load module - custom.bad: load fail")
    initialize.assert_called_once()


def test_main_setup_reraises_plugin_load_error_in_debug(tmp_path):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path)
    args = make_args(config_file=open(config_file), debug=True)
    config = {
        "database file": "{CONFIG}/db.yaml",
        "connections": {"bad": {"module": "custom.bad", "load": True}},
    }
    config_meta = {"connections": {"bad": {"source": "bad"}}}

    with (
        patch.object(
            argparse.ArgumentParser, "parse_known_args", return_value=(args, [])
        ),
        patch("fixgw.server.cfg.from_yaml", return_value=(config, config_meta)),
        patch("fixgw.server.database.init"),
        patch("fixgw.server.database.write"),
        patch("fixgw.server.status.initialize"),
        patch("fixgw.server.logging.getLogger", return_value=MagicMock()),
        patch("fixgw.server.logging.basicConfig"),
        patch("fixgw.server.load_plugin", side_effect=RuntimeError("load fail")),
    ):
        with pytest.raises(RuntimeError, match="load fail"):
            try:
                server.main_setup()
            finally:
                args.config_file.close()


def test_main_non_daemon_calls_run():
    args = make_args()

    with patch("fixgw.server.main_setup", return_value=args), patch(
        "fixgw.server.run"
    ) as run:
        server.main()

    run.assert_called_once_with(args)


def test_main_daemon_mode_logs_and_raises_when_daemon_module_is_missing():
    args = make_args(daemonize=True)
    fake_log = MagicMock()
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "daemon":
            raise ModuleNotFoundError("missing daemon")
        return original_import(name, *args, **kwargs)

    with (
        patch("fixgw.server.main_setup", return_value=args),
        patch("fixgw.server.logging.getLogger", return_value=fake_log),
        patch("builtins.__import__", side_effect=fake_import),
    ):
        with pytest.raises(ModuleNotFoundError):
            server.main()

    fake_log.error.assert_called_once_with("Unable to load daemon module.")


def test_main_daemon_mode_runs_inside_daemon_context_and_logs_run_errors():
    args = make_args(daemonize=True)
    fake_log = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = context
    context.__exit__.return_value = False
    daemon_module = SimpleNamespace(DaemonContext=MagicMock(return_value=context))

    with (
        patch("fixgw.server.main_setup", return_value=args),
        patch("fixgw.server.logging.getLogger", return_value=fake_log),
        patch.dict(sys.modules, {"daemon": daemon_module}),
        patch("fixgw.server.run", side_effect=RuntimeError("run exploded")),
    ):
        server.main()

    daemon_module.DaemonContext.assert_called_once_with(umask=0o002)
    assert context.signal_map[server.signal.SIGTERM] is server.sig_int_handler
    assert context.signal_map[server.signal.SIGINT] is server.sig_int_handler
    assert context.signal_map[server.signal.SIGHUP] == "terminate"
    fake_log.debug.assert_called_once_with("Sending to Background")
    fake_log.error.assert_called_once_with("run exploded")


def test_run_breaks_when_no_plugins_are_running():
    plugin_a = MagicMock()
    plugin_a.is_running.return_value = False
    plugin_b = MagicMock()
    plugin_b.is_running.return_value = False
    server.plugins = {"a": plugin_a, "b": plugin_b}
    server.log = MagicMock()
    args = make_args()

    with patch.object(
        server.plugin.jobQueue,
        "get",
        side_effect=[queue.Empty(), queue.Empty(), queue.Empty(), queue.Empty()],
    ):
        server.run(args)

    plugin_a.start.assert_called_once()
    plugin_b.start.assert_called_once()
    plugin_a.shutdown.assert_called_once()
    plugin_b.shutdown.assert_called_once()
    server.log.info.assert_any_call("No plugins running, quitting")
    server.log.info.assert_any_call("FIX Gateway Exiting Normally")


def test_run_continues_after_start_failure_when_not_debug_and_handles_non_quit_jobs():
    failing_plugin = MagicMock()
    failing_plugin.start.side_effect = RuntimeError("boom")
    failing_plugin.is_running.return_value = False
    healthy_plugin = MagicMock()
    healthy_plugin.is_running.return_value = True
    server.plugins = {"bad": failing_plugin, "good": healthy_plugin}
    server.log = MagicMock()
    args = make_args(debug=False)

    with patch.object(
        server.plugin.jobQueue,
        "get",
        side_effect=["CONTINUE", queue.Empty(), queue.Empty(), queue.Empty(), "QUIT"],
    ):
        server.run(args)

    healthy_plugin.start.assert_called_once()
    healthy_plugin.shutdown.assert_called_once()
    server.log.error.assert_any_call("Problem Starting Plugin: bad - boom")
    server.log.info.assert_any_call("FIX Gateway Exiting Normally")


def test_run_debug_mode_queues_quit_on_start_failure():
    failing_plugin = MagicMock()
    failing_plugin.start.side_effect = RuntimeError("boom")
    server.plugins = {"bad": failing_plugin}
    server.log = MagicMock()
    args = make_args(debug=True)

    with (
        patch.object(server.plugin.jobQueue, "put") as put,
        patch.object(server.plugin.jobQueue, "get", return_value="QUIT"),
        patch("fixgw.server.traceback.format_exc", return_value="traceback"),
    ):
        server.run(args)

    put.assert_called_once_with("QUIT")
    failing_plugin.shutdown.assert_called_once()
    server.log.error.assert_any_call("Problem Starting Plugin: bad - boom")
    server.log.info.assert_any_call("FIX Gateway Exiting Normally")


def test_run_force_exits_when_plugin_shutdown_fails():
    running_plugin = MagicMock()
    running_plugin.shutdown.side_effect = server.plugin.PluginFail()
    server.plugins = {"bad": running_plugin}
    server.log = MagicMock()
    args = make_args()

    with (
        patch.object(server.plugin.jobQueue, "get", side_effect=KeyboardInterrupt),
        patch("fixgw.server.os._exit") as os_exit,
    ):
        server.run(args)

    server.log.warning.assert_called_once_with("Plugin bad did not shutdown properly")
    server.log.info.assert_any_call("Termination from keybaord received")
    server.log.info.assert_any_call("FIX Gateway Exiting Forcefully")
    os_exit.assert_called_once_with(-1)


def test_main_block_executes_main_setup_and_main(tmp_path):
    config_file = make_config_file(tmp_path)
    write_preferences(tmp_path)

    def parse_args(*_args, **_kwargs):
        return (make_args(config_file=open(config_file)), [])

    with (
        patch.object(argparse.ArgumentParser, "parse_known_args", side_effect=parse_args),
        patch(
            "fixgw.cfg.from_yaml",
            return_value=({"database file": "{CONFIG}/db.yaml", "connections": {}}, {"connections": {}}),
        ),
        patch("fixgw.database.init"),
        patch("fixgw.database.write"),
        patch("fixgw.status.initialize"),
        patch("logging.getLogger", return_value=MagicMock()),
        patch("logging.basicConfig"),
        patch("signal.signal"),
        patch("fixgw.plugin.jobQueue.get", return_value="QUIT"),
    ):
        runpy.run_path(server.__file__, run_name="__main__")
