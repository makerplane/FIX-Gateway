from unittest.mock import MagicMock

import pytest

import fixgw.plugins.mgl as mgl
from fixgw.plugins.mgl import Plugin
from fixgw.plugins.mgl import rdac
from fixgw.plugins.mgl import tables


class FakeCanMessage:
    def __init__(self, arbitration_id, data):
        self.arbitration_id = arbitration_id
        self.data = data


class FakeRecvBus:
    def __init__(self, owner, messages):
        self.owner = owner
        self.messages = list(messages)

    def recv(self, timeout):
        assert timeout == 1.0
        if self.messages:
            return self.messages.pop(0)
        self.owner.getout = True
        return None


class FakeSendBus:
    def __init__(self, owner):
        self.owner = owner
        self.sent = []

    def send(self, message, timeout):
        self.sent.append((message, timeout))
        self.owner.getout = True


def arb_id(host, msg_id):
    return (host << 4) | msg_id


def word(value):
    return int(value).to_bytes(2, "little", signed=False)


def sint(value):
    return int(value).to_bytes(2, "little", signed=True)


def make_parent():
    parent = MagicMock()
    parent.log = MagicMock()
    parent.recvcount = 0
    parent.wantcount = 0
    parent.errorcount = 0
    return parent


def test_tables_rdac_is_available():
    assert tables.rdac["RPM1"]["msg_id"] == 8


def test_mgl_struct_decodes_host_and_message_id():
    decoded = rdac.MGLStruct()

    rdac.struct.pack_into("!I", decoded, 0, arb_id(32, 5))

    assert decoded.host == 32
    assert decoded.msg_id == 5


def test_get_builds_configured_rdac_item_map():
    parent = make_parent()
    config = {
        "default_id": 1,
        "get": {
            "oil": {"key": "OILT"},
            "rpm": {"id": 2, "key": "RPM1"},
        },
    }

    getter = rdac.Get(parent, config)

    assert getter.rdac_get_items[32][5]["OILT"]["key"] == "oil"
    assert getter.rdac_get_items[33][8]["RPM1"]["key"] == "rpm"


def test_get_run_filters_unwanted_frames_and_decodes_core_values():
    parent = make_parent()
    config = {
        "default_id": 1,
        "get": {
            "oil_temp": {"key": "OILT"},
            "oil_pressure": {"key": "OILP", "calibration": [(0, 0), (100, 1000)]},
        },
    }
    getter = rdac.Get(parent, config)
    payload = word(123) + word(500) + word(0) + word(0)
    getter.bus = FakeRecvBus(
        getter,
        [
            FakeCanMessage(arb_id(99, 5), payload),
            FakeCanMessage(arb_id(32, 1), payload),
            FakeCanMessage(arb_id(32, 5), payload),
        ],
    )
    parent.bus = getter.bus

    getter.run()

    assert parent.recvcount == 3
    assert parent.wantcount == 2
    parent.db_write.assert_any_call("oil_temp", 123)
    parent.db_write.assert_any_call("oil_pressure", 50.0)


def test_get_run_decodes_temperature_compensation_voltage_and_rpm_scaling():
    parent = make_parent()
    config = {
        "default_id": 1,
        "get": {
            "rdac_temp": {"key": "RDACTEMP"},
            "rdac_volt": {"key": "RDACVOLT"},
            "tc1": {"key": "TC1"},
            "rpm1": {"key": "RPM1"},
        },
    }
    getter = rdac.Get(parent, config)
    msg7 = FakeCanMessage(arb_id(32, 7), sint(10) + sint(1000) + word(0) + word(0))
    msg2 = FakeCanMessage(arb_id(32, 2), sint(-5) + word(0) + word(0) + word(0))
    msg8 = FakeCanMessage(arb_id(32, 8), word(51000) + word(0) + word(0) + word(0))
    getter.bus = FakeRecvBus(getter, [msg7, msg2, msg8])
    parent.bus = getter.bus

    getter.run()

    parent.db_write.assert_any_call("rdac_temp", 10)
    parent.db_write.assert_any_call("rdac_volt", 17.43)
    parent.db_write.assert_any_call("tc1", 5)
    parent.db_write.assert_any_call("rpm1", 60000)


def test_get_run_covers_error_marker_low_rpm_and_initial_getout(monkeypatch):
    parent = make_parent()
    config = {
        "default_id": 1,
        "get": {
            "rpm1": {"key": "RPM1"},
            "oil_temp": {"key": "OILT"},
        },
    }
    getter = rdac.Get(parent, config)
    monkeypatch.setitem(rdac.tables.rdac, "error", 123)
    getter.bus = FakeRecvBus(
        getter,
        [
            FakeCanMessage(arb_id(32, 8), word(2400) + word(0) + word(0) + word(0)),
            FakeCanMessage(arb_id(32, 5), word(123) + word(0) + word(0) + word(0)),
        ],
    )
    parent.bus = getter.bus

    getter.run()

    parent.db_write.assert_any_call("rpm1", 2400)
    parent.db_write.assert_any_call("oil_temp", 123)

    idle_getter = rdac.Get(parent, {"get": {}})
    idle_getter.getout = True
    idle_getter.run()


def test_get_stop_sets_getout_and_swallows_join_errors(monkeypatch):
    parent = make_parent()
    getter = rdac.Get(parent, {"get": {}})
    monkeypatch.setattr(getter, "join", MagicMock(side_effect=RuntimeError("not started")))

    getter.stop()

    assert getter.getout is True


def test_send_registers_callbacks_and_updates_values():
    parent = make_parent()
    sender = rdac.Send(
        parent,
        {
            "default_id": 1,
            "send": {
                "rpm_fix": {"key": "RPM1"},
                "tc_fix": {"id": 2, "key": "TC1"},
            },
        },
    )

    assert 1 in sender.rdac_ids
    assert 2 in sender.rdac_ids
    assert parent.db_callback_add.call_count == 2

    callback = sender.getOutputFunction(200, 8, "RPM1")
    callback("rpm_fix", (2500,), None)

    assert sender.rdac_send_items[200][8]["RPM1"] == 2500


def test_send_run_packs_signed_and_unsigned_values(monkeypatch):
    parent = make_parent()
    sender = rdac.Send(parent, {"default_id": 1, "send": {"rpm_fix": {"key": "RPM1"}}})
    sender.rdac_frequencies = {200: 0}
    sender.rdac_send_items = {200: {8: {"RPM1": 2500, "CURRNT": 12}}}
    bus = FakeSendBus(sender)
    parent.bus = bus
    monkeypatch.setattr(rdac.time, "sleep", MagicMock())
    monkeypatch.setattr(rdac.time, "time_ns", MagicMock(return_value=10**12))

    sender.run()

    message, timeout = bus.sent[0]
    assert timeout == 0.2
    assert message.arbitration_id == int("0x208", 16)
    assert message.data[0:2] == word(2500)
    assert message.data[6:8] == word(12)


def test_send_run_waits_until_frequency_is_due(monkeypatch):
    parent = make_parent()
    sender = rdac.Send(parent, {"default_id": 1, "send": {"rpm_fix": {"key": "RPM1"}}})
    sender.rdac_frequencies = {200: 10**9}
    sender.rdac_send_items = {200: {8: {"RPM1": 2500}}}
    bus = FakeSendBus(sender)
    parent.bus = bus
    now = iter([0, 0, 10**18, 10**18, 10**18])
    monkeypatch.setattr(rdac.time, "sleep", MagicMock())
    monkeypatch.setattr(rdac.time, "time_ns", MagicMock(side_effect=lambda: next(now)))

    sender.run()

    assert len(bus.sent) == 1


def test_send_run_exits_when_getout_is_already_set(monkeypatch):
    parent = make_parent()
    sender = rdac.Send(parent, {"send": {}})
    sender.getout = True
    parent.bus = MagicMock()
    monkeypatch.setattr(rdac.time, "sleep", MagicMock())

    sender.run()


def test_send_stop_sets_getout_and_joins(monkeypatch):
    parent = make_parent()
    sender = rdac.Send(parent, {"send": {}})
    join = MagicMock()
    monkeypatch.setattr(sender, "join", join)

    sender.stop()

    assert sender.getout is True
    join.assert_called_once_with()


def test_plugin_constructs_configured_threads_and_runs_bus(monkeypatch):
    get_thread = MagicMock()
    send_thread = MagicMock()
    monkeypatch.setattr(mgl.rdac, "Get", MagicMock(return_value=get_thread))
    monkeypatch.setattr(mgl.rdac, "Send", MagicMock(return_value=send_thread))
    bus_factory = MagicMock(return_value="bus")
    monkeypatch.setattr(mgl.can, "ThreadSafeBus", bus_factory)

    plugin = Plugin(
        "mgl-test",
        {
            "interface": "socketcan",
            "channel": "can0",
            "rdac": {"get": {"oil": {"key": "OILT"}}, "send": {"rpm": {"key": "RPM1"}}},
        },
        {},
    )
    plugin.run()

    assert plugin.threads == [get_thread, send_thread]
    bus_factory.assert_called_once_with("can0", interface="socketcan")
    get_thread.start.assert_called_once_with()
    send_thread.start.assert_called_once_with()


def test_plugin_handles_missing_or_disabled_rdac_sections():
    no_rdac = Plugin(
        "mgl-test",
        {"interface": "socketcan", "channel": "can0"},
        {},
    )
    disabled_rdac = Plugin(
        "mgl-test",
        {"interface": "socketcan", "channel": "can0", "rdac": {}},
        {},
    )

    assert no_rdac.threads == []
    assert disabled_rdac.threads == []
    no_rdac.stop()


def test_plugin_stop_joins_threads_and_raises_for_stubborn_thread():
    plugin = Plugin(
        "mgl-test",
        {"interface": "socketcan", "channel": "can0"},
        {},
    )
    ok_thread = MagicMock()
    ok_thread.is_alive.return_value = False
    bad_thread = MagicMock()
    bad_thread.is_alive.return_value = True
    plugin.threads = [ok_thread, bad_thread]

    with pytest.raises(mgl.plugin.PluginFail):
        plugin.stop()

    ok_thread.stop.assert_called_once_with()
    bad_thread.join.assert_called_once_with(1.0)


def test_plugin_status_reports_counts():
    plugin = Plugin(
        "mgl-test",
        {"interface": "socketcan", "channel": "can0"},
        {},
    )
    plugin.recvcount = 3
    plugin.wantcount = 2
    plugin.errorcount = 1

    status = plugin.get_status()

    assert status["CAN Interface"] == "socketcan"
    assert status["CAN Channel"] == "can0"
    assert status["Received Frames"] == 3
    assert status["Wanted Frames"] == 2
    assert status["Error Count"] == 1
