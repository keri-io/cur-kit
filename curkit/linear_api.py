"""Stdlib GraphQL client for the Linear board."""

from __future__ import annotations

import json
import os
import urllib.request

API = "https://api.linear.app/graphql"
CONTEXT = """query Context($id: String!) {
  team(id: $id) { id states { nodes { id name type } } activeCycle { id } }
  organization { projectStatuses { id name type } }
}"""
FIND = """query Find($after: String) {
  projects(first: 50, after: $after) {
    nodes { id description }
    pageInfo { hasNextPage endCursor }
  }
}"""
CREATE = (
    "mutation ProjectCreate($input: ProjectCreateInput!) "
    "{ projectCreate(input: $input) { project { id } } }"
)
MILESTONES = (
    "query Milestones($id: String!) "
    "{ project(id: $id) { projectMilestones { nodes { id name } } } }"
)
MILESTONE = (
    "mutation MilestoneCreate($input: ProjectMilestoneCreateInput!) "
    "{ projectMilestoneCreate(input: $input) { projectMilestone { id } } }"
)
LABELS = (
    "query Labels($id: String!) { team(id: $id) { "
    "labels(first: 250) { nodes { id name } } } }"
)
LABEL = (
    "mutation LabelCreate($input: IssueLabelCreateInput!) "
    "{ issueLabelCreate(input: $input) { issueLabel { id } } }"
)
ISSUES = """query Issues($id: String!, $after: String) {
  project(id: $id) {
    issues(first: 50, after: $after) {
      nodes { id title createdAt }
      pageInfo { hasNextPage endCursor }
    }
  }
}"""
INSERT = (
    "mutation IssueCreate($input: IssueCreateInput!) "
    "{ issueCreate(input: $input) { issue { id } } }"
)
UPDATE = (
    "mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) "
    "{ issueUpdate(id: $id, input: $input) { success } }"
)
RELATE = (
    "mutation Duplicate($input: IssueRelationCreateInput!) "
    "{ issueRelationCreate(input: $input) { success } }"
)
DOCS = (
    "query Docs($id: String!) { project(id: $id) { "
    "documents(first: 250) { nodes { id title } } } }"
)
DOC_NEW = """mutation DocCreate($input: DocumentCreateInput!) {
  documentCreate(input: $input) { document { id url } }
}"""
DOC_SET = """mutation DocUpdate($id: String!, $input: DocumentUpdateInput!) {
  documentUpdate(id: $id, input: $input) { document { url } }
}"""
STATUS = (
    "mutation ProjectStatus($id: String!, $input: ProjectUpdateInput!) "
    "{ projectUpdate(id: $id, input: $input) { success } }"
)
HEALTH = (
    "mutation Health($input: ProjectUpdateCreateInput!) "
    "{ projectUpdateCreate(input: $input) { success } }"
)
STAGES = ("Specify", "Plan", "Tasks", "Implement", "Converge")


def graphql(query: str, variables: dict, transport=None) -> dict:
    """Run one Linear query. `transport` replaces HTTP in tests."""
    payload = transport(query, variables) if transport else _http(query, variables)
    errors = payload.get("errors") if isinstance(payload, dict) else None
    if errors:
        message = errors[0].get("message", "linear") if isinstance(errors[0], dict) else "linear"
        raise RuntimeError(str(message))
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise TypeError("linear")
    return data


def open_team(run, key: str) -> dict:
    data = run(CONTEXT, {"id": key})
    group = data.get("team") or {}
    if not group.get("id"):
        raise RuntimeError(f"no Linear team {key}")
    cycle = (group.get("activeCycle") or {}).get("id")
    states = (group.get("states") or {}).get("nodes") or []
    org = data.get("organization") or {}
    return {"id": group["id"], "states": states, "cycle": cycle, "statuses": org.get("projectStatuses") or []}


def project_id(run, spec: tuple) -> str:
    team, name, key = spec
    marker = f"cur-kit:{key}"
    found = _find(run, marker)
    if found:
        return found
    made = run(CREATE, {"input": {"name": name, "description": marker, "teamIds": [team]}})
    return made["projectCreate"]["project"]["id"]


def _find(run, marker: str) -> str:
    cursor, guard = None, 0
    while guard < 20:
        data = run(FIND, {"after": cursor})["projects"]
        nodes = data.get("nodes") or []
        hit = [node["id"] for node in nodes if node.get("description") == marker]
        info = data.get("pageInfo") or {}
        if hit or not info.get("hasNextPage"):
            return hit[0] if hit else ""
        cursor, guard = info.get("endCursor"), guard + 1
    return ""


def milestones(run, project: str) -> dict[str, str]:
    nodes = run(MILESTONES, {"id": project})["project"]["projectMilestones"]["nodes"]
    found = {node["name"]: node["id"] for node in nodes}
    for index, name in enumerate(STAGES):
        if name not in found:
            body = {"projectId": project, "name": name, "sortOrder": index}
            made = run(MILESTONE, {"input": body})
            found[name] = made["projectMilestoneCreate"]["projectMilestone"]["id"]
    return found


def label_ids(run, team: str, names: list[str]) -> dict[str, str]:
    nodes = run(LABELS, {"id": team})["team"]["labels"]["nodes"]
    found = {node["name"]: node["id"] for node in nodes}
    for name in dict.fromkeys(names):
        if name not in found:
            made = run(LABEL, {"input": {"teamId": team, "name": name}})
            found[name] = made["issueLabelCreate"]["issueLabel"]["id"]
    return found


def issue_nodes(run, project: str) -> list[dict]:
    found, cursor, guard = [], None, 0
    while guard < 20:
        page = run(ISSUES, {"id": project, "after": cursor})["project"]["issues"]
        found.extend(page.get("nodes") or [])
        info = page.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            return found
        cursor, guard = info.get("endCursor"), guard + 1
    return found


def write_issue(run, payload: dict) -> str:
    ident = payload.get("id")
    if ident:
        run(UPDATE, {"id": ident, "input": payload["input"]})
    else:
        made = run(INSERT, {"input": payload["input"]})
        ident = made["issueCreate"]["issue"]["id"]
    if payload.get("duplicate"):
        run(RELATE, {"input": {"type": "duplicate", "issueId": ident, "relatedIssueId": payload["duplicate"]}})
    return ident


def write_doc(run, spec: tuple) -> str:
    project, title, content = spec
    if not content:
        return ""
    nodes = run(DOCS, {"id": project})["project"]["documents"]["nodes"]
    found = {node["title"]: node["id"] for node in nodes}
    if title in found:
        data = run(DOC_SET, {"id": found[title], "input": {"content": content}})
        document = (data.get("documentUpdate") or {}).get("document") or {}
        return document.get("url") or ""
    data = run(DOC_NEW, {"input": {"title": title, "content": content, "projectId": project}})
    document = (data.get("documentCreate") or {}).get("document") or {}
    return document.get("url") or ""


def _http(query: str, variables: dict) -> dict:
    key = os.environ.get("LINEAR_API_KEY", "").strip()
    body = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(API, data=body, method="POST")
    request.add_header("Authorization", key)
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        loaded = json.loads(response.read().decode())
    return loaded if isinstance(loaded, dict) else {}
