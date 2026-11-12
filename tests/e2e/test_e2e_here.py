"""AC-22: a real `cur-kit --here` in an empty folder runs `specify init` and seeds the wrapper files."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.skipif(shutil.which("specify") is None, reason="specify is not on PATH")

INIT = ["specify", "init", "--here", "--integration", "cursor-agent", "--non-interactive"]
MODELS = {
    "scout": "grok-4.7-high",
    "writer": "grok-4.7-high",
    "witness": "grok-4.7-high",
    "reviewer": "grok-4.7[effort=xhigh,context=500k]",
    "diagnose": "grok-4.7-medium",
}
WRAPPER = [
    ".cursor/cur-kit.json",
    *(f".cursor/agents/cur-kit-{name}.md" for name in MODELS),
    ".cursor/rules/cur-kit.mdc",
    ".cursor/cur-kit/workflow.yml",
    ".cursor/hooks.json",
    ".cursor/hooks/cur-kit",
]


def files_under(folder):
    return {str(path.relative_to(folder)): path.read_bytes() for path in folder.rglob("*") if path.is_file()}


@pytest.fixture
def seeded(kit):
    done = kit.run("--here")
    assert done.returncode == 0, f"stdout:\n{done.stdout}\nstderr:\n{done.stderr}"
    return kit


def test_ac22_here_runs_specify_init_and_seeds_the_wrapper_files(seeded):
    integration = json.loads((seeded.root / ".specify" / "integration.json").read_text(encoding="utf-8"))
    assert integration["integration"] == "cursor-agent"
    assert [rel for rel in WRAPPER if not (seeded.root / rel).is_file()] == []
    assert ".cursor/cur-kit/state/" in (seeded.root / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_ac22_here_seeds_agent_files_that_set_their_own_model(seeded):
    for name, model in MODELS.items():
        text = (seeded.root / ".cursor" / "agents" / f"cur-kit-{name}.md").read_text(encoding="utf-8")
        assert f"\nmodel: {model}\n" in text, name


def test_ac22_here_leaves_the_speckit_skills_as_spec_kit_writes_them(seeded, tmp_path):
    reference = tmp_path / "reference"
    reference.mkdir()
    subprocess.run(INIT, cwd=reference, env=seeded.env, check=True, capture_output=True, timeout=120)
    skills = files_under(seeded.root / ".cursor" / "skills")
    assert skills and skills == files_under(reference / ".cursor" / "skills")
    assert all(rel.startswith("speckit-") for rel in skills)


def test_ac22_here_project_runs_nothing_until_test_is_set(seeded):
    settings = json.loads((seeded.root / ".cursor" / "cur-kit.json").read_text(encoding="utf-8"))
    assert settings["test"] == ""
    assert seeded.check()["configured"] is False
    assert seeded.stop() == {}
