---
title: "Typing Remediation for Core Services"
id: "rfc-typing-remediation-20251020"
type: [ plan ]
status: draft
owner: "Automation Team"
last_reviewed: "20-10-2025"
tags: [plan, typing, mypy]
links:
  tooling: [mypy]
---

# RFC: Typing Remediation for Core Services

- **Owner**: Automation Team
- **Status**: Draft
- **Last Updated**: 20-10-2025
- **Created Date**: 20-10-2025
- **Audience**: Engineering, QA

## 1. Purpose

Capture outstanding mypy failures introduced by strict optional defaults and untyped collections across the core, CLI, and web packages. This plan records remediation tasks so we can resume after higher-priority work without losing context.

## 2. Problem Statement

- Recent mypy run (`mypy src/core/ src/cli/ src/web/ --ignore-missing-imports`) reports 162 errors across 37 files.
- Issues span missing stubs, improper Optional defaults, untyped accumulators, and mismatched overrides between repository interfaces.
- Without a structured fix, type checking remains disabled in CI, blocking stricter enforcement.

Success criteria:

1. mypy executes with zero errors using current flags.
2. No runtime regressions are introduced (targeted test suites remain green).
3. Documentation of new typing patterns (e.g., SQLAlchemy `Mapped[...]`) is added where appropriate.

Constraints:

- Large surface area; work must be batched.
- Some modules rely on legacy dynamic patterns; incremental refactors required.

## 3. Proposed Solution

Break remediation into focused workstreams:

1. **Stub Installation & Configuration**
   - Ensure `types-pytz`, `types-python-dateutil`, and `types-requests` remain pinned in dev requirements.
   - Re-run mypy after installation to confirm stub-related errors are cleared.

2. **Optional Defaults & Signature Hygiene**
   - Update functions using `arg: str = None` to `Optional[str]` (or `str | None`).
   - Prioritise CLI utilities (`cli/common/utils.py`) and migrations where defaults are simple.

3. **Collections & Accumulator Typing**
   - Add explicit annotations for result containers in:
     - `timesheet_archive_service.py`
     - `scheduled_archive_service.py`
     - `category_processing_service.py`
     - `background_job_service.py`
   - Introduce helper dataclasses or TypedDicts where the structure is reused.

4. **Repository Interface Alignment**
   - Reconcile MS Graph repositories with their base classes (accept `Union[int, str]` or adjust base signature).
   - Add unit tests covering both `int` and `str` identifiers to prevent regressions.

5. **SQLAlchemy Model Annotations**
   - Migrate key models (`Appointment`, etc.) to `Mapped[...]` declarations.
   - Document the pattern in developer guides.

6. **Utility Modules**
   - `audit_logging_utility`: annotate `details`, `request_data`, `response_data`.
   - `uri_utility`: fix Optional defaults and ensure helper returns precise types.
   - `audit_sanitizer`: replace list/dict mutation patterns with typed structures.

Sequencing: begin with stub installation and signature hygiene to shrink error count, then handle service modules one by one.

## 4. Alternatives

1. Disable mypy entirely — rejected; typing remains valuable for catching regressions.
2. Suppress errors with `# type: ignore` — rejected; masks true defects and increases maintenance cost.
3. Introduce partial `pyproject.toml` section filtering modules — deferred; prefer code fixes first.

## 5. Impact

- **Systems**: Affects core services, repositories, utilities, and select CLI helpers.
- **Risks**: Potential runtime regressions when adding strict typing; mitigated via targeted unit/integration tests.
- **Rollout**: Merge in batches; run mypy + pytest for each.

## 6. Decision Log

- 20-10-2025: Captured outstanding work; no fixes merged yet.

# References

- Mypy output (20-10-2025)
- `docs/plans/_template.md`
