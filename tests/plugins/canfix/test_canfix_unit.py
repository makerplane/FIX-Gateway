from unittest.mock import MagicMock

import can
import canfix
import pytest

import fixgw.plugin as pluginbase
import fixgw.plugins.canfix as canfix_plugin
from fixgw.plugins.canfix import mapping


class FakeDBItem:
    def __init__(self, key, value=(0, False, False, False, False, False)):
        self.key = key
        self.value = value
        self.aux_values = {}

    def set_aux_value(self, name, value):
        self.aux_values[name] = value


class FakeBus:
    def __init__(self, messages=None, send_error=None, join_error=None):
        self.messages = list(messages or [])
        self.sent = []
        self.flushed = False
        self.send_error = send_error

    def recv(self, _timeout):
        return self.messages.pop(0) if self.messages else None

    def send(self, msg):
        if self.send_error:
            raise self.send_error
        self.sent.append(msg)

    def flush_tx_buffer(self):
        self.flushed = True


class FakeThread:
    def __init__(self, alive_sequence, join_error=None):
        self.alive_sequence = list(alive_sequence)
        self.join_error = join_error
        self.stopped = False
        self.joined = False

    def stop(self):
        self.stopped = True

    def is_alive(self):
        if len(self.alive_sequence) > 1:
            return self.alive_sequence.pop(0)
        return self.alive_sequence[0]

    def join(self, timeout):
        self.joined = timeout
        if self.join_error:
            raise self.join_error


def make_mapping():
    m = mapping.Mapping.__new__(mapping.Mapping)
    m.meta_replacements_in = {"Minimum": "Min"}
    m.meta_replacements_out = {"Min": "Minimum"}
    m.input_mapping = [None] * 1280
    m.input_nodespecific = [None] * 1536
    m.output_mapping = {}
    m.log = MagicMock()
    m.sendcount = 0
    m.senderrorcount = 0
    m.recvignorecount = 0
    m.recvinvalidcount = 0
    m.ignore_fixid_missing = False
    return m


def test_main_thread_counts_parse_value_errors_and_non_parameters(monkeypatch):
    interesting_msg = can.Message(arbitration_id=0x180, is_extended_id=False)
    interesting_msg.data = bytearray([0, 0, 0])
    non_parameter_msg = can.Message(arbitration_id=0x180, is_extended_id=False)
    non_parameter_msg.data = bytearray([0, 0, 0])

    parent = MagicMock()
    parent.log = MagicMock()
    parent.recvcount = 0
    parent.recvignorecount = 0
    parent.recvinvalidcount = 0
    parent.mapping.input_mapping = [None] * 1280
    parent.mapping.input_mapping[0x80] = [None] * 256
    parent.mapping.input_nodespecific = [None] * 1536
    parent.bus = FakeBus([interesting_msg, non_parameter_msg])
    thread = canfix_plugin.MainThread(parent, {})

    parsed_non_parameter = MagicMock()
    parsed_non_parameter.getName = "not a parameter"
    parse_results = [ValueError("bad frame"), parsed_non_parameter]

    def fake_parse(_msg):
        result = parse_results.pop(0)
        if isinstance(result, Exception):
            raise result
        thread.stop()
        return result

    monkeypatch.setattr(canfix_plugin.canfix, "parseMessage", fake_parse)

    thread.run()

    assert parent.recvcount == 2
    assert parent.recvinvalidcount == 1
    assert parent.recvignorecount == 1
    parent.log.warning.assert_called_once()


def test_plugin_stop_ignores_join_errors_then_raises_if_thread_still_alive():
    pl = canfix_plugin.Plugin.__new__(canfix_plugin.Plugin)
    pl.thread = FakeThread([True, True], join_error=RuntimeError("join failed"))

    with pytest.raises(pluginbase.PluginFail):
        pl.stop()

    assert pl.thread.stopped is True
    assert pl.thread.joined == 1.2


def test_plugin_stop_joins_when_thread_stops_after_join():
    pl = canfix_plugin.Plugin.__new__(canfix_plugin.Plugin)
    pl.thread = FakeThread([True, False])

    pl.stop()

    assert pl.thread.stopped is True
    assert pl.thread.joined == 1.2


def test_plugin_stop_returns_when_thread_is_already_stopped():
    pl = canfix_plugin.Plugin.__new__(canfix_plugin.Plugin)
    pl.thread = FakeThread([False])

    pl.stop()

    assert pl.thread.stopped is True
    assert pl.thread.joined is False


def test_plugin_run_adds_quorum_callback_and_starts_thread(monkeypatch):
    pl = canfix_plugin.Plugin.__new__(canfix_plugin.Plugin)
    pl.channel = "test"
    pl.interface = "virtual"
    pl.node = 7
    pl.thread = MagicMock()
    pl.mapping = MagicMock()
    pl.mapping.output_mapping = {"ALT": {}}
    pl.mapping.getOutputFunction.return_value = "output-callback"
    pl.mapping.getQuorumOutputFunction.return_value = "quorum-callback"
    pl.db_callback_add = MagicMock()
    fake_bus = object()

    monkeypatch.setattr(canfix_plugin.can, "ThreadSafeBus", lambda *a, **k: fake_bus)
    monkeypatch.setattr(canfix_plugin.quorum, "enabled", True)
    monkeypatch.setattr(canfix_plugin.quorum, "vote_key", "QVOTE7")

    pl.run()

    assert canfix.NodeStatus.knownTypes[-1] == ("Quorum", "UINT", 1)
    pl.mapping.getOutputFunction.assert_called_once_with(fake_bus, "ALT", 7)
    pl.mapping.getQuorumOutputFunction.assert_called_once_with(fake_bus, "QVOTE7", 7)
    pl.db_callback_add.assert_any_call("ALT", "output-callback")
    pl.db_callback_add.assert_any_call("QVOTE7", "quorum-callback")
    pl.thread.start.assert_called_once()


def test_input_function_missing_fixid_returns_none(monkeypatch):
    m = make_mapping()
    monkeypatch.setattr(
        mapping.database,
        "get_raw_item",
        lambda key: (_ for _ in ()).throw(KeyError(key)),
    )

    assert m.getInputFunction("MISSING") is None


def test_input_function_logs_aux_write_errors(monkeypatch):
    m = make_mapping()
    db_item = FakeDBItem("ALT")
    db_item.set_aux_value = MagicMock(side_effect=RuntimeError("aux failed"))
    monkeypatch.setattr(mapping.database, "get_raw_item", lambda key: db_item)

    func = m.getInputFunction("ALT")
    par = MagicMock(meta="Minimum", value=10)
    func(par)

    assert m.recvinvalidcount == 1
    m.log.warning.assert_called_once_with("Problem setting Aux Value for ALT")


def test_input_function_counts_missing_parameter_fields(monkeypatch):
    m = make_mapping()
    db_item = FakeDBItem("ALT")
    monkeypatch.setattr(mapping.database, "get_raw_item", lambda key: db_item)

    func = m.getInputFunction("ALT")
    par = canfix.Parameter()
    par.meta = None
    par.value = None
    func(par)

    assert m.recvinvalidcount == 1
    assert db_item.value == (0, False, False, False, False, False)


def test_owner_output_suppresses_old_only_and_duplicate_changes():
    m = make_mapping()
    m.output_mapping["ALT"] = {
        "canid": 0x184,
        "index": 0,
        "owner": True,
        "require_leader": False,
        "on_change": True,
        "exclude": False,
        "lastValue": 100,
        "lastFlags": (False, False, False),
        "lastOld": False,
        "switch": False,
        "fixids": ["ALT"],
    }
    bus = FakeBus()
    func = m.getOutputFunction(bus, "ALT", 1)

    func("ALT", (100, False, True, False, False, False), None)
    func("ALT", (100, False, True, False, False, False), None)

    assert bus.sent == []
    assert m.sendcount == 0


def test_owner_output_send_failure_flushes_bus():
    m = make_mapping()
    m.output_mapping["ALT"] = {
        "canid": 0x184,
        "index": 0,
        "owner": True,
        "require_leader": False,
        "on_change": False,
        "exclude": False,
        "lastValue": None,
        "lastFlags": None,
        "lastOld": None,
        "switch": False,
        "fixids": ["ALT"],
    }
    bus = FakeBus(send_error=RuntimeError("tx full"))
    func = m.getOutputFunction(bus, "ALT", 1)

    func("ALT", (100, False, False, False, False, False), None)

    assert bus.flushed is True
    assert m.senderrorcount == 1
    assert m.sendcount == 1


def test_switch_output_merges_database_bits(monkeypatch):
    m = make_mapping()
    items = {
        "SW1": FakeDBItem("SW1", (True, False, False, False, False, False)),
        "SW2": FakeDBItem("SW2", (False, False, False, False, False, False)),
        "SW3": FakeDBItem("SW3", (True, False, False, False, False, False)),
    }
    m.output_mapping["SW1"] = {
        "canid": 0x309,
        "index": 0,
        "owner": True,
        "require_leader": False,
        "on_change": False,
        "exclude": False,
        "lastValue": None,
        "lastFlags": None,
        "lastOld": None,
        "switch": True,
        "fixids": ["SW1", "SW2", "SW3"],
    }
    monkeypatch.setattr(mapping.database, "get_raw_item", lambda key: items[key])
    bus = FakeBus()
    func = m.getOutputFunction(bus, "SW1", 1)

    func("SW1", (False, False, False, False, False, False), None)

    assert m.output_mapping["SW1"]["lastValue"] == bytearray([0b00000101, 0, 0, 0, 0])
    assert m.sendcount == 1


def test_non_owner_output_duplicate_and_send_failure_paths():
    m = make_mapping()
    m.output_mapping["BARO"] = {
        "canid": 0x190,
        "index": 0,
        "owner": False,
        "require_leader": False,
        "on_change": True,
        "exclude": False,
        "lastValue": 29.92,
        "lastFlags": None,
        "lastOld": None,
        "switch": False,
        "fixids": ["BARO"],
    }
    bus = FakeBus()
    func = m.getOutputFunction(bus, "BARO", 1)

    func("BARO", (29.92, False, False, False, False, False), None)
    assert bus.sent == []

    bus.send_error = RuntimeError("tx full")
    func("BARO", (30.01, False, False, False, False, False), None)
    assert bus.flushed is True
    assert m.senderrorcount == 1
    assert m.sendcount == 0


def test_quorum_output_send_success_and_failure():
    m = make_mapping()
    ok_bus = FakeBus()
    m.getQuorumOutputFunction(ok_bus, "QVOTE1", 1)(
        "QVOTE1", (1, False, False, False, False, False), None
    )
    assert m.sendcount == 1
    assert ok_bus.sent

    fail_bus = FakeBus(send_error=RuntimeError("tx full"))
    m.getQuorumOutputFunction(fail_bus, "QVOTE1", 1)(
        "QVOTE1", (1, False, False, False, False, False), None
    )
    assert m.senderrorcount == 1
    assert fail_bus.flushed is True


def test_encoder_function_adds_values_and_sets_buttons(monkeypatch):
    m = make_mapping()
    items = {
        "ENC1": FakeDBItem("ENC1", (5, False, False, False, False, False)),
        "ENC2": FakeDBItem("ENC2", (7, False, False, False, False, False)),
        "BTN1": FakeDBItem("BTN1"),
        "BTN2": FakeDBItem("BTN2"),
    }
    monkeypatch.setattr(mapping.database, "get_raw_item", lambda key: items[key])
    func = m.getEncoderFunction("ENC1,ENC2,BTN1,BTN2", add=True)
    par = MagicMock(value=[2, 3, [True, False]])

    func(par)

    assert items["ENC1"].value == 7
    assert items["ENC2"].value == 10
    assert items["BTN1"].value is True
    assert items["BTN2"].value is False


def test_encoder_function_handles_single_encoder(monkeypatch):
    m = make_mapping()
    item = FakeDBItem("ENC1", (5, False, False, False, False, False))
    monkeypatch.setattr(mapping.database, "get_raw_item", lambda key: item)
    func = m.getEncoderFunction("ENC1", add=True)
    par = MagicMock(value=[2])

    func(par)

    assert item.value == 7


def test_encoder_function_replaces_values_without_add(monkeypatch):
    m = make_mapping()
    items = {
        "ENC1": FakeDBItem("ENC1", (5, False, False, False, False, False)),
        "ENC2": FakeDBItem("ENC2", (7, False, False, False, False, False)),
    }
    monkeypatch.setattr(mapping.database, "get_raw_item", lambda key: items[key])
    func = m.getEncoderFunction("ENC1,ENC2", add=False)
    par = MagicMock(value=[2, 3])

    func(par)

    assert items["ENC1"].value == 2
    assert items["ENC2"].value == 3


def test_encoder_function_returns_none_when_fixid_missing(monkeypatch):
    m = make_mapping()
    monkeypatch.setattr(
        mapping.database,
        "get_raw_item",
        lambda key: (_ for _ in ()).throw(KeyError(key)),
    )

    assert m.getEncoderFunction("MISSING", add=False) is None


def test_switch_function_updates_toggle_and_output_exclusion(monkeypatch):
    m = make_mapping()
    toggle_item = FakeDBItem("TOGGLE", (False, False, False, False, False, False))
    plain_item = FakeDBItem("PLAIN", (False, False, False, False, False, False))
    items = {"TOGGLE": toggle_item, "PLAIN": plain_item}
    m.output_mapping = {
        "TOGGLE": {"exclude": False, "lastValue": None},
        "PLAIN": {"exclude": False, "lastValue": None},
    }
    monkeypatch.setattr(mapping.database, "get_raw_item", lambda key: items[key])
    func = m.getSwitchFunction("TOGGLE,PLAIN", toggle="TOGGLE")
    par = MagicMock(value=[[True, True]])

    func(par)

    assert toggle_item.value is True
    assert plain_item.value is True
    assert m.output_mapping["TOGGLE"]["exclude"] is True
    assert m.output_mapping["TOGGLE"]["lastValue"] is True
    assert m.output_mapping["PLAIN"]["lastValue"] is True


def test_switch_function_returns_none_when_fixid_missing(monkeypatch):
    m = make_mapping()
    monkeypatch.setattr(
        mapping.database,
        "get_raw_item",
        lambda key: (_ for _ in ()).throw(KeyError(key)),
    )

    assert m.getSwitchFunction("MISSING", toggle=None) is None


def test_input_map_ignores_missing_mapping_and_empty_index():
    m = make_mapping()
    par = canfix.Parameter()
    par.identifier = 0x180
    par.index = 1

    assert m.inputMap(par) is None

    called = []
    m.input_mapping[0x80] = [None] * 256
    m.input_mapping[0x80][1] = lambda p: called.append(p)
    m.inputMap(par)
    assert called == [par]


def test_valid_helpers(monkeypatch):
    m = make_mapping()
    monkeypatch.setattr(mapping.database, "listkeys", lambda: ["ALT"])

    assert m.valid_canid(0x100)
    assert m.valid_canid(0x50, detailed=True) == (
        False,
        "canid must be >= to 256 (0x100)",
    )
    assert m.valid_canid(0x800, detailed=True) == (
        False,
        "canid must be <= to 2015 (0x7df)",
    )
    assert m.valid_canid(0x600, detailed=True) == (
        False,
        "canid must not be between 1536 (0x600) and 1759 (0x6DF)",
    )
    assert m.valid_index(0)
    assert m.valid_index(256, detailed=True) == (
        False,
        "Index should be less than 256 and greater than or equall to 0",
    )
    assert m.valid_fixid("ALT")
    assert not m.valid_fixid("NOPE")


def test_mapping_rejects_missing_mapfile():
    with pytest.raises(ValueError, match="Unable to open mapfile"):
        mapping.Mapping("tests/config/canfix/does-not-exist.yaml")


def test_mapping_switch_reuses_existing_input_bucket(monkeypatch):
    maps = {
        "meta replacements": {"Minimum": "Min"},
        "outputs": [],
        "inputs": [
            {
                "canid": 0x309,
                "index": 1,
                "fixid": "PLAIN",
            }
        ],
        "encoders": [],
        "switches": [
            {
                "canid": 0x309,
                "index": 2,
                "fixid": "SW1",
            }
        ],
    }
    meta = {
        "inputs": [{"canid": {}, "index": {}, "fixid": {}}],
    }
    items = {
        "PLAIN": FakeDBItem("PLAIN"),
        "SW1": FakeDBItem("SW1"),
    }

    monkeypatch.setattr(mapping.os.path, "exists", lambda _path: True)
    monkeypatch.setattr(mapping.cfg, "from_yaml", lambda *_args, **_kwargs: (maps, meta))
    monkeypatch.setattr(mapping.database, "get_raw_item", lambda key: items[key])
    monkeypatch.setattr(mapping.database, "listkeys", lambda: ["PLAIN", "SW1"])

    m = mapping.Mapping("dummy-map.yaml", MagicMock())

    assert m.input_mapping[0x209][1] is not None
    assert m.input_mapping[0x209][2] is not None
