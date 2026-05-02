from unittest.mock import MagicMock

import pytest

import fixgw.plugins.compute as compute


def value_tuple(value, annunciate=False, old=False, bad=False, fail=False, secfail=False):
    return (value, annunciate, old, bad, fail, secfail)


class FakeItem:
    def __init__(self, key, value=0.0):
        self.key = key
        self.value = value
        self.old = False
        self.bad = False
        self.fail = False
        self.secfail = False
        self.aux = {}

    def get_aux_value(self, name):
        return self.aux.get(name)

    def set_aux_value(self, name, value):
        self.aux[name] = value


class FakeParent:
    def __init__(self):
        self.items = {}

    def db_get_item(self, key):
        return self.items.setdefault(key, FakeItem(key))


@pytest.fixture(autouse=True)
def leader(monkeypatch):
    monkeypatch.setattr(compute.quorum, "leader", True)


def test_alt_pressure_forwards_aux_and_combines_flags():
    parent = FakeParent()
    func = compute.altPressure(["BARO", "ALTMSL"], "PALT", require_leader=True)

    func("BARO.Min", 28.0, parent)
    assert parent.db_get_item("PALT").aux["Min"] == 28.0
    func("BARO.Min", 28.0, parent)
    func("ALTMSL.Min", 100.0, parent)
    assert parent.db_get_item("PALT").aux["Min"] == 28.0

    func("BARO", value_tuple(29.92126, old=True, bad=True), parent)
    assert parent.db_get_item("PALT").value == 0.0

    func("ALTMSL", value_tuple(1000.0, fail=True, secfail=True), parent)
    output = parent.db_get_item("PALT")
    assert output.value == 0.0
    assert output.old is True
    assert output.bad is True
    assert output.fail is True
    assert output.secfail is True


def test_alt_pressure_computes_without_failure():
    parent = FakeParent()
    func = compute.altPressure(["BARO", "ALTMSL"], "PALT", require_leader=False)

    func("BARO", value_tuple(29.92126), parent)
    func("ALTMSL", value_tuple(1000.0), parent)

    output = parent.db_get_item("PALT")
    assert output.value == pytest.approx(1000.0)
    assert output.fail is False


def test_alt_density_waits_for_inputs_and_computes_value():
    parent = FakeParent()
    func = compute.altDensity(["PALT", "ALTMSL", "OAT"], "DALT", require_leader=True)

    func("PALT", value_tuple(1000.0), parent)
    assert parent.db_get_item("DALT").value == 0.0

    func("ALTMSL", value_tuple(1000.0), parent)
    func("OAT", value_tuple(25.0), parent)

    assert parent.db_get_item("DALT").value == pytest.approx(2437.6)


@pytest.mark.parametrize(
    "factory,args",
    [
        (compute.altPressure, (["A", "B"], "OUT")),
        (compute.altDensity, (["A", "B", "C"], "OUT")),
        (compute.sumFunction, (["A", "B"], "OUT")),
        (compute.maxFunction, (["A", "B"], "OUT")),
        (compute.minFunction, (["A", "B"], "OUT")),
        (compute.spanFunction, (["A", "B"], "OUT")),
        (compute.AOAFunction, (["PITCH", "IAS", "ANORM", "HEAD", "VS", 2, 3, 100, 100, 50, 5, 5, 3, 3], "OUT")),
    ],
)
def test_aggregate_functions_respect_leader_requirement(factory, args, monkeypatch):
    parent = FakeParent()
    func = factory(*args, require_leader=True)
    monkeypatch.setattr(compute.quorum, "leader", False)

    func(args[0][0], value_tuple(10), parent)

    assert parent.db_get_item("OUT").value == 0.0


def test_average_respects_leader_and_forwards_aux(monkeypatch):
    parent = FakeParent()
    func = compute.averageFunction(["A", "B"], "AVG", require_leader=True)
    monkeypatch.setattr(compute.quorum, "leader", False)

    func("A", value_tuple(10), parent)
    assert parent.db_get_item("AVG").value == 0.0

    monkeypatch.setattr(compute.quorum, "leader", True)
    func("A.Max", 50, parent)
    assert parent.db_get_item("AVG").aux["Max"] == 50

    func("B.Max", 60, parent)
    assert parent.db_get_item("AVG").aux["Max"] == 50

    func("A.Max", 50, parent)
    assert parent.db_get_item("AVG").aux["Max"] == 50


def test_average_combines_values_and_old_flag():
    parent = FakeParent()
    func = compute.averageFunction(["A", "B"], "AVG", require_leader=False)

    func("A", value_tuple(10, old=True), parent)
    func("B", value_tuple(20), parent)

    output = parent.db_get_item("AVG")
    assert output.value == 15
    assert output.old is True


def test_encoder_function_ignores_meta_respects_leader_and_accumulates(monkeypatch):
    parent = FakeParent()
    parent.db_get_item("OUT").value = value_tuple(10)
    func = compute.encoderFunction(["ENC"], "OUT", multiplier=2, require_leader=True)

    func("ENC.Meta", 1, parent)
    assert parent.db_get_item("OUT").value == value_tuple(10)

    monkeypatch.setattr(compute.quorum, "leader", False)
    func("ENC", value_tuple(3), parent)
    assert parent.db_get_item("OUT").value == value_tuple(10)

    monkeypatch.setattr(compute.quorum, "leader", True)
    func("ENC", value_tuple(3), parent)
    assert parent.db_get_item("OUT").value == 16


def test_encoder_function_reraises_type_errors(capsys):
    parent = FakeParent()
    parent.db_get_item("OUT").value = 10
    func = compute.encoderFunction(["ENC"], "OUT", multiplier=2, require_leader=False)

    with pytest.raises(TypeError):
        func("ENC", value_tuple(3), parent)

    assert "WTF Encoder output OUT" in capsys.readouterr().out


def test_set_function_ignores_meta_false_values_and_sets_true_values(monkeypatch):
    parent = FakeParent()
    func = compute.setFunction(["SW"], "MODE", val=7, require_leader=True)

    func("SW.Meta", 1, parent)
    func("SW", value_tuple(False), parent)
    assert parent.db_get_item("MODE").value == 0.0

    monkeypatch.setattr(compute.quorum, "leader", False)
    func("SW", value_tuple(True), parent)
    assert parent.db_get_item("MODE").value == 0.0

    monkeypatch.setattr(compute.quorum, "leader", True)
    func("SW", value_tuple(True), parent)
    assert parent.db_get_item("MODE").value == 7


def test_sum_function_ignores_meta_and_reraises_type_errors(capsys):
    parent = FakeParent()
    func = compute.sumFunction(["A", "B"], "SUM", require_leader=False)

    func("A.Meta", 1, parent)

    with pytest.raises(TypeError):
        func("A", value_tuple("bad"), parent)

    assert "WTF A" in capsys.readouterr().out


def test_sum_function_combines_values_and_quality_flags():
    parent = FakeParent()
    func = compute.sumFunction(["A", "B"], "SUM", require_leader=False)

    func("A", value_tuple(1, old=True, bad=True), parent)
    func("B", value_tuple(2, fail=True, secfail=True), parent)

    output = parent.db_get_item("SUM")
    assert output.value == 0.0
    assert output.old is True
    assert output.bad is True
    assert output.fail is True
    assert output.secfail is True


def test_max_and_min_forward_aux_metadata():
    parent = FakeParent()
    max_func = compute.maxFunction(["A", "B"], "MAX", require_leader=False)
    min_func = compute.minFunction(["A", "B"], "MIN", require_leader=False)

    max_func("A.highWarn", 90, parent)
    min_func("A.lowWarn", 10, parent)
    max_func("A.highWarn", 90, parent)
    min_func("A.lowWarn", 10, parent)
    max_func("B.highWarn", 100, parent)
    min_func("B.lowWarn", 0, parent)

    assert parent.db_get_item("MAX").aux["highWarn"] == 90
    assert parent.db_get_item("MIN").aux["lowWarn"] == 10


def test_alt_density_flag_paths_and_aux_metadata():
    parent = FakeParent()
    func = compute.altDensity(["PALT", "ALTMSL", "OAT"], "DALT", require_leader=False)

    func("PALT.Min", 10, parent)
    assert parent.db_get_item("DALT").aux["Min"] == 10
    func("PALT.Min", 10, parent)
    func("ALTMSL.Min", 20, parent)
    assert parent.db_get_item("DALT").aux["Min"] == 10

    func("PALT", value_tuple(1000, old=True), parent)
    func("ALTMSL", value_tuple(1000, bad=True), parent)
    func("OAT", value_tuple(25, fail=True, secfail=True), parent)

    output = parent.db_get_item("DALT")
    assert output.value == 0.0
    assert output.old is True
    assert output.bad is True
    assert output.fail is True
    assert output.secfail is True


def test_max_and_min_flag_paths():
    parent = FakeParent()
    max_func = compute.maxFunction(["A", "B"], "MAX", require_leader=False)
    min_func = compute.minFunction(["A", "B"], "MIN", require_leader=False)

    max_func("A", value_tuple(0, old=True), parent)
    max_func("B", value_tuple(2, bad=True, fail=True, secfail=True), parent)
    min_func("A", value_tuple(0, old=True), parent)
    min_func("B", value_tuple(-2, bad=True, fail=True, secfail=True), parent)

    assert parent.db_get_item("MAX").value == 0.0
    assert parent.db_get_item("MAX").old is True
    assert parent.db_get_item("MAX").bad is True
    assert parent.db_get_item("MAX").fail is True
    assert parent.db_get_item("MAX").secfail is True
    assert parent.db_get_item("MIN").value == 0.0
    assert parent.db_get_item("MIN").old is True
    assert parent.db_get_item("MIN").bad is True
    assert parent.db_get_item("MIN").fail is True
    assert parent.db_get_item("MIN").secfail is True


def test_span_function_leader_meta_and_flag_paths(monkeypatch):
    parent = FakeParent()
    func = compute.spanFunction(["A", "B"], "SPAN", require_leader=True)
    monkeypatch.setattr(compute.quorum, "leader", False)

    func("A", value_tuple(1), parent)
    assert parent.db_get_item("SPAN").value == 0.0

    monkeypatch.setattr(compute.quorum, "leader", True)
    func("A.Meta", 1, parent)
    func("A", value_tuple(3, old=True), parent)
    func("B", value_tuple(8, bad=True, secfail=True), parent)

    output = parent.db_get_item("SPAN")
    assert output.value == 5
    assert output.old is True
    assert output.bad is True
    assert output.secfail is True


def test_span_function_updates_minimum_and_old_flag():
    parent = FakeParent()
    func = compute.spanFunction(["A", "B", "C"], "SPAN", require_leader=False)

    func("A", value_tuple(5), parent)
    func("B", value_tuple(2, old=True), parent)
    func("C", value_tuple(8), parent)

    output = parent.db_get_item("SPAN")
    assert output.value == 6
    assert output.old is True


def test_aoa_ignores_non_string_keys_and_handles_missing_vs(monkeypatch):
    parent = FakeParent()
    monkeypatch.setattr(compute, "read", lambda key: None)
    func = compute.AOAFunction(
        ["PITCH", "IAS", "ANORM", "HEAD", "VS", 2, 3, 100, 100, 50, 5, 5, 3, 3],
        "AOA",
        require_leader=False,
    )

    func(object(), value_tuple(1), parent)
    assert parent.db_get_item("AOA").value == 0.0

    func("PITCH", value_tuple(4), parent)
    assert parent.db_get_item("AOA").value == 6


def test_aoa_direct_lift_constant_path_propagates_flags(monkeypatch):
    parent = FakeParent()
    reads = {"IAS.Vs": 50, "AOA.0g": -1}
    monkeypatch.setattr(compute, "read", lambda key: reads[key])
    monkeypatch.setattr(compute, "AOA_lift_constant", 10000)
    compute.AOA_ias_history.clear()
    compute.AOA_acc_history.clear()
    func = compute.AOAFunction(
        ["PITCH", "IAS", "ANORM", "HEAD", "VS", 2, 3, 100, 100, 50, 5, 5, 3, 3],
        "AOA",
        require_leader=False,
    )

    func("ANORM", value_tuple(1.5, fail=True, secfail=True), parent)
    func("IAS", value_tuple(100, old=True, bad=True), parent)

    output = parent.db_get_item("AOA")
    assert output.value == pytest.approx(2.5)
    assert output.old is True
    assert output.bad is True
    assert output.fail is True
    assert output.secfail is True


def test_aoa_resets_history_count_for_bad_quality_inputs(monkeypatch):
    parent = FakeParent()
    monkeypatch.setattr(compute, "read", lambda key: 50 if key == "IAS.Vs" else 0)
    compute.AOA_lift_constant = None
    func = compute.AOAFunction(
        ["PITCH", "IAS", "ANORM", "HEAD", "VS", 2, 3, 100, 100, 50, 5, 5, 3, 3],
        "AOA",
        require_leader=False,
    )

    func("PITCH", value_tuple(1, old=True), parent)
    func("IAS", value_tuple(100, bad=True), parent)
    func("ANORM", value_tuple(1, fail=True), parent)
    func("HEAD", value_tuple(90, secfail=True), parent)
    func("VS", value_tuple(0), parent)

    assert parent.db_get_item("AOA").bad is True


@pytest.mark.parametrize(
    "key,flag",
    [
        ("IAS", "bad"),
        ("ANORM", "fail"),
        ("HEAD", "secfail"),
    ],
)
def test_aoa_resets_history_count_for_each_bad_quality_flag(monkeypatch, key, flag):
    parent = FakeParent()
    monkeypatch.setattr(compute, "read", lambda key: 50 if key == "IAS.Vs" else 0)
    compute.AOA_lift_constant = None
    func = compute.AOAFunction(
        ["PITCH", "IAS", "ANORM", "HEAD", "VS", 2, 3, 100, 100, 50, 5, 5, 3, 3],
        "AOA",
        require_leader=False,
    )

    values = {
        "PITCH": value_tuple(1),
        "IAS": value_tuple(100),
        "ANORM": value_tuple(1),
        "HEAD": value_tuple(90),
        "VS": value_tuple(0),
    }
    index = {"bad": 3, "fail": 4, "secfail": 5}[flag]
    values[key] = values[key][:index] + (True,) + values[key][index + 1 :]

    for input_key in ["PITCH", "IAS", "ANORM", "HEAD", "VS"]:
        func(input_key, values[input_key], parent)

    assert parent.db_get_item("AOA").value == 3


def test_aoa_direct_lift_constant_marks_missing_input_failure(monkeypatch):
    parent = FakeParent()
    monkeypatch.setattr(compute, "read", lambda key: 50 if key == "IAS.Vs" else -1)
    monkeypatch.setattr(compute, "AOA_lift_constant", 10000)
    compute.AOA_ias_history[:] = [100]
    compute.AOA_acc_history[:] = [1.5]
    func = compute.AOAFunction(
        ["PITCH", "IAS", "ANORM", "HEAD", "VS", 2, 3, 100, 100, 50, 5, 5, 3, 3],
        "AOA",
        require_leader=False,
    )

    with pytest.raises(TypeError):
        func("PITCH", value_tuple(1), parent)


def test_aoa_updates_existing_lift_constant_with_filter(monkeypatch):
    parent = FakeParent()
    reads = {"IAS.Vs": 50, "AOA.0g": -1}
    monkeypatch.setattr(compute, "read", lambda key: reads[key])
    monkeypatch.setattr(compute, "AOA_lift_constant", 1000)
    for history in [
        compute.AOA_pitch_history,
        compute.AOA_ias_history,
        compute.AOA_acc_history,
        compute.AOA_vs_history,
        compute.AOA_heading_history,
    ]:
        history.clear()
    func = compute.AOAFunction(
        ["PITCH", "IAS", "ANORM", "HEAD", "VS", 2, 1, 100, 100, 50, 5, 5, 3, 3],
        "AOA",
        require_leader=False,
    )

    for _ in range(2):
        func("ANORM", value_tuple(10), parent)
        func("IAS", value_tuple(100), parent)
        func("PITCH", value_tuple(1), parent)
        func("HEAD", value_tuple(350), parent)
        func("VS", value_tuple(0), parent)

    assert compute.AOA_lift_constant != 1000


def test_is_calm_and_wrap_helpers():
    assert compute.is_calm([1, 1, 1], max_sample_dev=0.1, max_trend_dev=0.1)
    assert not compute.is_calm([1, 10, 1], max_sample_dev=0.1, max_trend_dev=0.1)
    assert compute.mean_wrap([350, 10], 360) == 0
    assert compute.mean_wrap([10, 350], 360) == 0
    assert compute.mean_wrap([10, 300], 360) == 335
    assert compute.is_calm([350, 10], max_sample_dev=30, max_trend_dev=30, wrap=360)
    assert compute.abs_wrap(350, 10, 360) == 20
    assert compute.abs_wrap(10, 350, 360) == 20


def test_xte_ignores_meta_respects_leader_and_same_position(monkeypatch):
    parent = FakeParent()
    func = compute.xteFunction(["LAT", "LONG", "WPLAT", "WPLON", "COURSE"], "XTE", True)

    func("LAT.Meta", 1, parent)
    monkeypatch.setattr(compute.quorum, "leader", False)
    func("LAT", value_tuple(0), parent)
    assert parent.db_get_item("XTE").value == 0.0

    monkeypatch.setattr(compute.quorum, "leader", True)
    for key in ["LAT", "LONG", "WPLAT", "WPLON", "COURSE"]:
        func(key, value_tuple(0), parent)

    assert parent.db_get_item("XTE").value == 0.0


def test_xte_propagates_non_fail_quality_flags():
    parent = FakeParent()
    func = compute.xteFunction(["LAT", "LONG", "WPLAT", "WPLON", "COURSE"], "XTE", False)

    values = {
        "LAT": value_tuple(1, old=True),
        "LONG": value_tuple(2, bad=True),
        "WPLAT": value_tuple(0),
        "WPLON": value_tuple(0),
        "COURSE": value_tuple(90, secfail=True),
    }
    for key, value in values.items():
        func(key, value, parent)

    output = parent.db_get_item("XTE")
    assert output.fail is False
    assert output.old is True
    assert output.bad is True
    assert output.secfail is True


def test_plugin_run_registers_special_functions_and_unknown_function():
    pl = compute.Plugin.__new__(compute.Plugin)
    pl.config = {
        "functions": [
            {
                "function": "encoder",
                "inputs": ["ENC", 2],
                "output": "OUT",
                "multiplier": 3,
                "require_leader": False,
            },
            {
                "function": "set",
                "inputs": ["SW"],
                "output": "MODE",
                "value": 7,
                "require_leader": True,
            },
            {
                "function": "sum",
                "inputs": ["A", 123],
                "output": "SUM",
            },
            {
                "function": "mystery",
                "inputs": ["A"],
                "output": "B",
            },
        ]
    }
    pl.db_callback_add = MagicMock()
    pl.log = MagicMock()

    pl.run()

    assert pl.db_callback_add.call_count == 3
    assert pl.db_callback_add.call_args_list[0].args[0] == "ENC"
    assert pl.db_callback_add.call_args_list[1].args[0] == "SW"
    assert pl.db_callback_add.call_args_list[2].args[0] == "A"
    pl.log.warning.assert_called_once_with("Unknown function - mystery")
    pl.stop()
