"""AC-21 and R5 through the CLI: a symlinked cur-kit, --version, install into a given home, --here without specify,
and the environment the project's own commands get."""

from __future__ import annotations

import json
import os
import shlex
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BIN = REPO / "bin" / "cur-kit"
COMMAND = shlex.quote(str(BIN))
VERSION = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
DUMP_ENV = "python3 -c \"import json, os; json.dump(dict(os.environ), open('env.json', 'w'))\""


def test_ac21_cur_kit_works_through_a_symlink_from_another_directory(project, tmp_path):
    project.exe = tmp_path / "links" / "cur-kit"
    project.exe.parent.mkdir()
    project.exe.symlink_to(BIN)
    version = project.run("--version", cwd=tmp_path)
    assert version.returncode == 0, version.stderr
    assert VERSION in version.stdout
    assert project.check()["red"] is True


def test_ac21_install_writes_the_hooks_and_the_link_into_the_given_home(kit, tmp_path):
    target = tmp_path / "target-home"
    done = kit.run("install", "--home", str(target))
    assert done.returncode == 0, f"stdout:\n{done.stdout}\nstderr:\n{done.stderr}"
    hooks = json.loads((target / ".cursor" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert hooks["stop"] == [{"command": f"{COMMAND} hook stop --user", "timeout": 900, "loop_limit": 25}]
    assert hooks["sessionStart"] == [{"command": f"{COMMAND} hook session-start", "timeout": 10}]
    assert os.path.samefile(target / ".local" / "bin" / "cur-kit", BIN)
    assert list(Path(kit.env["HOME"]).iterdir()) == []


def test_ac21_here_without_specify_exits_1_with_the_install_hint(kit):
    folders = kit.env["PATH"].split(os.pathsep)
    kit.env["PATH"] = os.pathsep.join(folder for folder in folders if not Path(folder, "specify").exists())
    done = kit.run("--here")
    assert done.returncode == 1
    assert "uv tool install specify-cli" in done.stdout + done.stderr
    assert list(kit.root.iterdir()) == []


@pytest.mark.parametrize("user_path", [None, "/opt/user-lib"])
def test_r5_project_commands_get_the_users_pythonpath_unchanged(project, user_path):
    project.env.pop("PYTHONPATH", None)
    if user_path:
        project.env["PYTHONPATH"] = user_path
    project.configure(test=DUMP_ENV, junit="")
    assert project.check()["ok"] is True
    seen = json.loads((project.root / "env.json").read_text(encoding="utf-8"))
    assert seen.get("PYTHONPATH") == user_path
