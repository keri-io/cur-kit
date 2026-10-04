from __future__ import annotations

import json

import pytest

from curkit.install import InstallError, install_hooks, link_bin

CMD = "/opt/cur-kit/bin/cur-kit"
STOP = {"command": f"{CMD} hook stop", "timeout": 900, "loop_limit": 25}
START = {"command": f"{CMD} hook session-start", "timeout": 10}
OTHER = {
    "extra": {"keep": True},
    "hooks": {
        "stop": [{"command": "./hooks/tdd_stop.py", "timeout": 120, "loop_limit": 25}],
        "preToolUse": [{"command": "./hooks/pretool.py", "timeout": 10}],
    },
}


def hooks_file(home, text=None):
    path = home / ".cursor" / "hooks.json"
    if text is not None:
        path.parent.mkdir(parents=True)
        path.write_text(text, encoding="utf-8")
    return path


def test_ac16_install_hooks_creates_the_file_when_missing(tmp_path):
    log = install_hooks(tmp_path, CMD)
    data = json.loads(hooks_file(tmp_path).read_text(encoding="utf-8"))
    assert data == {"version": 1, "hooks": {"stop": [STOP], "sessionStart": [START]}}
    assert log == [f"add stop hook: {CMD} hook stop", f"add sessionStart hook: {CMD} hook session-start"]


def test_ac16_install_hooks_keeps_every_other_entry(tmp_path):
    path = hooks_file(tmp_path, json.dumps(OTHER))
    install_hooks(tmp_path, CMD)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 1 and data["extra"] == OTHER["extra"]
    assert data["hooks"]["stop"] == [*OTHER["hooks"]["stop"], STOP]
    assert data["hooks"]["preToolUse"] == OTHER["hooks"]["preToolUse"]
    assert data["hooks"]["sessionStart"] == [START]


def test_ac16_install_hooks_is_idempotent(tmp_path):
    hooks_file(tmp_path, json.dumps(OTHER))
    install_hooks(tmp_path, CMD)
    before = hooks_file(tmp_path).read_bytes()
    log = install_hooks(tmp_path, CMD)
    assert hooks_file(tmp_path).read_bytes() == before
    assert log == [f"skip stop hook: {CMD} hook stop (exists)",
                   f"skip sessionStart hook: {CMD} hook session-start (exists)"]


def test_r6_install_hooks_replaces_an_edited_cur_kit_entry(tmp_path):
    edited = {**STOP, "timeout": 120}
    path = hooks_file(tmp_path, json.dumps({"version": 1, "hooks": {"stop": [edited]}}))
    log = install_hooks(tmp_path, CMD)
    assert json.loads(path.read_text(encoding="utf-8"))["hooks"]["stop"] == [STOP]
    assert log[0] == f"replace stop hook: {CMD} hook stop -> {CMD} hook stop"


@pytest.mark.parametrize("text", ["{broken", "[]", '{"hooks": []}', '{"hooks": {"stop": {}}}'])
def test_ac16_install_hooks_refuses_a_file_it_cannot_merge(tmp_path, text):
    path = hooks_file(tmp_path, text)
    with pytest.raises(InstallError, match="hooks"):
        install_hooks(tmp_path, CMD)
    assert path.read_text(encoding="utf-8") == text


def test_ac16_link_bin_symlinks_local_bin_cur_kit_to_the_target(tmp_path):
    target = tmp_path / "repo" / "bin" / "cur-kit"
    line = link_bin(tmp_path / "home", target)
    link = tmp_path / "home" / ".local" / "bin" / "cur-kit"
    assert link.is_symlink() and link.readlink() == target
    assert line == f"link {link} -> {target}"


def test_ac16_link_bin_is_idempotent_and_repoints_an_old_link(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    link = tmp_path / ".local" / "bin" / "cur-kit"
    link_bin(tmp_path, tmp_path / "old")
    link_bin(tmp_path, tmp_path / "new" / "cur-kit")
    line = link_bin(tmp_path, tmp_path / "new" / "cur-kit")
    assert link.readlink() == tmp_path / "new" / "cur-kit"
    assert line.startswith(f"skip {link}")
    link_bin(tmp_path, link.parent.parent.relative_to(tmp_path) / "relative")
    assert link.readlink() == tmp_path / ".local" / "relative"


def test_ac16_link_bin_leaves_a_regular_file_in_place(tmp_path):
    link = tmp_path / ".local" / "bin" / "cur-kit"
    link.parent.mkdir(parents=True)
    link.write_text("#!/bin/sh\n", encoding="utf-8")
    line = link_bin(tmp_path, tmp_path / "target")
    assert not link.is_symlink() and link.read_text(encoding="utf-8") == "#!/bin/sh\n"
    assert line == f"skip {link} (exists and is not a symlink)"
