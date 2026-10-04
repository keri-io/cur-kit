"""AC-09: State keeps last-run.json, latch.json, and runs.jsonl under .cursor/cur-kit/state/."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from curkit.state import STATE_DIR, State

DEFAULT_LATCH = {"failure": None, "count": 0}


def test_ac09_state_dir_is_under_cursor_cur_kit() -> None:
    assert STATE_DIR == ".cursor/cur-kit/state"


def test_ac09_state_creates_its_folder_on_first_write(tmp_path: Path) -> None:
    state = State(tmp_path)
    assert not (tmp_path / STATE_DIR).exists()
    state.save_last({"ok": True, "key": "abc"})
    assert json.loads((tmp_path / STATE_DIR / "last-run.json").read_text()) == {"ok": True, "key": "abc"}
    assert State(tmp_path).last() == {"ok": True, "key": "abc"}


def test_ac09_reads_and_clearing_never_create_the_folder(tmp_path: Path) -> None:
    state = State(tmp_path)
    assert state.last() is None
    assert state.latch() == DEFAULT_LATCH
    state.clear_latch()
    assert not (tmp_path / ".cursor").exists()


def test_ac09_latch_round_trips_and_clears(tmp_path: Path) -> None:
    state = State(tmp_path)
    state.save_latch({"failure": "abc", "count": 2})
    assert json.loads((tmp_path / STATE_DIR / "latch.json").read_text()) == {"failure": "abc", "count": 2}
    assert State(tmp_path).latch() == {"failure": "abc", "count": 2}
    state.clear_latch()
    assert state.latch() == DEFAULT_LATCH


def test_ac09_log_appends_one_json_line_per_run(tmp_path: Path) -> None:
    state = State(tmp_path)
    state.log({"ok": False, "seconds": 1.5})
    state.log({"ok": True, "seconds": 0.5})
    lines = (tmp_path / STATE_DIR / "runs.jsonl").read_text().splitlines()
    assert [json.loads(line) for line in lines] == [{"ok": False, "seconds": 1.5}, {"ok": True, "seconds": 0.5}]


@pytest.mark.parametrize("content", [b'{"ok": tru', b"[1, 2]", b"", b"\xff\xfe{}"])
def test_ac09_corrupt_files_read_as_missing(tmp_path: Path, content: bytes) -> None:
    folder = tmp_path / STATE_DIR
    folder.mkdir(parents=True)
    for name in ("last-run.json", "latch.json"):
        (folder / name).write_bytes(content)
    state = State(tmp_path)
    assert state.last() is None
    assert state.latch() == DEFAULT_LATCH


def test_ac09_latch_without_a_whole_number_count_reads_as_missing(tmp_path: Path) -> None:
    folder = tmp_path / STATE_DIR
    folder.mkdir(parents=True)
    (folder / "latch.json").write_text('{"failure": "abc", "count": "two"}')
    assert State(tmp_path).latch() == DEFAULT_LATCH
