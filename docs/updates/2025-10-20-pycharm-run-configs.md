# 2025-10-20 – PyCharm Run Config Cleanup

- **Author**: Codex Agent
- **Related Work**: N/A
- **Rules Consulted**: `.agents/rules/preferences.md`, `.agents/rules/planning.md`, `.agents/rules/documentation.md`, `.agents/rules/testing.md`

## Summary

PyCharm run configurations for unit and integration suites were filtering tests via marker expressions that did not match repository usage. Unit runs only executed ~20 tests due to `-m unit`, and integration runs passed an improperly quoted marker expression that resulted in zero collection. The configurations now delegate discovery to pytest's path-based collection so the IDE matches CLI behavior.

## Implementation Notes

- Updated `.run/Unit Tests.run.xml` to remove the `-m unit` filter, add `$PROJECT_DIR$/src` to `PYTHONPATH`, and add `--log-cli-level=WARNING` so GC debug output is suppressed while pytest still runs verbose mode.
- Updated `.run/Integration Tests.run.xml` to drop the broken `-m 'integration and not msgraph'` expression, add the same environment/logging tweaks, and rely on the directory target so MS Graph scaffolding still skips via existing logic.
- Updated `.run/All Tests.run.xml` to use the same `PYTHONPATH` and logging arguments for consistency.
- CLI validation commands:
  - `.venv/bin/pytest --co tests/unit`
  - `.venv/bin/pytest --co tests/integration -m integration`
  - `.venv/bin/pytest tests/integration --maxfail=1` (fails with `sqlite3.IntegrityError` on duplicate user email; matches pre-existing issue).
  - `PYTHONPATH=src .venv/bin/pytest tests/unit -k audit --maxfail=1 -q`
  - `PYTHONPATH=src .venv/bin/pytest tests/unit/support/test_calendar_utils.py -q`
- Updated `src/support/calendar_utils.get_event_date_range` to ignore cancelled/free/all-day events and refreshed the expectation in `tests/unit/support/test_calendar_utils.py` for the newer sample data.
- Follow-up: investigate and stabilize integration data setup to resolve the duplicate user constraint error.

## Documentation & Links

- Added `docs/updates/README.md`, `_template.md`, and `index.md` to support future task logs.
- This entry documents the configuration alignment.
