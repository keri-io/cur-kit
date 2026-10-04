#!/usr/bin/env bash
# Full validation: tests under coverage (>= 80%), ruff, and the quality gates.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."
uvx --with pytest --from coverage coverage run -m pytest -q "$@"
uvx --from coverage coverage report --fail-under=80
uvx ruff check curkit tests scripts
python3 scripts/gates.py curkit tests scripts
