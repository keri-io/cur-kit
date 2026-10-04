from __future__ import annotations

import json

import pytest

from curkit import config
from curkit.config import CONFIG_PATH, Config, commands, detect_test, load


def write_config(root, data) -> None:
    path = root / CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


def test_ac10_config_path_is_cur_kit_json():
    assert CONFIG_PATH == ".cursor/cur-kit.json"
    assert config.CONFIG_PATH == CONFIG_PATH


@pytest.mark.parametrize("text", [None, "[1, 2]", '"pytest -q"', "null", "{not json", ""])
def test_ac10_load_returns_none_for_a_missing_file_or_a_non_object(tmp_path, text):
    if text is not None:
        write_config(tmp_path, text)
    assert load(tmp_path) is None


def test_ac10_load_fills_defaults_and_ignores_unknown_keys(tmp_path):
    write_config(tmp_path, {"test": "pytest -q", "surprise": [1], "lint": "ruff check ."})
    assert load(tmp_path) == Config(
        test="pytest -q", lint="ruff check .", typecheck="", junit="", timeout=300, cache=True
    )


def test_ac10_load_keeps_every_given_value(tmp_path):
    given = {"test": "bun test", "lint": "eslint .", "typecheck": "tsc --noEmit", "junit": "junit.xml",
             "timeout": 90, "cache": False}
    write_config(tmp_path, given)
    assert load(tmp_path) == Config(**given)


@pytest.mark.parametrize("key, value", [
    ("test", None), ("lint", 3), ("junit", ["x"]), ("timeout", "90"), ("timeout", 0), ("timeout", -5),
    ("timeout", True), ("cache", "no"), ("cache", 0),
])
def test_ac10_load_replaces_a_wrong_type_with_the_default(tmp_path, key, value):
    write_config(tmp_path, {key: value})
    assert getattr(load(tmp_path), key) == config.DEFAULTS[key]


def test_ac10_commands_returns_the_non_empty_commands_only():
    cfg = Config(test="pytest -q", lint="  ", typecheck="mypy .", junit="j.xml", timeout=300, cache=True)
    assert commands(cfg) == {"test": "pytest -q", "typecheck": "mypy ."}


@pytest.mark.parametrize("marker", ["pyproject.toml", "pytest.ini", "setup.py"])
def test_ac10_detect_test_returns_pytest_for_python_markers(tmp_path, marker):
    (tmp_path / marker).write_text("", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"scripts": {"test": "jest"}}', encoding="utf-8")
    assert detect_test(tmp_path) == "pytest -q"


@pytest.mark.parametrize("package, expected", [
    ('{"scripts": {"test": "bun test"}}', "bun test"),
    ('{"scripts": {"build": "tsc"}}', ""),
    ('{"scripts": {"test": ""}}', ""),
    ('{"scripts": ["test"]}', ""),
    ("{broken", ""),
    (None, ""),
])
def test_ac10_detect_test_reads_the_package_json_test_script(tmp_path, package, expected):
    if package is not None:
        (tmp_path / "package.json").write_text(package, encoding="utf-8")
    assert detect_test(tmp_path) == expected
