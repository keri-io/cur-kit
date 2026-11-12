"""Latch updates for one stop, including a new cloud conversation."""

from __future__ import annotations

from curkit.state import State, should_report


def judge(state: State, payload: dict, failure: str) -> tuple[bool, dict]:
    """Report this failure. A new non-empty conversation_id starts the count over."""
    latch = _for_chat(state.latch(), _chat(payload))
    report, saved = should_report(latch, failure)
    return report, _stamp(saved, latch.get("conversation"))


def _chat(payload: dict) -> str | None:
    value = payload.get("conversation_id")
    return value if isinstance(value, str) and value else None


def _for_chat(latch: dict, chat: str | None) -> dict:
    if chat and latch.get("conversation") != chat:
        return {"failure": None, "count": 0, "conversation": chat}
    return latch


def _stamp(saved: dict, chat: object) -> dict:
    if isinstance(chat, str):
        return {**saved, "conversation": chat}
    return saved
