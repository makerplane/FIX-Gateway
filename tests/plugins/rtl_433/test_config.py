import pytest
from fixgw.plugins.rtl_433 import valid_decoder, valid_type, validate_config
from fixgw import cfg
from unittest.mock import MagicMock
import re


@pytest.mark.parametrize(
    "replace, value, message",
    [
        (
            "TIRE_PRESSURE1",
            "DOESNOTEXIST",
            "'DOESNOTEXIST' is not a valid fixid on line 12, column 13 in file 'test.yaml'",
        ),
        (
            "decoder: 203",
            "decoder: 999999",
            "'999999' is not a valid decoder id on line 9, column 18 in file 'test.yaml'",
        ),
        (
            'type: "float"',
            'type: "flot"',
            "'flot' is not a valid type on line 15, column 19 in file 'test.yaml'",
        ),
        (
            'source: "pressure_kPa"',
            "",
            "'source' must be specified in mapping on line 13, column 13 in file 'test.yaml'",
        ),
        (
            "scale: 0.145032632",
            'scale: "0.145032632"',
            "'scale' must be an integer or float on line 13, column 20 in file 'test.yaml'",
        ),
        (
            "round: 0",
            'round: "0"',
            "'round' must be an integer on line 19, column 20 in file 'test.yaml'",
        ),
        (
            "round: 0",
            "round: 5",
            "'round' must be 0, 1, 2, 3 or 4 on line 19, column 20 in file 'test.yaml'",
        ),
        (
            "offset: -40",
            'offset: "-40"',
            "'-40' must be a float or int on line 18, column 21 in file 'test.yaml'",
        ),
        (
            "threshold: 2.0",
            'threshold: "2.0"',
            "'2.0' must be a float or int on line 23, column 24 in file 'test.yaml'",
        ),
        (
            'offset: -40\n            round: 0\n            type: "float"',
            'offset: "-40"\n            round: 0',
            "'-40' must be a float or int on line 18, column 21 in file 'test.yaml'",
        ),
    ],
)
def test_validate_config(rtl_433_config, replace, value, message):
    with pytest.raises(ValueError) as excinfo:
        config, config_meta = cfg.from_yaml(
            re.sub(replace, value, rtl_433_config), metadata=True, fname="test.yaml"
        )
        parent = MagicMock()
        parent.config = config
        parent.config_meta = config_meta
        parent.db_list.return_value = ["TIRE_PRESSURE1", "TIRE_TEMP1", "TIRE_BATOK1"]
        validate_config(parent)

    assert str(excinfo.value) == message
