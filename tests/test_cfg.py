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

def test_cfg_no_preferences_include_samedir_found():
    data = cfg.from_yaml('tests/config/cfg/test_cfg_no_preferences_include_samedir_found.yaml')
    assert data == {'main': {'here': {'is': 'some', 'stuff': 'that', 'can': 'be', 'included': 'where nothing should get included on this line'}}}
    data, meta = cfg.from_yaml('tests/config/cfg/test_cfg_no_preferences_include_samedir_found.yaml', metadata=True)
    assert meta['main']['here']['included']['line'] == 5
    assert meta['main']['here']['included']['column'] == 3
    assert meta['main']['here']['included']['value_meta']['line'] == 5
    assert meta['main']['here']['included']['value_meta']['column'] == 13
    assert meta['main']['here']['included']['value_meta']['file'] == 'tests/config/cfg/found_stuff.yaml'
    assert meta['.__main__.']['file'] == 'tests/config/cfg/test_cfg_no_preferences_include_samedir_found.yaml'



def test_cfg_no_preferences_include_samedir_found_from_string():
    # To cover paths where the yaml is a string not a file or stream
    data = cfg.from_yaml(fs="main:\n  include: found_stuff.yaml", bpath="tests/config/cfg/")
    assert data == {'main': {'here': {'is': 'some', 'stuff': 'that', 'can': 'be', 'included': 'where nothing should get included on this line'}}}
    data, meta = cfg.from_yaml(fs="main:\n  include: found_stuff.yaml", fname='tests/config/cfg/test_cfg_no_preferences_include_samedir_found.yaml', metadata=True)
    assert meta['main']['here']['included']['line'] == 5
    assert meta['main']['here']['included']['column'] == 3
    assert meta['main']['here']['included']['value_meta']['line'] == 5
    assert meta['main']['here']['included']['value_meta']['column'] == 13
    assert meta['main']['here']['included']['value_meta']['file'] == 'tests/config/cfg/found_stuff.yaml'
    assert meta['.__main__.']['file'] == 'tests/config/cfg/test_cfg_no_preferences_include_samedir_found.yaml'

def test_cfg_no_preferences_include_samedir_found_from_stream():
    # To cover paths where the yaml is a stream not a file  or strong
    with open('tests/config/cfg/test_cfg_no_preferences_include_samedir_found.yaml') as stream:
        data = cfg.from_yaml(stream)
        assert data == {'main': {'here': {'is': 'some', 'stuff': 'that', 'can': 'be', 'included': 'where nothing should get included on this line'}}}
    with open('tests/config/cfg/test_cfg_no_preferences_include_samedir_found.yaml') as stream:
        data, meta = cfg.from_yaml(stream, metadata=True)
        assert meta['main']['here']['included']['line'] == 5
        assert meta['main']['here']['included']['column'] == 3
        assert meta['main']['here']['included']['value_meta']['line'] == 5
        assert meta['main']['here']['included']['value_meta']['column'] == 13
        assert meta['main']['here']['included']['value_meta']['file'] == 'tests/config/cfg/found_stuff.yaml'
        assert meta['.__main__.']['file'] == 'tests/config/cfg/test_cfg_no_preferences_include_samedir_found.yaml'


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


def test_cfg_preferences_include_items_missing():
    with pytest.raises(ValueError) as excinfo:
        data = cfg.from_yaml('tests/config/cfg/test_cfg_preferences_include_items_missing.yaml',  preferences=preferences('tests/config/cfg/preferences.yaml'))
    assert (
        str(excinfo.value)
        == "Cannot find include: 'missing.yaml' from preferences 'MISSING' on line 3, column 5 in file 'tests/config/cfg/test_cfg_preferences_include_items_missing.yaml'"
    )

def test_include_loop_detect():
    with pytest.raises(ValueError) as excinfo:
        data = cfg.from_yaml('tests/config/cfg/test_include_loop_detect.yaml')
    assert (
        "==>tests/config/cfg/test_include_loop_detect1.yaml<== was referenced on line 1, column 10 in file '==>tests/config/cfg/test_include_loop_detect3.yaml<=='"
        in
        str(excinfo.value)
    )
