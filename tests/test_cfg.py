from fixgw import cfg
import pytest
import yaml
import os

from fixgw.server import merge_dict

def preferences(preference_file):
    preferences = {}
    with open(preference_file) as cf:
        preferences = yaml.safe_load(cf)
    preference_file = preference_file + ".custom"
    # override preferecnes with customizations
    if os.path.exists(preference_file):
        with open(preference_file) as cf:
            custom = yaml.safe_load(cf)
        merge_dict(preferences, custom)
    return preferences


def test_cfg_no_preferences_include_samedir_missing():
    with pytest.raises(ValueError) as excinfo:
        data = cfg.from_yaml('tests/config/cfg/test_cfg_no_preferences_include_samedir_missing.yaml')
    assert (
        str(excinfo.value)
        == "Cannot find include: 'missing.yaml' on line 2, column 12 in file 'tests/config/cfg/test_cfg_no_preferences_include_samedir_missing.yaml'"
    )

def test_cfg_preferences_include_samedir_missing():
    with pytest.raises(ValueError) as excinfo:
        data = cfg.from_yaml('tests/config/cfg/test_cfg_preferences_include_samedir_missing.yaml',
            preferences=preferences('tests/config/cfg/preferences.yaml')
        )
    assert (
        str(excinfo.value)
        == "Cannot find include: 'missing.yaml' from preferences 'MISSING' on line 4, column 12 in file 'tests/config/cfg/test_cfg_preferences_include_samedir_missing.yaml'"
    )

def _cfg_no_preferences_include_in_array_samedir_missing():
    with pytest.raises(ValueError) as excinfo:
        data = cfg.from_yaml('tests/config/cfg/include_not_found_in_array.yaml')
    assert (
        str(excinfo.value)
        == "Cannot find include: 'missing.yaml' on line 2, column 12 in file 'tests/config/cfg/include_not_found_in_array.yaml'"
    )

def test_cfg_no_preferences_include_subfolder_in_array_samedir_missing():
    with pytest.raises(ValueError) as excinfo:
        data = cfg.from_yaml('tests/config/cfg/test_cfg_no_preferences_include_subfolder_in_array_samedir_missing.yaml') #, preferences='tests/config/cfg/preferences.yaml')
    assert (
        str(excinfo.value)
        == "Cannot find include: 'missing.yaml' on line 2, column 12 in file 'tests/config/cfg/subfolder/include_not_found_in_array.yaml'"
    )

def test_cfg_preferences_include_subfolder_in_array_samedir_missing():
    with pytest.raises(ValueError) as excinfo:
        data = cfg.from_yaml('tests/config/cfg/test_cfg_preferences_include_subfolder_in_array_samedir_missing.yaml', preferences=preferences('tests/config/cfg/preferences.yaml'))
    assert (
        str(excinfo.value)
        == "Cannot find include: 'missing.yaml' from preferences 'MISSING' on line 2, column 12 in file 'tests/config/cfg/test_cfg_preferences_include_subfolder_in_array_samedir_missing.yaml'"
    )


def test_cfg_no_preferences_include_items_missing():
    with pytest.raises(ValueError) as excinfo:
        data = cfg.from_yaml('tests/config/cfg/test_cfg_no_preferences_include_items_missing.yaml')
    assert (
        str(excinfo.value)
        == "Cannot find include: 'missing.yaml' on line 3, column 5 in file 'tests/config/cfg/test_cfg_no_preferences_include_items_missing.yaml'"
    )

