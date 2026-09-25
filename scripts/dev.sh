#!/usr/bin/env bash
# Run every local gate CI runs, in the same order. Usage: scripts/dev.sh
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --all-groups --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run python scripts/check_coverage_floors.py
echo "dev.sh: all gates passed"
