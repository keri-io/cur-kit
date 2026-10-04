from __future__ import annotations

import pytest

from curkit import speckit
from curkit.speckit import feature_dir, tasks_path

GOOD = """echo '{"FEATURE_DIR": "specs/001-login"}'\n"""
BAD = [
    None,
    "exit 3",
    "exec sleep 5",
    "echo 'not json'",
    "echo '[1]'",
    "echo '{}'",
    """echo '{"FEATURE_DIR": "  "}'""",
    """echo '{"FEATURE_DIR": 7}'""",
]


@pytest.fixture(autouse=True)
def quick_and_unset(monkeypatch):
    monkeypatch.delenv("SPECIFY_FEATURE_DIRECTORY", raising=False)
    monkeypatch.setattr(speckit, "TIMEOUT", 0.5)


def make_project(root, body):
    (root / ".specify").mkdir()
    if body is not None:
        script = root / ".specify" / "scripts" / "bash" / "check-prerequisites.sh"
        script.parent.mkdir(parents=True)
        script.write_text(body, encoding="utf-8")


@pytest.mark.parametrize("body", BAD)
def test_ac11_feature_dir_is_none_when_the_script_is_missing_fails_times_out_or_has_no_feature_dir(tmp_path, body):
    make_project(tmp_path, body)
    assert feature_dir(tmp_path) is None


@pytest.mark.parametrize("options", ['{"script": "zsh"}', '{"script": ["sh"]}'])
def test_ac11_feature_dir_is_none_for_an_unknown_script_kind(tmp_path, options):
    make_project(tmp_path, GOOD)
    (tmp_path / ".specify" / "init-options.json").write_text(options, encoding="utf-8")
    assert feature_dir(tmp_path) is None


def test_ac11_specify_feature_directory_wins_when_set(tmp_path, monkeypatch):
    make_project(tmp_path, GOOD)
    monkeypatch.setenv("SPECIFY_FEATURE_DIRECTORY", "specs/009-env")
    assert feature_dir(tmp_path) == tmp_path / "specs" / "009-env"
    monkeypatch.setenv("SPECIFY_FEATURE_DIRECTORY", str(tmp_path / "abs"))
    assert feature_dir(tmp_path) == tmp_path / "abs"
    monkeypatch.setenv("SPECIFY_FEATURE_DIRECTORY", "  ")
    assert feature_dir(tmp_path) == tmp_path / "specs" / "001-login"


def test_ac11_feature_dir_is_none_when_spec_kit_is_inactive(tmp_path, monkeypatch):
    make_project(tmp_path, GOOD)
    (tmp_path / ".specify" / "integration.json").write_text('{"integration_state_schema": 2}', encoding="utf-8")
    assert feature_dir(tmp_path) is None
    monkeypatch.setenv("SPECIFY_FEATURE_DIRECTORY", "specs/009-env")
    assert feature_dir(tmp_path) is None


def test_ac11_tasks_path_is_tasks_md_in_the_feature_dir(tmp_path):
    make_project(tmp_path, GOOD)
    assert tasks_path(tmp_path) is None
    tasks = tmp_path / "specs" / "001-login" / "tasks.md"
    tasks.parent.mkdir(parents=True)
    tasks.write_text("- [ ] T001 Do it\n", encoding="utf-8")
    assert tasks_path(tmp_path) == tasks


def test_ac11_tasks_path_is_none_without_a_feature_dir(tmp_path):
    make_project(tmp_path, None)
    assert tasks_path(tmp_path) is None
