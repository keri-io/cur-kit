"""The `cur-kit` command line."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from curkit import __version__, check, here, hooks, install

BIN = Path(__file__).resolve().parent.parent / "bin" / "cur-kit"


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(prog="cur-kit", description="Always Run TDD harness for Spec Kit on Cursor.")
    top.add_argument("--version", action="version", version=f"cur-kit {__version__}")
    top.add_argument("--here", action="store_true", help="seed the current directory with Spec Kit and cur-kit")
    commands = top.add_subparsers(dest="command")
    run = commands.add_parser("check", help="run the check and print the result as JSON (exits 0 even when red)")
    run.add_argument("--json", action="store_true", help="print the result on one line")
    setup = commands.add_parser("install", help="install the Cursor hooks and ~/.local/bin/cur-kit")
    setup.add_argument("--home", type=Path, help="home folder to install into (default: your home)")
    commands.add_parser("hook", help="answer a Cursor hook: stop or session-start, JSON on stdin")
    return top


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args[:1] == ["hook"]:
        return hook(args[1:])
    top = parser()
    opts = top.parse_args(args)
    if opts.here:
        return report(lambda: here.seed(Path.cwd()))
    if opts.command == "check":
        print(json.dumps(checked(Path.cwd()), indent=None if opts.json else 2))
        return 0
    if opts.command == "install":
        home = opts.home or Path.home()
        return report(lambda: [*install.install_hooks(home, str(BIN)), install.link_bin(home, BIN)])
    top.print_help()
    return 2


def hook(args: list[str]) -> int:
    """Print one JSON object for the hook named in args and exit 0, whatever stdin holds."""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        body = payload if isinstance(payload, dict) else {}
        text = json.dumps(_dispatch(args, body))
    except Exception:  # noqa: BLE001 - a hook must always answer with JSON
        text = "{}"
    print(text)
    return 0


def _dispatch(args: list[str], payload: dict) -> dict:
    name = args[0] if args else ""
    if name == "stop":
        return hooks.on_stop(payload, user="--user" in args[1:])
    if name == "session-start":
        return hooks.on_session_start(payload)
    return {}


def checked(root: Path) -> dict:
    """The check result, or a red one naming the error, so the workflow step always gets JSON."""
    try:
        return check.run_check(root)
    except Exception as exc:  # noqa: BLE001 - `cur-kit check` must always answer with JSON
        return {"configured": True, "ok": False, "red": True, "error": f"{type(exc).__name__}: {exc}"}


def report(action: Callable[[], list[str]]) -> int:
    try:
        lines = action()
    except (here.SeedError, install.InstallError) as exc:
        print(exc, file=sys.stderr)
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
