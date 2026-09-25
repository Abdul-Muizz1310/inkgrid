# Pull request

## Spec-TDD checklist

- [ ] Spec written or updated under `docs/specs/`, with enumerated pass and fail cases
- [ ] Failing tests written first and seen failing for the expected reason
- [ ] Implementation brings every test green; nothing was written without a failing test
- [ ] Every enumerated failure case is covered, not only the happy path
- [ ] The composed flow is tested (the CLI or `read_pages` end to end), not only the helpers
- [ ] Coverage floors hold (`uv run python scripts/check_coverage_floors.py`, 80% total and per file)
- [ ] No untyped dicts cross a module boundary; PDF library output is parsed at the adapter
- [ ] The layer table still holds (`tests/test_architecture.py`)

## Summary

<!-- Why this change, not what. -->

## Test plan

- [ ] `uv run ruff check .` and `uv run ruff format --check .`
- [ ] `uv run mypy`
- [ ] `uv run pytest`, and `uv run pytest -m slow --no-cov` when packaging changed
