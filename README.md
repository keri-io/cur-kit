# cur-kit

cur-kit is Always Run for [Spec Kit](https://github.com/github/spec-kit) on Cursor. When a project sets a test
command, cur-kit runs the suite after every completed agent turn. A red result comes back to the agent as its next
message.

Spec Kit stays an upgradable dependency. cur-kit never edits `.specify/` or `.cursor/skills/speckit-*`. After
`/speckit-implement`, the stop hook submits `/speckit-converge`. If that reply names `/speckit-implement` and does
not say the work is finished, the next stop submits implement. `specify workflow` still runs the same loop headless.
Subagents get their model from agent files in the project's `.cursor/agents/`.

## Requirements

- Python 3.11 or later as `python3` on PATH. cur-kit uses only the standard library.
- git. Result reuse and the unplanned-file list need a git work tree.
- specify-cli 1.0.13 or later: `uv tool install specify-cli`.
- cursor-agent, the Cursor CLI. The workflow steps run it.

## Install

```bash
bin/cur-kit install
```

This changes `~/.cursor/hooks.json`. It adds two user hooks and keeps every other entry:

- `stop` runs `<repo>/bin/cur-kit hook stop --user`, with `timeout` 900 and `loop_limit` 25.
- `sessionStart` runs `<repo>/bin/cur-kit hook session-start`, with `timeout` 10.

`--user` stays quiet when the project already has a cur-kit `stop` hook, so the suite runs once. Cloud agents never
load `~/.cursor/hooks.json`. They run the project file `.cursor/hooks.json`, which `cur-kit --here` writes.

An older cur-kit entry for the same event, for example from another checkout, is replaced rather than kept beside the
new one. It also links `~/.local/bin/cur-kit` to `bin/cur-kit`. Running it again changes nothing. `--home DIR`
installs under another home folder. If `hooks.json` cannot be merged, for example because it is not valid JSON, the
command exits 1 and leaves the file alone.

User hooks run in every project you open in Cursor. In a project without `.cursor/cur-kit.json`, they do nothing.

If you are switching from cursor-bootstrap, remove its `stop` entries, the `hooks/cursor-bootstrap/*_stop.py`
commands, from `~/.cursor/hooks.json` yourself. `bin/cur-kit install` leaves them in place. A project seeded with
`cur-kit --here` has `.specify/`, so the old `tdd_stop.py` stays quiet there. In a project with a hand-written
`.cursor/cur-kit.json` and no `.specify/`, it can still run its own `pytest -q` or `bun test`. The old
`codex_stop.py` can send its own follow-up in either case.

## Start a project

```bash
cd my-app
cur-kit --here
```

`cur-kit --here` sets up Spec Kit first:

- `.specify/` is present: no `specify init`.
- The folder is empty: `specify init --here --integration cursor-agent --non-interactive`.
- The folder has files but no `.specify/`: the same command with `--force`.
- `specify` is not on PATH: it exits 1 and prints the install command.

Then it writes these files. It writes a file only when it is missing and never overwrites one.
`.cursor/hooks.json` is the exception: cur-kit merges its entries and keeps every other hook.

- `.cursor/cur-kit.json`, the config. `test` is `python3 -m pytest -q || test $? -eq 5` when there is a `pyproject.toml`,
  `pytest.ini`, or `setup.py`, and `bun test` when `package.json` has a `test` script. Otherwise it is empty. pytest
  exits 5 when a project has no tests yet, and that command treats 5 as green.
- `.cursor/agents/cur-kit-scout.md`, `cur-kit-writer.md`, `cur-kit-witness.md`, `cur-kit-reviewer.md`, and
  `cur-kit-diagnose.md`.
- `.cursor/rules/cur-kit.mdc`, the always-on rule.
- `.cursor/cur-kit/workflow.yml`, the converge loop.
- `.cursor/hooks/cur-kit`, the project hook command, and entries in `.cursor/hooks.json` for `stop`,
  `sessionStart`, `beforeSubmitPrompt`, and `afterAgentResponse`. `stop` runs `bash .cursor/hooks/cur-kit stop`
  with `timeout` 900 and `loop_limit` 25. Cloud agents load this file. `sessionStart` is for the desktop app and
  for self-hosted workers. Managed cloud agents do not send that step.

It also adds `.cursor/cur-kit/state/` to `.gitignore`, once. If `.cursor/hooks.json` is not valid JSON, `--here` exits 1
and leaves that file alone.

Set `test` to the real suite. Spec Kit has no test command. While `test` is empty, nothing runs.

## Config

`.cursor/cur-kit.json`:

```json
{
  "test": "bun test --pass-with-no-tests --reporter=junit --reporter-outfile=report.xml",
  "lint": "bunx oxlint src spacetimedb/src --ignore-pattern src/module_bindings",
  "typecheck": "bunx tsc --noEmit -p tsconfig.json && bunx tsc --noEmit -p spacetimedb/tsconfig.json",
  "junit": "report.xml",
  "timeout": 300,
  "cache": true
}
```

| Key | Default | Meaning |
| --- | --- | --- |
| `test` | `""` | The suite. Empty means nothing runs. |
| `lint` | `""` | Runs at the same time as `test`. Optional. |
| `typecheck` | `""` | Runs at the same time as `test`. Optional. |
| `junit` | `""` | The JUnit XML report the test command writes, as a path inside the project. |
| `timeout` | `300` | Seconds before a command is killed, with its whole process group. At most 850. |
| `cache` | `true` | Reuse the last result when nothing changed. |
| `linear.team` | unset | Linear team key, such as `ENG`. The mirror queues a board for the Linear MCP. `LINEAR_API_KEY` is optional and used only when the MCP is not how you connect. |

Commands run through the shell in the project root. They are the project's own commands, and they get your
environment unchanged. Put a coverage floor in the test command, like `--cov-fail-under=80`.

With `junit` set, cur-kit deletes the report before each run and reads the failing test names from it. Keep the
report gitignored. Most reports record test times, so a tracked report changes on every run and nothing is ever
reused. A `junit` path that is absolute or leads outside the project is ignored, as if it were empty. Without a report, scenario ids
come from the lines of the failing commands' output that mention "fail" or "error", and the check-off guard is
skipped.

A `timeout` above 850 is lowered to 850, so a run ends before the stop hook's own 900-second limit. Unknown keys are
ignored by the check. `linear.team` is read only by the Linear mirror.

If you write `.cursor/cur-kit.json` by hand instead of with `cur-kit --here`, add `.cursor/cur-kit/state/` to
`.gitignore` yourself. cur-kit rewrites the files in that folder on every run.

## Check

```bash
cur-kit check --json
```

This runs the same check as the stop hook and prints the result as JSON on one line. It exits 0 even when red, so a
workflow shell step does not fail. If cur-kit itself fails, it still prints JSON, with `red` true and an `error`
field, and exits 0. `cur-kit check` prints the same JSON, indented.

For a project whose suite fails `test_US1_AC2_redirects`, with tasks T014 `[US1]` and T015 `[US2]` open:

```json
{
  "configured": true, "ok": false, "red": true, "reused": false, "key": "<sha256>",
  "outcomes": [{"name": "test", "command": "python3 suite.py", "code": 1,
                "output": "FAILED tests/test_auth.py::test_US1_AC2_redirects - AssertionError: 200 != 302",
                "timed_out": false, "seconds": 0.032}],
  "failing": ["tests.test_auth::test_US1_AC2_redirects"],
  "ids": ["US1/AC2"],
  "tasks_for_ids": [{"id": "T014", "text": "T014 [US1] Implement login redirect in src/auth.py"}],
  "open": 2, "open_tasks": ["T014", "T015"],
  "guard": [],
  "unplanned": [],
  "feature_dir": "specs/001-login"
}
```

- `red` is true when a command failed or timed out, when the JUnit report has a failing test, or when `guard` has
  entries. A command that exits 0 with failures in its report is still red.
- `outcomes` keep the end of each command's output, at most 30 lines and 4000 characters. `failing` keeps at most
  50 names.
- `reused` is true when the result came from the last run, because nothing changed.
- `ids` are the scenario keys that the failing tests cite. `tasks_for_ids` are the tasks that cite them.
- `open` and `open_tasks` count the tasks in the feature's `tasks.md` that are not marked `[x]`. A mark like `[-]` or
  `[~]` counts as open.
- `guard` lists checked tasks that no passing test covers. It is `null` when there is no JUnit report.
- `unplanned` lists changed files that no task names, outside `.cursor/`, `.specify/`, and `specs/`. The JUnit report
  is left out.

## The converge loop

```bash
specify workflow run .cursor/cur-kit/workflow.yml
```

Run it from the project root. Each pass runs `speckit.implement`, then `speckit.converge`, then
`cur-kit check --json`. From the second pass on, implement gets the last check's JSON as its arguments. The loop
repeats while a task is open or the check is red, at most 3 times. Then a gate asks you to pick the next skill:
done, implement, clarify, or plan.

In a chat, the stop hook does the same handoff. A green `/speckit-implement` turn submits `/speckit-converge`.
A red suite still comes back first, and converge waits until a later stop is green. A converge reply submits
`/speckit-implement` only when it names that command and does not say the work is finished (`converged`,
`no further implement`, or `implementation is complete`). A reply that never names the command ends the loop. The stock Spec Kit skills are not edited. A converge
prompt that also mentions implement in a sentence stays a converge turn. Cloud often sends the chat id only on
stop, and it may skip the prompt hook for a follow-up. cur-kit keeps that turn and remembers the command it just
submitted.

Each step is a headless `cursor-agent` run, so run the loop on a branch or in a worktree. The check step calls
`cur-kit` from PATH, so `~/.local/bin` must be on PATH. To see the steps without running them:

```bash
specify workflow info .cursor/cur-kit/workflow.yml
```

## What happens on each stop

Cursor runs `cur-kit hook stop` when an agent turn ends.

1. Skip. The hook returns `{}` and runs nothing when the turn did not complete, when `loop_count` is 25 or more, or
   when the project has no `.cursor/cur-kit.json`. The project is `CURSOR_PROJECT_DIR`, else the first workspace
   root, else the current folder.
2. Reuse. If nothing changed since the last run, cur-kit reuses that result. The key covers the commands, the `junit`
   path, `HEAD`, the working-tree diff, and the contents of untracked files. Gitignored files and cur-kit's state
   folder do not count. If a tracked file changes while the suite runs, the next stop runs the suite again. An
   untracked file edited while the suite runs is not caught that way, because the suite's own artifacts are untracked
   too. That edit is still in the tree, so the stop after the next change runs the suite.
3. Suite. Otherwise cur-kit runs `test`, `lint`, and `typecheck` at the same time, each under `timeout`.
4. Guard. On every stop, cur-kit reads `tasks.md` again. A checked task with a story label, like `[US1]`, needs a
   passing test that cites `US1` or one of its scenarios, like `test_US1_AC2_redirects`. No citing test may fail.
   Story keys are not scoped to a feature, so a passing `US1` test from another feature also counts for this
   feature's `[US1]` tasks.
5. Green. The hook clears the latch. It then submits `/speckit-converge` or `/speckit-implement` when the skill
   loop above still has a next step, and otherwise returns `{}`.
6. Latch. Each distinct failure is reported at most twice. A failure is the set of failing test names, or the end
   of the output when there are no names. The second report says the same failure came back after a change, or
   that it is still there and nothing changed. Either way it tells the agent to stop and tell you if it can't fix
   it. After that the hook returns `{}` until the failure changes, a run is green, or a new chat starts.
   `sessionStart` clears the latch. A stop whose `conversation_id` is a new non-empty string does too, which is how a
   new cloud chat is heard: managed cloud agents do not run `sessionStart`. An empty `conversation_id` changes nothing.
   The latch only compares a failure with the one before it, so a suite that
   alternates between two failures is reported every time, until `loop_count` reaches 25.
7. Follow-up. A reported failure returns `{"followup_message": "..."}`. It names the failing tests, the scenario ids
   with the tasks that cite them, each failing command with up to the last 30 lines of its output, and the guard
   messages. It ends with: "If you're implementing a task, fix this before marking it done. If this was a spec
   skill, note it under the task and leave the code alone. Mark nothing [x] while the suite is red." When the only
   problem is a timeout, it says so, points to `timeout`, and does not tell the agent to fix the code. The message
   goes to the model and into the chat transcript, test output included, so keep secrets out of test output.

The follow-up for the example above:

```text
cur-kit: the suite is red (1/25).

Failing tests:
- tests.test_auth::test_US1_AC2_redirects

Scenario ids: US1/AC2
Tasks that cite them:
- T014 [US1] Implement login redirect in src/auth.py

$ python3 suite.py
FAILED tests/test_auth.py::test_US1_AC2_redirects - AssertionError: 200 != 302

If you're implementing a task, fix this before marking it done. If this was a spec skill, note it under the task and leave the code alone. Mark nothing [x] while the suite is red.
```

Each check is appended to `.cursor/cur-kit/state/runs.jsonl`. Both hooks always exit 0 and print JSON. An internal
error returns `{}`.

## Linear

Set `linear.team` in `.cursor/cur-kit.json` to the team key, such as `ENG`. Every completed stop writes
`.cursor/cur-kit/state/linear-board.json`. On the next turn, if the Linear MCP is connected, the agent applies that
board before other work. Cursor Cloud with the Linear plugin connected is enough. No API key is required for that
path. If `LINEAR_API_KEY` is set as well, the stop hook publishes directly and does not leave the file pending.
A missing team does nothing, and the stop hook still returns its follow-up. Spec Kit skills and `.specify/` are not edited.

One git repository is one project. cur-kit finds it by the description `cur-kit:` plus the `origin` URL, or plus the
folder name when there is no remote. Leave that description in place. The project name is the repository name.

`tasks.md` and the feature markdown stay the files the stop hook reads. Linear is the board.

| On the board | Status |
| --- | --- |
| A spec, plan, research note, constitution, checklist, or task with no file or task line yet | Backlog |
| An unchecked task in the active `tasks.md` | Todo |
| The skill that is running, the next skill this stop will submit, and open tasks during `/speckit-implement` | In Progress |
| A checked task, or a written spec, plan, or checklist | In Review |
| Those In Review items after `/speckit-converge` says the work is finished and the suite is not red | Done |
| A task id gone from `tasks.md`, or a box that is neither empty nor `x` | Canceled |
| A second issue with the same key (`T014`, or `Specification` for the spec) | Duplicate of the older issue |

Finished means the converge reply contains `converged`, `no further implement`, or `implementation is complete`. That
pass also sets the Linear project to Completed.

Priority is Urgent for a constitution breach or a CRITICAL finding, High for the first user story or a HIGH finding,
Medium for the spec, the plan, the constitution, and later stories, and Low for research, checklists, and LOW findings.

In Progress and In Review issues join the team's current cycle when it has one. Backlog and Todo stay out of the cycle.
cur-kit does not create a cycle. Issues sit on the Specify, Plan, Tasks, Implement, or Converge milestone. The full
markdown of the spec, plan, research, constitution, each checklist, and the latest convergence findings is a project
document; the issue keeps the first line and links to it. Story ids and `convergence` are labels. Each sync posts a
project update: on track when the suite is green or not configured, at risk when it is red.

A Linear error is appended to `runs.jsonl`. It does not change the hook's answer.

## Agent files

`cur-kit --here` writes these into the project's `.cursor/agents/`. Each file sets its own model. The parent picks
the agent type and never passes a model.

| Agent | Model | Job |
| --- | --- | --- |
| `cur-kit-scout` | `grok-4.7-high` | Research for the plan. Read-only. |
| `cur-kit-writer` | `grok-4.7-high` | One task in its own files, red test first. |
| `cur-kit-witness` | `grok-4.7-high` | Walks a user flow in the running app. Read-only. |
| `cur-kit-reviewer` | `grok-4.7-xhigh, 500k` | Checks that a test proves its scenario. Read-only. |
| `cur-kit-diagnose` | `grok-4.7-high` | Finds the cause of one cluster of failing tests. Read-only. |

The rule `.cursor/rules/cur-kit.mdc` applies to every chat. The parent plans. Writers run up to twelve at once, on
separate files, and a large job may run more. Scouts do the same. Test names cite `FR-###`, `SC-###`, `USn`, or
`USn/ACn`. Nothing is marked `[x]` while the suite
is red, or before the reviewer has matched the scenario to the test. Commits and pushes are the parent's.

## Differences from the plan

cur-kit started as a plan page for Always Run. v0.1.0 differs from it on purpose:

- The config is `.cursor/cur-kit.json`, not `.cursor/bootstrap.json`. State, including `runs.jsonl` and the child
  record `slots.jsonl`, is in `.cursor/cur-kit/state/`, not `.cursor/bootstrap/`. The old `tdd_stop.py` reads the old
  config and stays quiet where `.specify/` exists. The old `codex_stop.py` does not check either file and can still
  send follow-ups, so remove the old pack's stop hooks when you switch (see Install).
- The workflow file is `.cursor/cur-kit/workflow.yml`. It adds an `integration` input, default `auto`, to both command
  steps, and `on_reject: skip` to the gate. Without them, Spec Kit's validator rejects the gate and the command steps
  cannot start the agent. The check step gets 900 seconds instead of the engine's default 300.
- Project hooks live in `.cursor/hooks.json`. Cursor Cloud loads that file and runs `stop`. It does not load
  `~/.cursor/hooks.json`, and it does not run `sessionStart`. The red latch therefore resets when `conversation_id`
  changes. Deferred to a later version: the `subagentStart` cap on writers, because its payload is unverified, and the
  compaction checkpoint, which cursor-bootstrap still provides. Until then, cur-kit lists unplanned files instead of
  blocking a writer.

## Development

```bash
scripts/check.sh
```

This runs the tests under coverage (at least 80%), `ruff`, and the size gates in `scripts/gates.py`. It needs `uvx`.

The end-to-end tests drive `bin/cur-kit` in temp projects with a temp HOME:

```bash
python3 -m pytest -q tests/e2e
```

The `cur-kit --here` tests are skipped when `specify` is not on PATH.
