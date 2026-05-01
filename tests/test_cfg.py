from fixgw import cfg
import pytest
import yaml
import os
from unittest.mock import patch

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

def test_include_empty_file():
    data = cfg.from_yaml('tests/config/cfg/test_include_empty_file.yaml')
    assert data == {'line': 'one', 'test': {}}

    data,meta = cfg.from_yaml('tests/config/cfg/test_include_empty_file.yaml', metadata=True)
    assert meta == {'line': {'line': 1, 'column': 1, 'file': 'tests/config/cfg/test_include_empty_file.yaml', 'value_meta': {'line': 1, 'column': 7, 'file': 'tests/config/cfg/test_include_empty_file.yaml'}}, '.__test__.': {'line': 2, 'column': 1, 'file': 'tests/config/cfg/test_include_empty_file.yaml', 'value_meta': {'line': 3, 'column': 3, 'file': 'tests/config/cfg/test_include_empty_file.yaml'}}, 'test': {}}


def test_comment_only_string():
    data=cfg.from_yaml('# No yaml here!\n')
    assert data == {}


def test_include_is_bool():
    with pytest.raises(ValueError) as excinfo:
        data=cfg.from_yaml('include: true', fname='tests/config/cfg/bool.yaml')
    assert (
        str(excinfo.value)
        ==
        "include in tests/config/cfg/bool.yaml must be string or array on line 1, column 10 in file 'tests/config/cfg/bool.yaml'"
    )

def test_prefrence_undefined():
    data=cfg.from_yaml('include: PREFER', fname='tests/config/cfg/bool.yaml', preferences={"includes":  {"FOO": "BAR"}} )
    assert data == {}

def test_preference_defined_not_found():
    with pytest.raises(ValueError) as excinfo:
        data=cfg.from_yaml('include: PREFER', fname='tests/config/cfg/bool.yaml', preferences={"includes":  {"PREFER": "BAR"}} )
    assert (
        str(excinfo.value)
        ==
        "Cannot find include: 'BAR' from preferences 'PREFER' on line 1, column 10 in file 'tests/config/cfg/bool.yaml'"
    )


def test_preferences_include_array_falls_back_to_base_path(tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    main_file = subdir / "main.yaml"
    include_file = tmp_path / "preferred.yaml"

    main_file.write_text("include:\n  - WANT\n")
    include_file.write_text("preferred: true\n")

    data = cfg.from_yaml(
        str(main_file),
        bpath=str(tmp_path),
        preferences={"includes": {"WANT": "preferred.yaml"}},
    )

    assert data == {"preferred": True}


def test_include_file_must_be_mapping(tmp_path):
    main_file = tmp_path / "main.yaml"
    include_file = tmp_path / "scalar.yaml"

    main_file.write_text("include: scalar.yaml\n")
    include_file.write_text("valid: yaml\n")

    original_from_yaml = cfg.from_yaml

    def fake_recursive_from_yaml(*args, **kwargs):
        if args and args[0] == str(include_file):
            return ["not", "a", "mapping"], {}
        return original_from_yaml(*args, **kwargs)

    with patch("fixgw.cfg.from_yaml", side_effect=fake_recursive_from_yaml):
        with pytest.raises(Exception, match="Include scalar.yaml .* is invalid"):
            original_from_yaml(str(main_file))


def test_preferences_include_string_finds_file_in_same_directory(tmp_path):
    main_file = tmp_path / "main.yaml"
    include_file = tmp_path / "preferred.yaml"

    main_file.write_text("include: WANT\n")
    include_file.write_text("preferred: true\n")

    data = cfg.from_yaml(
        str(main_file),
        preferences={"includes": {"WANT": "preferred.yaml"}},
    )

    assert data == {"preferred": True}


def test_preferences_include_string_falls_back_to_base_path(tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    main_file = subdir / "main.yaml"
    include_file = tmp_path / "preferred.yaml"

    main_file.write_text("include: WANT\n")
    include_file.write_text("preferred: true\n")

    data = cfg.from_yaml(
        str(main_file),
        bpath=str(tmp_path),
        preferences={"includes": {"WANT": "preferred.yaml"}},
    )

    assert data == {"preferred": True}


def test_list_item_include_uses_preference_fallback_to_base_path(tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    main_file = subdir / "main.yaml"
    include_file = tmp_path / "items.yaml"

    main_file.write_text("items:\n  - include: WANT\n")
    include_file.write_text("items:\n  - one\n  - two\n")

    data = cfg.from_yaml(
        str(main_file),
        bpath=str(tmp_path),
        preferences={"includes": {"WANT": "items.yaml"}},
    )

    assert data == {"items": ["one", "two"]}


def test_list_item_include_uses_preference_file_in_same_directory(tmp_path):
    main_file = tmp_path / "main.yaml"
    include_file = tmp_path / "items.yaml"

    main_file.write_text("items:\n  - include: WANT\n")
    include_file.write_text("items:\n  - one\n")

    data = cfg.from_yaml(
        str(main_file),
        preferences={"includes": {"WANT": "items.yaml"}},
    )

    assert data == {"items": ["one"]}


def test_list_item_include_missing_from_preferences_falls_through_to_open(tmp_path):
    main_file = tmp_path / "main.yaml"
    main_file.write_text("items:\n  - include: WANT\n")

    with pytest.raises(FileNotFoundError):
        cfg.from_yaml(str(main_file), preferences={"includes": {"OTHER": "items.yaml"}})


def test_list_item_include_preference_missing_raises(tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    main_file = subdir / "main.yaml"

    main_file.write_text("items:\n  - include: WANT\n")

    with pytest.raises(NameError):
        cfg.from_yaml(
            str(main_file),
            bpath=str(tmp_path),
            preferences={"includes": {"WANT": "missing.yaml"}},
        )


def test_list_item_include_requires_items_key(tmp_path):
    main_file = tmp_path / "main.yaml"
    include_file = tmp_path / "not_items.yaml"

    main_file.write_text("items:\n  - include: not_items.yaml\n")
    include_file.write_text("other:\n  - one\n")

    with pytest.raises(Exception, match="they need listed under 'items:'"):
        cfg.from_yaml(str(main_file))


def test_list_item_include_with_empty_items_adds_nothing(tmp_path):
    main_file = tmp_path / "main.yaml"
    include_file = tmp_path / "empty_items.yaml"

    main_file.write_text("items:\n  - include: empty_items.yaml\n  - after\n")
    include_file.write_text("items:\n")

    data = cfg.from_yaml(str(main_file))

    assert data == {"items": ["after"]}


def test_plain_mapping_inside_list_preserves_metadata():
    data, meta = cfg.from_yaml(
        fs="items:\n  - name: one\n",
        fname="tests/config/cfg/mapping-list.yaml",
        metadata=True,
    )

    assert data == {"items": [{"name": "one"}]}
    assert meta["items"][0][".__name__."]["line"] == 2
    assert meta["items"][".__0__."]["line"] == 2


def test_list_scalar_metadata_fallback_paths():
    data, meta = cfg.from_yaml(
        fs="items:\n  - one\n  - two\n",
        fname="tests/config/cfg/list.yaml",
        metadata=True,
    )

    assert data == {"items": ["one", "two"]}
    assert meta["items"][0]["line"] == 2
    assert meta["items"][1]["line"] == 3

    data, meta = cfg.from_yaml(
        fs="items: [one, two]",
        fname="tests/config/cfg/flow-list.yaml",
        metadata=True,
    )

    assert data == {"items": ["one", "two"]}
    assert meta["items"][".__0__."]["file"] == "tests/config/cfg/flow-list.yaml"


def test_list_scalar_metadata_direct_cfg_meta_fallbacks():
    data, meta = cfg.from_yaml(
        fs="direct.yaml",
        bpath="",
        cfg={"items": ["one"]},
        cfg_meta={
            "items": {
                ".__0__.": {
                    "line": 3,
                    "column": 5,
                    "file": "direct.yaml",
                    "value_meta": {"line": 3, "column": 5, "file": "direct.yaml"},
                }
            }
        },
        metadata=True,
    )

    assert data == {"items": ["one"]}
    assert meta["items"][".__0__."]["line"] == 3

    data, meta = cfg.from_yaml(
        fs="direct.yaml",
        bpath="",
        cfg={"items": ["one"]},
        cfg_meta={
            "items": {
                "line": 8,
                "column": 2,
                "file": "direct.yaml",
            }
        },
        metadata=True,
    )

    assert data == {"items": ["one"]}
    assert meta["items"][".__0__."]["line"] == 8


def test_message_without_value_uses_wrapped_metadata_entry():
    message = cfg.message(
        "Problem",
        {".__thing__.": {"line": 4, "column": 9, "file": "wrapped.yaml"}},
        "thing",
    )

    assert message == "Problem on line 4, column 9 in file 'wrapped.yaml'"


def test_message_without_value_uses_direct_metadata_entry():
    message = cfg.message(
        "Problem",
        {"thing": {"line": 7, "column": 3, "file": "direct.yaml"}},
        "thing",
    )

    assert message == "Problem on line 7, column 3 in file 'direct.yaml'"
