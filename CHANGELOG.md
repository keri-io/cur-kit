# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog.

## [Unreleased]

### Added

- Project skeleton, build spec in `docs/spec.md`, and the quality gate checker in `scripts/gates.py`.
- Parsing engine: scenario keys (`ids`), Spec Kit tasks (`tasks`), JUnit reports (`junit`), the check-off guard
  (`guard`), and follow-up text (`followup`).
- Run engine: tree fingerprint and changed files (`tree`), concurrent commands with process-group timeouts (`runner`),
  and run state with the red latch (`state`).
- Installer: config (`config`), Spec Kit adapter (`speckit`), `seed` for `cur-kit --here` (`here`), user hook install
  (`install`), five agent files, the project rule, and the converge loop workflow.
- `cur-kit check` (`check`), the stop and sessionStart hooks (`hooks`), the CLI (`__main__`), and the `bin/cur-kit`
  shim, which runs `python3 -P` so a project's own modules can't shadow the standard library.
- End-to-end tests in `tests/e2e/` that drive `bin/cur-kit` in temp Spec Kit projects, and `README.md`.

### Changed

- `cur-kit-scout`, `cur-kit-writer`, `cur-kit-witness`, and `cur-kit-diagnose` use Grok 4.7 high. Scouts and writers
  run up to twelve at once, and more when the job is large.
- The implement and converge loop tolerates an unmodified Spec Kit install on Cursor Cloud. A chat id that arrives
  only on `stop` no longer drops the turn, a converge prompt that mentions implement in a sentence stays a converge
  turn, and a follow-up is remembered when the prompt hook is skipped.
- After `/speckit-implement`, a green stop submits `/speckit-converge`. If that reply names implement and does not
  say the work is finished, the next stop submits `/speckit-implement`. A red suite still comes back first.
- `cur-kit --here` merges a project `stop` and `sessionStart` hook into `.cursor/hooks.json` and writes
  `.cursor/hooks/cur-kit`, so Cursor Cloud runs the suite. The user-level stop command is `hook stop --user` and stays
  quiet when that project hook is present. A new non-empty `conversation_id` resets the red latch, because managed
  cloud agents do not run `sessionStart`.
- `cur-kit-reviewer` uses Grok 4.7 at extra-high effort with a 500k context window.
- The check-off guard treats a skipped test as not passing.
- `keys_in` reads Spec Kit's own wording: `User Story 4 AC1` and `acceptance scenario 1` become `US4/AC1`.
- `cur-kit --here` writes a pytest command that treats exit code 5, "no tests collected", as green.
- The rule and the writer agent say the parent does not write application code or tests during implement. It gives
  every implementation task to `cur-kit-writer`.
- `install` shell-quotes the hook command and replaces an older cur-kit entry instead of adding a second one.
- The writer agent and the rule say commits and pushes are the parent's.

### Fixed

- The check result caps each command's output at 30 lines and 4000 characters, and `failing` at 50 names, so the
  workflow's implement argument stays under Linux's 128 KiB limit.
- A tracked edit made while the suite runs no longer gets keyed as tested (`tree.tracked_print`).
- A command that exits 0 while its JUnit report has failures is red.
- `timeout` is capped at 850 seconds, below the stop hook's 900, so a slow suite isn't left running.
- A `junit` path outside the project is ignored instead of being deleted before each run.
- `bin/cur-kit` no longer leaks its `PYTHONPATH` into the project's commands.
- `unplanned` no longer lists the JUnit report.
- `cur-kit check` prints JSON and exits 0 on internal errors.
- Without JUnit, scenario ids come only from failure and error lines.
- The Spec Kit feature folder is resolved once per check.
- Follow-up wording for a repeat on an unchanged tree and for a project without `tasks.md`.
- Task lines marked `[-]` or `[~]` count as open.
- A tracked JUnit report that comes back unchanged no longer blocks reuse. The README says to keep the report
  gitignored and explains what an untracked edit during a run does.
