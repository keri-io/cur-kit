from __future__ import annotations

import json
import os

import pytest

from curkit import speckit
from curkit.speckit import active, feature_dir

SCRIPTS = {
    "sh": ".specify/scripts/bash/check-prerequisites.sh",
    "py": ".specify/scripts/python/check_prerequisites.py",
    "ps": ".specify/scripts/powershell/check-prerequisites.ps1",
}
SH = """[ "$*" = "--json --paths-only" ] && [ "$SPECIFY_FEATURE_NO_PERSIST" = 1 ] || exit 9
echo '{"FEATURE_DIR": "%s", "TASKS": "elsewhere/tasks.md"}'
"""
PY = """import sys
if sys.argv[1:] == ["--json", "--paths-only"]:
    print('{"FEATURE_DIR": "specs/002-py"}')
"""
PWSH = """#!/bin/sh
[ "$*" = "-NoProfile -File %s -Json -PathsOnly" ] || exit 9
echo '{"FEATURE_DIR": "specs/003-ps"}'
"""


@pytest.fixture(autouse=True)
def no_feature_env(monkeypatch):
    monkeypatch.delenv("SPECIFY_FEATURE_DIRECTORY", raising=False)


def make_project(root, body, kind):
    script = root / SCRIPTS[kind]
    script.parent.mkdir(parents=True)
    script.write_text(body, encoding="utf-8")
    return script


def test_ac11_active_is_false_without_a_specify_dir(tmp_path):
    (tmp_path / "specify").mkdir()
    assert active(tmp_path) is False


@pytest.mark.parametrize("text", [None, "{}", '{"integration_state_schema": 1}', "{corrupt"])
def test_ac11_active_accepts_a_missing_schema_or_the_integer_one(tmp_path, text):
    (tmp_path / ".specify").mkdir()
    if text is not None:
        (tmp_path / ".specify" / "integration.json").write_text(text, encoding="utf-8")
    assert active(tmp_path) is True


@pytest.mark.parametrize("schema", [2, 0, "1", 1.0, True, None])
def test_ac11_active_rejects_any_other_schema(tmp_path, schema):
    (tmp_path / ".specify").mkdir()
    payload = json.dumps({"integration_state_schema": schema})
    (tmp_path / ".specify" / "integration.json").write_text(payload, encoding="utf-8")
    assert active(tmp_path) is False


def test_ac11_feature_dir_runs_the_sh_script_with_json_paths_only(tmp_path):
    make_project(tmp_path, SH % (tmp_path / "specs" / "001-login"), "sh")
    assert feature_dir(tmp_path) == tmp_path / "specs" / "001-login"


def test_ac11_feature_dir_runs_the_py_script_when_init_options_say_py(tmp_path):
    make_project(tmp_path, SH % "specs/wrong", "sh")
    make_project(tmp_path, PY, "py")
    (tmp_path / ".specify" / "init-options.json").write_text('{"script": "py"}', encoding="utf-8")
    assert feature_dir(tmp_path) == tmp_path / "specs" / "002-py"


def test_ac11_feature_dir_runs_the_ps_script_on_windows(tmp_path, monkeypatch):
    script = make_project(tmp_path, "Write-Output 'unused'", "ps")
    pwsh = tmp_path / "bin" / "pwsh"
    pwsh.parent.mkdir()
    pwsh.write_text(PWSH % script, encoding="utf-8")
    pwsh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{pwsh.parent}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(speckit, "DEFAULT_KIND", "ps")
    assert feature_dir(tmp_path) == tmp_path / "specs" / "003-ps"
