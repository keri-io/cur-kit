from __future__ import annotations

import re
from pathlib import Path

import pytest

import curkit

TEMPLATES = Path(curkit.__file__).parent / "templates"
MODELS = {
    "cur-kit-scout": "grok-4.7-high",
    "cur-kit-writer": "grok-4.7-high",
    "cur-kit-witness": "grok-4.7-high",
    "cur-kit-reviewer": "grok-4.7[effort=xhigh,context=500k]",
    "cur-kit-diagnose": "grok-4.7-high",
}
FILES = [f"agents/{name}.md" for name in MODELS] + ["rules/cur-kit.mdc", "workflow.yml"]
EMPHASIS = re.compile(r"\b(MUST|NEVER|ALWAYS|CRITICAL|IMPORTANT|ONLY|NOT|DO|NO|STOP|REQUIRED|WARNING)\b")
WRITER = ["one task", "its own files", "test first", "named after the scenario key", "minimum code",
          "never run the full suite", "files you touched", "red and green output", "open questions",
          "does not write application code or tests itself"]
REVIEWER = ["read-only", "scenario text", "the spec and the test", "not the writer's transcript",
            "do not run speckit-analyze"]
RULE = ["always run", "cur-kit-writer", "up to twelve", "more when the job is large", "separate files",
        "fr-###", "sc-###", "usn", "usn/acn",
        "nothing is marked [x] while the suite is red", "cur-kit-reviewer", "matched the scenario to the test",
        "the stop hook may submit /speckit-converge after /speckit-implement",
        "specify workflow run .cursor/cur-kit/workflow.yml", "spec.md", "plan.md",
        "research.md", "tasks.md", "checklists", "changelog.md", ".cursor/cur-kit.json",
        "secrets never go in messages", "one json line", ".cursor/cur-kit/state/slots.jsonl",
        "does not write application code or tests", "gives every implementation task to cur-kit-writer"]
R14 = {
    "agents/cur-kit-writer.md": [
        ("never run the full suite. the full suite runs after the turn, through the stop hook or cur-kit check in a "
         "workflow step."),
        "commits and pushes are the parent's.",
    ],
    "rules/cur-kit.mdc": ["commits and pushes are the parent's."],
}
WORKFLOW = [
    'schema_version: "1.0"', 'id: "cur-kit-converge"', "speckit_version:", "type: do-while", "max_iterations: 3",
    'condition: "{{ steps.remaining.output.data.open > 0 or steps.remaining.output.data.red }}"',
    "command: speckit.implement", "args: \"{{ steps.remaining.output.stdout | default('') }}\"",
    "command: speckit.converge", "type: shell", 'run: "cur-kit check --json"', "output_format: json",
    "type: gate", "options: [done, implement, clarify, plan]",
]


def split(name: str) -> tuple[dict[str, str], str]:
    _, head, body = (TEMPLATES / name).read_text(encoding="utf-8").split("---\n", 2)
    fields = dict(line.split(": ", 1) for line in head.splitlines() if ": " in line)
    return fields, " ".join(body.replace("`", "").split()).lower()


@pytest.mark.parametrize("name, model", MODELS.items())
def test_ac14_agent_files_have_name_description_and_model(name, model):
    fields, body = split(f"agents/{name}.md")
    assert set(fields) == {"name", "description", "model"}
    assert (fields["name"], fields["model"]) == (name, model)
    assert len(fields["description"]) > 40 and body
    assert ": " not in fields["description"] and " #" not in fields["description"]


@pytest.mark.parametrize("name", MODELS)
def test_ac14_scout_witness_reviewer_and_diagnose_say_they_are_read_only(name):
    fields, body = split(f"agents/{name}.md")
    said = "read-only" in body and "read-only" in fields["description"].lower()
    assert said is (name != "cur-kit-writer")


@pytest.mark.parametrize("name, phrases", [("cur-kit-writer", WRITER), ("cur-kit-reviewer", REVIEWER)])
def test_ac14_writer_and_reviewer_state_their_rules(name, phrases):
    _, body = split(f"agents/{name}.md")
    assert [phrase for phrase in phrases if phrase not in body] == []


@pytest.mark.parametrize("name", FILES)
def test_ac14_templates_avoid_all_caps_emphasis(name):
    assert EMPHASIS.findall((TEMPLATES / name).read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("name, phrases", R14.items())
def test_r14_writer_and_rule_leave_the_suite_to_the_hooks_and_commits_to_the_parent(name, phrases):
    _, body = split(name)
    assert [phrase for phrase in phrases if phrase not in body] == []


def test_ac13_rule_always_applies_and_states_the_contract():
    fields, body = split("rules/cur-kit.mdc")
    assert fields["alwaysApply"] == "true"
    assert [phrase for phrase in RULE if phrase not in body] == []


def test_ac15_workflow_has_the_required_pieces():
    text = (TEMPLATES / "workflow.yml").read_text(encoding="utf-8")
    assert [piece for piece in WORKFLOW if piece not in text] == []


def test_ac15_workflow_nests_implement_converge_and_check_in_the_loop_before_the_gate():
    lines = (TEMPLATES / "workflow.yml").read_text(encoding="utf-8").splitlines()
    steps = [line.rstrip() for line in lines if line.strip().startswith("- id: ")]
    assert steps == ["  - id: build", "      - id: implement", "      - id: converge", "      - id: remaining",
                     "  - id: review"]
