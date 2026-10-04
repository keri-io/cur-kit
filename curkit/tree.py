"""What changed in the working tree, read from git: a fingerprint for reuse and a list of changed files."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

NO_COMMITS = b"(no commits)"
GIT_TIMEOUT = 60
DIFF = ("diff", "--binary", "--no-color", "--no-ext-diff", "--no-textconv", "--no-renames")
NAMES = ("diff", "--name-only", "-z", "--no-renames", "--relative")
# cur-kit rewrites its state folder after every run, so counting it would make every key new.
UNTRACKED = ("ls-files", "--others", "--exclude-standard", "-z", "--exclude=**/.cursor/cur-kit/state/")


def fingerprint(root: Path, salt: str) -> str | None:
    """sha256 of salt, HEAD, tracked changes, and untracked files of the whole repo. None outside a git work tree."""
    return _print(root, salt, True)


def tracked_print(root: Path, salt: str) -> str | None:
    """Like fingerprint, without untracked files, so artifacts a suite writes leave it unchanged."""
    return _print(root, salt, False)


def _print(root: Path, salt: str, untracked: bool) -> str | None:
    out = _git(root, "rev-parse", "--show-toplevel")
    parts = _tree_parts(Path(os.fsdecode(out.rstrip(b"\n"))), untracked) if out else None
    if parts is None:
        return None
    digest = hashlib.sha256()
    for part in (salt.encode(), *parts):
        digest.update(len(part).to_bytes(8, "big") + part)
    return digest.hexdigest()


def changed_files(root: Path) -> list[str]:
    """Tracked changes vs HEAD plus untracked, non-ignored files under root, relative to root."""
    outputs = [*_diffs(root, _head(root), NAMES), _git(root, *UNTRACKED)]
    return sorted({os.fsdecode(name) for out in outputs if out for name in out.split(b"\0") if name})


def _git(cwd: Path, *args: str) -> bytes | None:
    command = ["git", "--no-optional-locks", "-C", str(cwd), *args]
    try:
        done = subprocess.run(command, capture_output=True, timeout=GIT_TIMEOUT, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def _head(cwd: Path) -> bytes | None:
    return _git(cwd, "rev-parse", "--verify", "--quiet", "HEAD")


def _diffs(cwd: Path, head: bytes | None, diff: tuple[str, ...]) -> list[bytes | None]:
    if head:
        return [_git(cwd, *diff, "HEAD")]
    return [_git(cwd, *diff, "--cached"), _git(cwd, *diff)]


def _tree_parts(top: Path, untracked: bool) -> list[bytes] | None:
    head = _head(top)
    parts = [head or NO_COMMITS, *_diffs(top, head, DIFF), *([_untracked(top)] if untracked else [])]
    known = [part for part in parts if part is not None]
    return known if len(known) == len(parts) else None


def _untracked(top: Path) -> bytes | None:
    out = _git(top, *UNTRACKED)
    if out is None:
        return None
    names = [name for name in out.split(b"\0") if name]
    return b"".join(name + b"\0" + _file_hash(top / os.fsdecode(name)) for name in names)


def _file_hash(path: Path) -> bytes:
    try:
        with path.open("rb") as handle:
            return hashlib.file_digest(handle, "sha256").digest()
    except OSError:
        return bytes(32)
