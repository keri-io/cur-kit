from __future__ import annotations

from pathlib import Path

import pytest

import curkit
from curkit import config
from curkit.here import seed
from curkit.project_hooks import START_COMMAND, STOP_COMMAND, WRAPPER

TEMPLATES = Path(curkit.__file__).parent / "templates"
AGENTS = ["scout", "writer", "witness", "reviewer", "diagnose"]
COPIES = {f".cursor/agents/cur-kit-{name}.md": f"agents/cur-kit-{name}.md" for name in AGENTS}
COPIES |= {".cursor/rules/cur-kit.mdc": "rules/cur-kit.mdc", ".cursor/cur-kit/workflow.yml": "workflow.yml"}
STATE = ".cursor/cur-kit/state/"
HOOKS = [f"add {WRAPPER}", f"add stop hook: {STOP_COMMAND}", f"add sessionStart hook: {START_COMMAND}"]


def project(tmp_path):
    root = tmp_path / "project"
    (root / ".specify").mkdir(parents=True)
    return root


def snapshot(root):
    folders = [root / ".specify", root / ".cursor" / "skills"]
    return {path: path.read_bytes() for folder in folders for path in folder.rglob("*") if path.is_file()}


def no_run(argv, **kwargs):
    pytest.fail(f"seed ran {argv} in a project that already has .specify/")


def test_ac13_seed_writes_the_config_agents_rule_and_workflow(tmp_path):
    root = project(tmp_path)
    (root / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    log = seed(root, runner=no_run)
    assert log == ["add .cursor/cur-kit.json", *(f"add {rel}" for rel in COPIES), *HOOKS, f"add {STATE} to .gitignore"]
    assert (root / WRAPPER).read_bytes() == (TEMPLATES / "hooks" / "cur-kit").read_bytes()
    assert config.load(root) == config.Config(config.PYTEST, "", "", "", 300, True)
    for rel, name in COPIES.items():
        assert (root / rel).read_bytes() == (TEMPLATES / name).read_bytes()


def test_ac13_seed_never_overwrites_a_file_or_a_dangling_link(tmp_path):
    root = project(tmp_path)
    mine = root / ".cursor" / "cur-kit.json"
    mine.parent.mkdir()
    mine.write_text('{"test": "make check"}', encoding="utf-8")
    rule = root / ".cursor" / "rules" / "cur-kit.mdc"
    rule.parent.mkdir()
    rule.symlink_to(tmp_path / "nowhere.mdc")
    log = seed(root, runner=no_run)
    assert mine.read_text(encoding="utf-8") == '{"test": "make check"}'
    assert rule.is_symlink() and not (tmp_path / "nowhere.mdc").exists()
    assert {"skip .cursor/cur-kit.json (exists)", "skip .cursor/rules/cur-kit.mdc (exists)"} <= set(log)
    assert all(line.startswith("skip ") for line in seed(root, runner=no_run))


def test_ac13_seed_appends_the_state_dir_to_gitignore_once(tmp_path):
    root = project(tmp_path)
    (root / ".gitignore").write_text("node_modules", encoding="utf-8")
    seed(root, runner=no_run)
    log = seed(root, runner=no_run)
    assert (root / ".gitignore").read_text(encoding="utf-8") == f"node_modules\n{STATE}\n"
    assert log[-1] == f"skip .gitignore (lists {STATE})"


def test_ac13_seed_creates_gitignore_when_missing(tmp_path):
    root = project(tmp_path)
    seed(root, runner=no_run)
    assert (root / ".gitignore").read_text(encoding="utf-8") == f"{STATE}\n"


def test_ac13_seed_never_touches_specify_or_cursor_skills(tmp_path):
    root = project(tmp_path)
    (root / ".specify" / "integration.json").write_text('{"integration_state_schema": 1}', encoding="utf-8")
    skill = root / ".cursor" / "skills" / "speckit-implement" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# implement\n", encoding="utf-8")
    before = snapshot(root)
    seed(root, runner=no_run)
    seed(root, runner=no_run)
    assert snapshot(root) == before
