from __future__ import annotations

import json
import shlex

from curkit.install import install_hooks

SPACED = "/home/me/My Work/cur-kit/bin/cur-kit"
QUOTED = shlex.quote(SPACED)
OLD = "/old/place/cur-kit/bin/cur-kit"
KEEP_A = {"command": "./hooks/tdd_stop.py", "timeout": 120, "loop_limit": 25}
KEEP_B = {"command": "./hooks/mnemos_stop.py", "timeout": 20}
PROMPT = {"type": "prompt", "prompt": "Check the diff."}
OTHER_EVENT = {"command": f"{OLD} hook stop", "timeout": 5}


def read(home):
    return json.loads((home / ".cursor" / "hooks.json").read_text(encoding="utf-8"))["hooks"]


def test_r6_install_hooks_shell_quotes_the_command(tmp_path):
    install_hooks(tmp_path, SPACED)
    hooks = read(tmp_path)
    assert hooks["stop"][0]["command"] == f"'{SPACED}' hook stop"
    assert shlex.split(hooks["stop"][0]["command"]) == [SPACED, "hook", "stop"]
    assert shlex.split(hooks["sessionStart"][0]["command"]) == [SPACED, "hook", "session-start"]


def test_r6_install_hooks_replaces_old_cur_kit_entries_for_the_same_event(tmp_path):
    path = tmp_path / ".cursor" / "hooks.json"
    path.parent.mkdir()
    stale = [{"command": f"{OLD} hook stop", "timeout": 120}, {"command": f"{SPACED} hook stop"}]
    path.write_text(json.dumps({"version": 1, "hooks": {
        "stop": [KEEP_A, stale[0], KEEP_B, stale[1], PROMPT],
        "sessionStart": [{"command": f"{OLD} hook session-start", "timeout": 10}],
        "preToolUse": [OTHER_EVENT],
    }}), encoding="utf-8")
    log = install_hooks(tmp_path, SPACED)
    hooks = read(tmp_path)
    assert hooks["stop"] == [KEEP_A, {"command": f"{QUOTED} hook stop", "timeout": 900, "loop_limit": 25}, KEEP_B, PROMPT]
    assert hooks["sessionStart"] == [{"command": f"{QUOTED} hook session-start", "timeout": 10}]
    assert hooks["preToolUse"] == [OTHER_EVENT]
    assert log == [f"replace stop hook: {OLD} hook stop, {SPACED} hook stop -> {QUOTED} hook stop",
                   f"replace sessionStart hook: {OLD} hook session-start -> {QUOTED} hook session-start"]


def test_r6_install_hooks_stays_idempotent_after_a_replace(tmp_path):
    install_hooks(tmp_path, OLD)
    install_hooks(tmp_path, SPACED)
    before = (tmp_path / ".cursor" / "hooks.json").read_bytes()
    log = install_hooks(tmp_path, SPACED)
    assert (tmp_path / ".cursor" / "hooks.json").read_bytes() == before
    assert log == [f"skip stop hook: {QUOTED} hook stop (exists)",
                   f"skip sessionStart hook: {QUOTED} hook session-start (exists)"]
    assert [len(entries) for entries in read(tmp_path).values()] == [1, 1]


def test_r6_install_hooks_stays_idempotent_for_a_command_outside_a_bin_directory(tmp_path):
    install_hooks(tmp_path, "cur-kit")
    assert install_hooks(tmp_path, "cur-kit") == ["skip stop hook: cur-kit hook stop (exists)",
                                                  "skip sessionStart hook: cur-kit hook session-start (exists)"]
