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

- The check-off guard treats a skipped test as not passing.
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
