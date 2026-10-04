"""End-to-end fixtures: temp projects driven only through bin/cur-kit, with a temp HOME."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BIN = REPO / "bin" / "cur-kit"
FEATURE = "specs/001-login"
# The user's git config, Cursor session, and Spec Kit feature must not leak into a temp project.
DROP = ("CURSOR_", "GIT_", "SPECIFY_", "XDG_")
TASKS = """# Tasks: Login

## Phase 3: User Story 1 - Sign in (Priority: P1)

- [ ] T014 [US1] Implement login redirect in src/auth.py

## Phase 4: User Story 2 - Sign out (Priority: P2)

- [ ] T015 [US2] Add logout in src/session.py
"""
SUITE = r'''import pathlib
import sys

fixed = pathlib.Path("fixed").exists()
failure = "" if fixed else "<failure message='no redirect'>AssertionError: 200 != 302</failure>"
case = f"<testcase classname='tests.test_auth' name='test_US1_AC2_redirects'>{failure}</testcase>"
pathlib.Path("report.xml").write_text(f"<testsuites><testsuite name='pytest'>{case}</testsuite></testsuites>\n")
print("1 passed" if fixed else "FAILED tests/test_auth.py::test_US1_AC2_redirects - AssertionError: 200 != 302")
sys.exit(0 if fixed else 1)
'''
FILES = {
    f"{FEATURE}/tasks.md": TASKS,
    ".cursor/cur-kit.json": json.dumps({"test": "python3 suite.py", "junit": "report.xml"}) + "\n",
    "suite.py": SUITE,
    "src/auth.py": "def login():\n    return 200\n",
    "src/session.py": "def logout():\n    return None\n",
}
GIT = (
    ["init", "--quiet"],
    ["config", "user.email", "e2e@example.com"],
    ["config", "user.name", "cur-kit e2e"],
    ["add", "--all"],
    ["commit", "--quiet", "--no-gpg-sign", "--message", "Login feature, red"],
)


def printed_json(done: subprocess.CompletedProcess[str]) -> dict:
    """The JSON a command printed. It must exit 0, red or not."""
    detail = f"exit {done.returncode}\nstdout:\n{done.stdout}\nstderr:\n{done.stderr}"
    assert done.returncode == 0, detail
    try:
        return json.loads(done.stdout)
    except ValueError:
        pytest.fail(f"stdout is not JSON\n{detail}")


@dataclass
class Kit:
    """Runs bin/cur-kit (or a link to it) in one project folder with a fixed env."""

    root: Path
    env: dict[str, str]
    exe: Path = BIN

    def run(self, *args: str, stdin: str = "", cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.exe), *args],
            input=stdin,
            cwd=cwd or self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    def hook(self, event: str, stdin: str) -> dict:
        return printed_json(self.run("hook", event, stdin=stdin))

    def stop(self, loop_count: int = 0, status: str = "completed") -> dict:
        return self.hook("stop", json.dumps({"status": status, "loop_count": loop_count}))

    def check(self) -> dict:
        return printed_json(self.run("check", "--json"))

    def fix(self) -> None:
        (self.root / "fixed").touch()
        (self.root / "src" / "auth.py").write_text("def login():\n    return 302\n", encoding="utf-8")

    def tick(self, task: str) -> None:
        path = self.root / FEATURE / "tasks.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace(f"- [ ] {task} ", f"- [x] {task} "), encoding="utf-8")

    def configure(self, **settings: object) -> None:
        path = self.root / ".cursor" / "cur-kit.json"
        merged = json.loads(path.read_text(encoding="utf-8")) | settings
        path.write_text(json.dumps(merged) + "\n", encoding="utf-8")


@pytest.fixture
def kit(tmp_path: Path) -> Kit:
    """An empty project folder. Every call sets HOME, CURSOR_PROJECT_DIR, and SPECIFY_FEATURE_DIRECTORY."""
    root, home = tmp_path / "project", tmp_path / "home"
    root.mkdir()
    home.mkdir()
    env = {key: value for key, value in os.environ.items() if not key.startswith(DROP)}
    env |= {"HOME": str(home), "CURSOR_PROJECT_DIR": str(root), "SPECIFY_FEATURE_DIRECTORY": FEATURE}
    return Kit(root, env | {"GIT_CONFIG_NOSYSTEM": "1"})


@pytest.fixture
def project(kit: Kit) -> Kit:
    """A committed git project: a bare .specify/, T014 [US1] and T015 [US2] open, and a suite that fails
    test_US1_AC2_redirects until a `fixed` file exists. The JUnit report stays untracked."""
    (kit.root / ".specify").mkdir()
    for rel, text in FILES.items():
        path = kit.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    for args in GIT:
        subprocess.run(["git", *args], cwd=kit.root, env=kit.env, check=True, capture_output=True)
    return kit
