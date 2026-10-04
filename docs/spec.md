# cur-kit v0.1.0 build spec

Source plan: `file:///tmp/sdd-tdd-harness.html` (read it once for intent). This file is the contract.

cur-kit wraps GitHub Spec Kit on Cursor. If `"test"` is set, the suite runs after every completed turn
(Always Run). Spec Kit stays an upgradable dependency. The converge loop runs through `specify workflow`.
Children get their model from project agent files.

## Locks

- Stdlib Python 3.11+ only. No third-party imports in `curkit/`.
- Never edit or generate anything under `.cursor/skills/speckit-*` or `.specify/` in a target project.
- Hooks never start a Spec Kit skill. No daemon, no chatroom, no secrets in agent messages.
- Every hook command exits 0 and prints JSON, even on internal errors (emit `{}`).
- Commands from the project config run with `shell=True` in the project root. They are the project's own commands.

## Deviations from the page (deliberate)

- Config is `.cursor/cur-kit.json`, not `.cursor/bootstrap.json`. State is `.cursor/cur-kit/state/`, not `.cursor/bootstrap/`.
  The old cursor-bootstrap hooks read those paths. Separate names mean the two packs never double-run a suite.
- The converge loop workflow file lives at `.cursor/cur-kit/workflow.yml`.
- Deferred to a later version: the `subagentStart` writer cap (its payload is unverified), project-level hooks for cloud,
  and the compaction checkpoint (the existing pack still provides it). v0 reports unplanned files instead of blocking.

## Layout and ownership

Only edit the files you own. Report anything else you need. The parent owns `pyproject.toml`, `CHANGELOG.md`,
`docs/spec.md`, `scripts/`, and `tests/test_gates.py`.

| Owner | Files |
| --- | --- |
| Fable A (wave 1) | `curkit/ids.py`, `curkit/tasks.py`, `curkit/junit.py`, `curkit/guard.py`, `curkit/followup.py`, their tests |
| Opus A (wave 1) | `curkit/tree.py`, `curkit/runner.py`, `curkit/state.py`, their tests |
| Opus B (wave 1) | `curkit/config.py`, `curkit/speckit.py`, `curkit/here.py`, `curkit/install.py`, `curkit/templates/**`, their tests |
| Opus C (wave 2) | `curkit/check.py`, `curkit/hooks.py`, `curkit/__main__.py`, `bin/cur-kit`, their unit tests |
| Opus D (wave 2) | `tests/e2e/**`, `README.md` |
| Fable B (wave 3) | Review only. No edits. |

Tests live in `tests/test_<module>.py` (split into `_2.py` files to stay under the gates). Name each test after the
acceptance criterion it proves, for example `test_ac01_keys_in_reads_underscore_forms`.

## Interfaces

```python
# curkit/ids.py
def keys_in(text: str) -> list[str]: ...          # canonical keys, unique, first-seen order
def story_of(key: str) -> str | None: ...         # "US1/AC2" -> "US1", "US3" -> "US3", "FR-003" -> None

# curkit/tasks.py
@dataclass(frozen=True)
class Task:
    id: str                    # "T014"
    done: bool                 # [x] or [X]
    story: str | None          # from a "[US1]" label
    keys: tuple[str, ...]      # keys_in(line), includes the story label and converge refs like "per US1/AC2"
    paths: tuple[str, ...]     # file paths named in the line, e.g. "src/models/user.py"
    text: str                  # the line without the checkbox
def parse_tasks(text: str) -> list[Task]: ...
def open_tasks(tasks: list[Task]) -> list[Task]: ...
def tasks_citing(tasks: list[Task], keys: list[str]) -> list[Task]: ...   # exact key match first, else same story

# curkit/junit.py
@dataclass(frozen=True)
class Case:
    name: str                  # "classname::name" when classname is present, else name
    failed: bool               # has <failure> or <error>
    skipped: bool = False      # has <skipped>; a skipped case is neither failed nor passing
def read_junit(path: Path) -> list[Case] | None: ...   # None when missing or unparseable

# curkit/guard.py
def violations(tasks: list[Task], cases: list[Case] | None) -> list[str] | None: ...   # None = skipped, no JUnit

# curkit/followup.py
TAIL: str
def compose(result: dict, loops: int, repeat: bool) -> str: ...

# curkit/tree.py
def fingerprint(root: Path, salt: str) -> str | None: ...   # None outside a git work tree
def changed_files(root: Path) -> list[str]: ...             # tracked changes vs HEAD plus untracked, not ignored

# curkit/runner.py
@dataclass(frozen=True)
class Outcome:
    name: str; command: str; code: int | None; output: str; timed_out: bool; seconds: float
def run_all(commands: dict[str, str], cwd: Path, timeout: float) -> list[Outcome]: ...

# curkit/state.py
STATE_DIR = ".cursor/cur-kit/state"
class State:                                  # State(root)
    def last(self) -> dict | None: ...        # last-run.json
    def save_last(self, record: dict) -> None: ...
    def latch(self) -> dict: ...              # latch.json, default {"failure": None, "count": 0}
    def save_latch(self, latch: dict) -> None: ...
    def clear_latch(self) -> None: ...
    def log(self, entry: dict) -> None: ...   # appends one line to runs.jsonl
def should_report(latch: dict, failure: str) -> tuple[bool, dict]: ...
def failure_print(names: list[str], output: str) -> str: ...

# curkit/config.py
CONFIG_PATH = ".cursor/cur-kit.json"
@dataclass(frozen=True)
class Config:
    test: str; lint: str; typecheck: str; junit: str; timeout: float; cache: bool
def load(root: Path) -> Config | None: ...       # None when the file is missing or not a JSON object
def commands(cfg: Config) -> dict[str, str]: ... # {"test": ..., "lint": ..., "typecheck": ...}, non-empty only
def detect_test(root: Path) -> str: ...

# curkit/speckit.py
def active(root: Path) -> bool: ...
def feature_dir(root: Path) -> Path | None: ...
def tasks_path(root: Path) -> Path | None: ...

# curkit/here.py
def seed(root: Path, runner=subprocess.run) -> list[str]: ...   # log lines; raises SeedError when specify is missing

# curkit/install.py
def install_hooks(home: Path, command: str) -> list[str]: ...   # command = absolute path to bin/cur-kit
def link_bin(home: Path, target: Path) -> str: ...

# curkit/check.py
def run_check(root: Path) -> dict: ...

# curkit/hooks.py
def project_root(payload: dict) -> Path: ...
def on_stop(payload: dict) -> dict: ...
def on_session_start(payload: dict) -> dict: ...
```

### The check result (contract between check, followup, hooks, and the workflow)

```json
{
  "configured": true, "ok": false, "red": true, "reused": false, "key": "sha256-or-null",
  "outcomes": [{"name": "test", "command": "pytest -q", "code": 1, "timed_out": false, "seconds": 1.2, "output": "tail"}],
  "failing": ["tests/test_auth.py::test_US1_AC2_redirects"],
  "ids": ["US1/AC2"],
  "tasks_for_ids": [{"id": "T014", "text": "T014 [US1] Implement login in src/auth.py"}],
  "open": 2, "open_tasks": ["T042", "T043"],
  "guard": ["T015 [US2] is checked, but no passing test cites US2."],
  "unplanned": ["src/extra.py"],
  "feature_dir": "specs/001-login"
}
```

`red` is true when the project is configured and either a command failed or timed out, or `guard` has entries.
`guard` is `null` when there is no JUnit report. The workflow condition reads `open` and `red`.

## Acceptance criteria

Engine, parsing (Fable A):

- AC-01 `keys_in` finds `FR-003`, `SC-002`, `US1`, `US1/AC2` in plain text and in test-name forms (`test_US1_AC2_x`,
  `us1_ac2`, `fr_003`, `FR003`, `US1-AC2`, `US1 AC2`). It also reads Spec Kit's own heading and converge wording:
  `User Story 4` is `US4`, and `User Story 4 AC1` or `User Story 4 acceptance scenario 1` is `US4/AC1`. Output is
  canonical (`US1/AC2`, `FR-003`), unique, first-seen order. It does not match inside other words (`BUS1`, `xFR-003`,
  `User Stories`) or longer numbers (`FR-0031`).
- AC-02 `parse_tasks` reads Spec Kit lines (`- [ ] T012 [P] [US1] Create User model in src/models/user.py`) and converge
  lines (`- [ ] T042 Add export per US2/AC1 (missing)`). It ignores non-task lines and handles `[x]` and `[X]`.
- AC-03 `read_junit` reads pytest, Jest, and Bun style reports, including nested `<testsuites>`. A case with `<failure>`
  or `<error>` is failed. A `<skipped>` case is not failed. Missing or malformed files return `None`.
- AC-08 `violations`: every done task with a story label needs at least one passing case (not failed, not skipped)
  whose name cites that story (`US1` or `US1/ACn`), and no citing case may fail. Messages name the task id and story.
  `None` cases means skipped.
- AC-07 `compose` lists failing names, scenario ids with the tasks that cite them, each failing command with the last
  30 lines of its output, and guard messages. It ends with `TAIL`: "If you're implementing a task, fix this before
  marking it done. If this was a spec skill, note it under the task and leave the code alone. Mark nothing [x] while
  the suite is red." When a command timed out, it says so, names the `timeout` key in `.cursor/cur-kit.json`, and does
  not tell the agent to fix code. With `repeat=True` it adds that the same failure came back after a change, and that
  if the agent can't fix it, it should stop and tell the user. The header includes `(loops+1)/25`.

Engine, running (Opus A):

- AC-04 `fingerprint` changes when a tracked file changes, an untracked file is added or edited, `HEAD` moves, or `salt`
  changes. It does not change for gitignored files. It works in a repo with no commits. `None` outside git.
  `changed_files` lists modified, staged, and untracked paths relative to the root.
- AC-05 `run_all` runs all commands at the same time (wall time is near the slowest, not the sum), records exit codes,
  combined stdout and stderr (last 200 lines), and seconds. A command over `timeout` is killed with its whole process
  group, `timed_out=True`, `code=None`. Empty commands are skipped.
- AC-06 `should_report`: a new failure is reported (count 1). The same failure again is reported once more (count 2).
  After that it is not reported until the failure changes. `failure_print` uses sorted failing names when there are any.
  Otherwise it uses the last 20 output lines with digits replaced, so timings don't change it.
- AC-09 `State` reads and writes `last-run.json`, `latch.json`, and `runs.jsonl` under `.cursor/cur-kit/state/`,
  creating the folder on first write. A corrupt file reads as missing.

Installer (Opus B):

- AC-10 `load` fills defaults (`lint`, `typecheck`, `junit` empty; `timeout` 300; `cache` true), ignores unknown keys,
  and returns `None` for a missing file or a non-object. `detect_test` returns
  `python3 -m pytest -q || test $? -eq 5` for `pyproject.toml`, `pytest.ini`, or `setup.py` (pytest exits 5 when there
  are no tests yet); `bun test` for a `package.json` with a `test` script; otherwise `""`.
- AC-11 `active` is true when `.specify/` exists and `integration_state_schema` in `.specify/integration.json` is missing
  or the integer 1. `feature_dir` runs `check-prerequisites --json --paths-only` (sh by default, ps on Windows, py when
  `.specify/init-options.json` says `"script": "py"`) and returns `FEATURE_DIR` as a path. It returns `None` if the script
  is missing, fails, times out, or prints no `FEATURE_DIR`. `SPECIFY_FEATURE_DIRECTORY` wins when set. Base it on
  `~/Work/cursor-bootstrap/hooks/speckit.py`.
- AC-12 `seed` with `.specify/` present runs no `specify init`. In an empty directory it runs
  `specify init --here --integration cursor-agent --non-interactive`. In a non-empty directory without `.specify/` it adds
  `--force`. When `specify` is not on PATH it raises `SeedError` with an install hint.
- AC-13 `seed` writes only files that are missing and never overwrites: `.cursor/cur-kit.json` (with `detect_test`),
  the five agent files, `.cursor/rules/cur-kit.mdc`, `.cursor/cur-kit/workflow.yml`. It appends
  `.cursor/cur-kit/state/` to `.gitignore` once. It never touches `.specify/` or `.cursor/skills/`.
- AC-14 Agent files: `cur-kit-scout`, `cur-kit-writer`, `cur-kit-witness` use `model: composer-2.5`; `cur-kit-reviewer`
  uses `model: grok-4.7[effort=xhigh,context=500k]`; `cur-kit-diagnose` uses `model: grok-4.7-medium`. Each has `name`, `description`,
  `model` frontmatter. Scout, witness, reviewer, and diagnose say they are read-only. The writer says: one task, only its
  own files, red test first named after the scenario key, minimum code, never run the full suite, return files touched,
  the red and green output, and open questions. The reviewer compares the scenario text to the test, gets the spec and
  the test (not the writer's transcript), and does not run `speckit-analyze`.
- AC-15 `workflow.yml` is the page's loop: a `do-while` with `max_iterations: 3` and condition
  `{{ steps.remaining.output.data.open > 0 or steps.remaining.output.data.red }}`; `speckit.implement` with
  `input.args: "{{ steps.remaining.output.stdout | default('') }}"`; `speckit.converge`; a `shell` step `remaining` running
  `cur-kit check --json` with `output_format: json` and `timeout: 900`; then a gate with options
  `[done, implement, clarify, plan]` and `on_reject: skip`. Both command steps take `integration: "{{ inputs.integration }}"`
  from an `integration` input that defaults to `"auto"`. It has `schema_version`, `workflow.id` `cur-kit-converge`, and
  `requires.speckit_version: ">=1.0.13"`. `specify workflow add <file>` (with a `.specify/` folder present) validates it.
  Found in wave 1: without `on_reject: skip` the validator rejects the gate, and without the integration input the
  command steps can't start the agent.
- AC-16 `install_hooks` merges into `HOME/.cursor/hooks.json`: `stop` runs `<command> hook stop` (timeout 900,
  loop_limit 25) and `sessionStart` runs `<command> hook session-start` (timeout 10). It is idempotent, keeps every other
  entry, and creates the file if missing. `link_bin` symlinks `HOME/.local/bin/cur-kit` to the target.
- The rule `.cursor/rules/cur-kit.mdc` (`alwaysApply: true`) states the contract: Always Run; the parent plans and
  children write through `cur-kit-writer`, at most two at once on separate files; test names cite `FR-###`, `SC-###`,
  `USn`, `USn/ACn`; nothing is marked `[x]` while red or before the reviewer matched the scenario to the test; hooks never
  start a skill, the human types skills or runs `specify workflow run .cursor/cur-kit/workflow.yml`; the one-writer files
  (`spec.md`, `plan.md`, `research.md`, `tasks.md`, checklists, `CHANGELOG.md`, `.cursor/cur-kit.json`); secrets never go
  in messages; record each child as one JSON line in `.cursor/cur-kit/state/slots.jsonl`.

Glue (Opus C):

- AC-17 `run_check` returns `configured: false` without a config or test command. It deletes a stale JUnit file before
  running, reuses the last result when `cache` is on and the fingerprint (salted with the commands and junit path)
  matches, and otherwise runs `run_all`. It fills every field of the check result, recomputes tasks and guard on every
  call, and logs each run. Without JUnit, `ids` come from the failing commands' output.
- AC-18 `cur-kit check` and `cur-kit check --json` print the check result as JSON and exit 0, even when red.
- AC-19 `on_stop` returns `{}` outside a cur-kit project, when `status` is not `completed`, or when `loop_count >= 25`.
  Green clears the latch and returns `{}`. Red returns `{"followup_message": ...}` as the latch allows, with
  `repeat=True` on the second report.
- AC-20 `on_session_start` clears the latch and returns `{}`.
- AC-21 `bin/cur-kit` works when called through a symlink from another directory. `cur-kit --version` prints the version.
  `cur-kit install [--home DIR]` installs the hooks and the bin link. `cur-kit --here` seeds the current directory.

End to end (Opus D):

- AC-22 In a temporary git project with a Spec Kit layout, a failing command that writes JUnit for
  `test_US1_AC2_redirects` makes `cur-kit hook stop` return a follow-up naming `US1/AC2` and its task. The same failure
  twice more gives one more follow-up, then `{}`. After the fix, `{}`. `cur-kit check --json` reports `open` and `red`.
  One test runs a real `specify init` in a temp directory through `cur-kit --here` and is skipped when `specify` is missing.

Quality (everyone):

- AC-23 `python3 scripts/gates.py curkit tests scripts` passes: files at most 200 lines and 10 functions; functions at
  most 20 lines, 3 params (not counting `self`), nesting depth 2.
- AC-24 `scripts/check.sh` passes: coverage at least 80% and `ruff` clean.

## Wave 2 algorithms (from wave 1 findings)

`run_check(root)`:

1. `cfg = config.load(root)`. No config or empty `cfg.test`: return `configured: false`, `ok: true`, `red: false`, with
   `open`/`open_tasks`/`feature_dir` still filled from tasks when Spec Kit is active.
2. `cmds = config.commands(cfg)`; `salt = json.dumps([cmds, cfg.junit], sort_keys=True)`; `before = tree.fingerprint(root, salt)`.
3. If `cfg.cache` and `before` is not None and `state.last()["key"] == before`: reuse the stored run (`reused: true`).
4. Otherwise delete the JUnit file if `cfg.junit` is set, `run_all(cmds, root, cfg.timeout)`, read JUnit, then compute
   `after = tree.fingerprint(root, salt)` and store the run under `after`. The report written by this run is part of the
   next run's tree, so a key taken before the run would never match.
5. The stored run holds `ok`, `outcomes`, `cases` (name, failed, skipped), `failing`, `ids`, and `key`. Without JUnit,
   `ids` come from `ids.keys_in` over the output of the failing outcomes.
6. On every call (reused or not): resolve `speckit.tasks_path(root)`, parse tasks, fill `open`, `open_tasks`,
   `tasks_for_ids` (`tasks_citing(tasks, ids)` as `{"id", "text"}`), `guard` (`violations(tasks, cases)`), and `unplanned`
   (`tree.changed_files(root)` minus every task path, minus anything under `.cursor/`, `.specify/`, or `specs/`).
7. `red = not ok or bool(guard)`. Log `{at, key, reused, ok, red, seconds, ids, open}` with `State.log`.

`on_stop(payload)`:

1. `status` other than `completed`, or `loop_count >= followup.MAX_LOOPS`: `{}`. Not a cur-kit project
   (`config.load(project_root(payload))` is `None`): `{}`.
2. `result = run_check(root)`. Not red: `State.clear_latch()`, `{}`.
3. `failure = state.failure_print(result["failing"], output)` where `output` joins the failing outcomes' output; when the
   commands passed but `guard` has entries, use `state.failure_print(["guard: " + g for g in guard], "")`.
4. `report, latch = state.should_report(State.latch(), failure)`; save the latch. Report only when allowed, with
   `repeat = latch["count"] == 2`. The count keeps rising after 2, so use equality.
5. Any exception: return `{}` and append `{"at", "error"}` to the run log if the state folder can be written.

`project_root(payload)`: `CURSOR_PROJECT_DIR` when set, else the first entry of `payload["workspace_roots"]`, else the
current directory.

CLI: `cur-kit --here` catches `here.SeedError` (print the message, exit 1). `cur-kit install [--home DIR]` catches
`install.InstallError` (exit 1); it passes the absolute path of `bin/cur-kit` to `install_hooks` and `link_bin`.
`cur-kit hook <stop|session-start>` reads JSON from stdin, prints JSON, and always exits 0.

## Review round (Fable B findings, accepted)

These override the sections above where they differ.

- R1 (S1) The check result keeps at most 30 lines and 4000 characters of `output` per outcome, and at most 50 `failing`
  names. The workflow passes the whole check stdout to implement as one argument, and Linux caps one argument at 128 KiB.
- R2 (S2) `tree.tracked_print(root, salt)` fingerprints `HEAD` and tracked changes only. `run_check` takes it before and
  after the run. If it changed during the run, store the run with `key: null`, so the next call runs again. Otherwise
  store the full fingerprint taken after the run, as before. Untracked artifacts the suite writes (the JUnit report,
  `.coverage`) still allow reuse.
- R3 (S3) `red = not ok or bool(failing) or bool(guard)`. A command that exits 0 while its JUnit report has failures is red.
- R4 (S4) `config.load` clamps `timeout` to at most 850 seconds, below the stop hook's 900-second entry.
- R5 (S5) `bin/cur-kit` does not export `PYTHONPATH`. It puts the repo root on `sys.path` inside Python, so the project's
  own commands run with the user's environment unchanged.
- R6 (S6, N6) `install_hooks` shell-quotes the command and replaces existing cur-kit entries for the same event (a command
  containing `/bin/cur-kit` and ending in ` hook stop` or ` hook session-start`) instead of adding a second one.
- R7 (S7) `config.load` sets `junit` to `""` when it is absolute or resolves outside the root.
- R8 (S9) `unplanned` leaves out the JUnit report path.
- R9 (N2) `cur-kit check` catches internal errors and still prints JSON (`configured`, `ok: false`, `red: true`,
  `error`) and exits 0.
- R10 (N3) Without JUnit, `ids` come only from output lines that contain "fail" or "error" (any case).
- R11 (N5) `run_check` resolves the feature folder once per call.
- R12 (N1, N7) With `repeat=True` and `result["reused"]` true, the follow-up says the same failure is still there and
  nothing in the tree changed. When `feature_dir` is null it says no `tasks.md` was found, instead of saying no task
  cites the ids.
- R13 (N4) A task line with any mark other than `x` or `X` (for example `[-]` or `[~]`) is open.
- R14 (N8) `cur-kit-writer.md` says the full suite runs after the turn, through the stop hook or `cur-kit check` in a
  workflow step. The writer file and the rule say commits and pushes are the parent's.
- R15 (S8, N9, N10, N11) README: cur-kit projects always have `.specify/`, so the old `tdd_stop.py` stays quiet there,
  but `codex_stop.py` can still follow up; remove the old pack's stop hooks when switching. Story keys are not scoped to
  a feature. Follow-ups carry up to 30 lines of test output, so keep secrets out of test output. Ignore
  `.cursor/cur-kit/state/` when writing the config by hand. A suite that alternates between two failures defeats the latch.

## Process for every writer

1. Read this spec and the files you own (they may not exist yet).
2. Red: write the tests for your criteria first. Run only your test files, for example
   `python3 -m pytest -q tests/test_ids.py`, and keep the failing output.
3. Green: write the minimum code. Run your tests again.
4. Refactor while green. Run `python3 scripts/gates.py <your files>` and `uvx ruff check <your files>`.
5. Return: the files you created, the red output (short), the green output, the gates and ruff output, and anything
   you needed outside your files.

References:

- Spec Kit commands: `~/.local/share/uv/tools/specify-cli/lib/python3.13/site-packages/specify_cli/core_pack/commands/`
  (`tasks.md` for the task format, `converge.md` for the convergence format and keys like `US1/AC2`).
- Spec Kit workflow engine and step types: `.../specify_cli/workflows/` (`step/` holds `do_while`, `shell`, `gate`).
- The old pack: `~/Work/cursor-bootstrap/hooks/speckit.py` and `hooks/tdd_stop.py`.
