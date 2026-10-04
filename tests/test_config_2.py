from __future__ import annotations

import json

import pytest

from curkit.config import CONFIG_PATH, load

INSIDE = ["report.xml", ".cursor/report.xml", "reports/../report.xml", " out/junit.xml "]
OUTSIDE = ["{root}/report.xml", "/tmp/report.xml", "../report.xml", "reports/../../report.xml", ".", "a/..",
           "bad\u0000name.xml"]


def load_with(root, **values):
    path = root / CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"test": "pytest -q", **values}), encoding="utf-8")
    return load(root)


@pytest.mark.parametrize("given, expected", [
    (1200, 850), (850, 850), (849.5, 849.5), (90, 90), (1e308, 850), (float("inf"), 850), (float("nan"), 300),
    pytest.param(10**400, 850, id="401-digit-int"),
])
def test_r4_load_clamps_timeout_to_at_most_850_seconds(tmp_path, given, expected):
    assert load_with(tmp_path, timeout=given).timeout == expected


@pytest.mark.parametrize("junit", INSIDE)
def test_r7_load_keeps_a_junit_path_inside_the_root(tmp_path, junit):
    assert load_with(tmp_path, junit=junit).junit == junit.strip()


@pytest.mark.parametrize("junit", OUTSIDE, ids=lambda junit: junit.replace("\0", "NUL"))
def test_r7_load_drops_a_junit_path_that_is_absolute_or_outside_the_root(tmp_path, junit):
    root = tmp_path / "project"
    root.mkdir()
    assert load_with(root, junit=junit.format(root=root)).junit == ""


def test_r7_load_drops_a_junit_path_that_leaves_the_root_through_a_symlink(tmp_path):
    root, outside = tmp_path / "project", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "reports").symlink_to(outside)
    (root / "report.xml").symlink_to(outside / "report.xml")
    assert load_with(root, junit="reports/junit.xml").junit == ""
    assert load_with(root, junit="report.xml").junit == ""


def test_r7_load_keeps_a_junit_path_when_the_root_is_reached_through_a_symlink(tmp_path):
    (tmp_path / "real").mkdir()
    (tmp_path / "alias").symlink_to(tmp_path / "real")
    assert load_with(tmp_path / "alias", junit="reports/junit.xml").junit == "reports/junit.xml"
