"""GraphQL client paths the stop-hook fake does not reach."""

from __future__ import annotations

from functools import partial
from unittest import mock

import pytest

from curkit.__main__ import main
from curkit.linear_api import graphql, milestones, project_id, write_doc
from tests.test_check import make_project


def test_project_is_created_when_the_repo_is_new():
    seen = []

    def transport(query, variables):
        seen.append(variables)
        if query.startswith("query Find") and not variables.get("after"):
            node = {"id": "other", "description": "nope"}
            page = {"nodes": [node], "pageInfo": {"hasNextPage": True, "endCursor": "c"}}
            return {"data": {"projects": page}}
        if query.startswith("query Find"):
            return {"data": {"projects": {"nodes": [], "pageInfo": {"hasNextPage": False}}}}
        return {"data": {"projectCreate": {"project": {"id": "new"}}}}

    run = partial(graphql, transport=transport)
    assert project_id(run, ("team", "Corund", "https://github.com/keri-io/Corund.git")) == "new"
    made = seen[-1]["input"]
    assert made["name"] == "Corund" and made["teamIds"] == ["team"]
    assert made["description"] == "cur-kit:https://github.com/keri-io/Corund.git"


def test_missing_milestones_are_created():
    made = []

    def transport(query, variables):
        if query.startswith("query Milestones"):
            nodes = [{"id": "S", "name": "Specify"}]
            return {"data": {"project": {"projectMilestones": {"nodes": nodes}}}}
        made.append(variables["input"])
        name = variables["input"]["name"]
        return {"data": {"projectMilestoneCreate": {"projectMilestone": {"id": name[:1]}}}}

    found = milestones(partial(graphql, transport=transport), "project")
    assert [item["name"] for item in made] == ["Plan", "Tasks", "Implement", "Converge"]
    assert found["Specify"] == "S" and made[0]["sortOrder"] == 1


def test_graphql_errors_raise():
    broken = lambda *_args: {"errors": [{"message": "nope"}]}
    with pytest.raises(RuntimeError, match="nope"):
        graphql("query {}", {}, broken)
    with pytest.raises(TypeError):
        graphql("query {}", {}, lambda *_args: {"data": []})


def test_an_existing_document_is_updated():
    seen = []

    def transport(query, variables):
        seen.append(query)
        if query.startswith("query Docs"):
            nodes = [{"id": "doc", "title": "Specification"}]
            return {"data": {"project": {"documents": {"nodes": nodes}}}}
        return {"data": {"documentUpdate": {"document": {"url": "https://linear.app/doc"}}}}

    run = partial(graphql, transport=transport)
    assert write_doc(run, ("project", "Specification", "")) == ""
    url = write_doc(run, ("project", "Specification", "# Spec"))
    assert url == "https://linear.app/doc" and seen[-1].startswith("mutation DocUpdate")


def test_http_posts_the_api_key(monkeypatch):
    box = {}

    def opener(req, timeout):
        box["auth"] = req.get_header("Authorization")
        box["url"] = req.full_url
        box["body"] = req.data
        body = mock.MagicMock()
        body.read.return_value = b'{"data": {"ok": true}}'
        body.__enter__.return_value = body
        return body

    monkeypatch.setenv("LINEAR_API_KEY", "lin_test")
    monkeypatch.setattr("curkit.linear_api.urllib.request.urlopen", opener)
    assert graphql("query Q", {"id": "1"}) == {"ok": True}
    assert box["auth"] == "lin_test" and box["url"].endswith("/graphql")
    assert b"query Q" in box["body"]


def test_linear_sync_command_exits_0_without_a_key(tmp_path, monkeypatch):
    monkeypatch.chdir(make_project(tmp_path))
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    assert main(["linear"]) == 2
    assert main(["linear", "sync"]) == 0
