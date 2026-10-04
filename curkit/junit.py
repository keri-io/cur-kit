"""JUnit XML reports as written by pytest, Jest, and Bun."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree


@dataclass(frozen=True)
class Case:
    name: str
    failed: bool
    skipped: bool = False


def _case(element: ElementTree.Element) -> Case:
    name, classname = element.get("name", ""), element.get("classname", "")
    failed = element.find("failure") is not None or element.find("error") is not None
    skipped = element.find("skipped") is not None
    return Case(name=f"{classname}::{name}" if classname else name, failed=failed, skipped=skipped)


def read_junit(path: Path) -> list[Case] | None:
    """Every <testcase> in the report, at any nesting depth. None when missing or unparseable."""
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError):
        return None
    return [_case(element) for element in root.iter("testcase")]
