---
title: "Migration Plan: Integrating PA Admin Capabilities into Admin Assistant"
id: "MIG-001"
type: [ implementation, migration ]
status: [ draft ]
owner: "Auriora Team"
last_reviewed: "22-10-2025"
tags: [todo, migration, admin-assistant, integration]
links:
  related:
    - "../2-architecture/README.md"
    - "../1-requirements/REQ-Microsoft-ToDo-MCP-Spec.md"
---

# Migration Plan: Integrating PA Admin Capabilities into Admin Assistant

- **Owner**: Auriora Team  
- **Status**: Draft  
- **Created Date**: 22-10-2025  
- **Last Updated**: 23-10-2025  
- **Audience**: Migration engineers, maintainers of both repositories

## 1. Purpose

This document describes how the existing PA Admin functionality will be merged into the Admin Assistant architecture. It records the current migration status, enumerates the remaining work, and provides a module-by-module mapping so that the consolidation can happen in staged, reviewable increments.

## 2. Current Status Snapshot

| Step | Description | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Prototype Microsoft To Do repository and domain models in Admin Assistant | ✅ Complete | `admin-assistant/src/core/todo/models.py`, `admin-assistant/src/core/todo/repositories/msgraph_task_repository.py`, `admin-assistant/tests/unit/todo/test_msgraph_task_repository.py` |
| 2 | Port PA Admin clustering, deduplication, and AI orchestration into Admin Assistant services | ✅ Complete | `admin-assistant/src/core/todo/services/clustering_service.py`, `admin-assistant/src/core/todo/services/exact_duplicate_service.py`, `admin-assistant/src/core/todo/ai/dedup_orchestrator.py`, `admin-assistant/tests/unit/todo/test_dedup_orchestrator.py` |
| 3 | Port action execution, rule processing, and rollback flows into Admin Assistant orchestrators | ⏳ Pending | N/A |
| 4 | Expose new To Do capabilities through CLI and scheduling surface | ⏳ Pending | N/A |
| 5 | Decommission redundant PA Admin packages and finalise documentation/testing | ⏳ Pending | N/A |

**Step 1 confirmation:** The Admin Assistant repository now contains a `core.todo` package with Graph-aware models, a high-fidelity task repository that uses OData queries, a PATCH-enabled `update_task` method, and unit tests covering pagination plus flagged-email enrichment. This satisfies the prerequisites for migrating higher-level PA Admin logic.

## 3. Migration Strategy

The migration progresses “outside-in”: start with data access (completed), then move pure services, then orchestrators/actions, and finally surface area (CLI, jobs, docs). Each phase should land as an independent pull request in Admin Assistant, with matching removals or adapters in PA Admin only after parity is proven.

### Phase 2 – Deduplication & AI Services

| PA Admin Component | Target Location in Admin Assistant | Migration Notes |
| --- | --- | --- |
| `src/pa_admin/dedup/clustering.py` | `src/core/todo/services/clustering_service.py` (new) | Convert `TaskClusterer` into a service that accepts Admin Assistant `Task` models and emits cluster DTOs. Replace YAML-driven threshold configuration with values sourced from Admin Assistant’s configuration system. |
| `src/pa_admin/dedup/exact_match.py` | `src/core/todo/services/exact_duplicate_service.py` | Keep pure functions; inject via service container for testability. |
| `src/pa_admin/ai/prompts.py`, `src/pa_admin/ai/parser.py`, `src/pa_admin/ai/batch.py` | `src/core/todo/ai/` namespace | Adapt to Admin Assistant prompt repository + logging. Replace file-system batch directories with Admin Assistant’s storage abstractions. |
| `src/pa_admin/ai/orchestrator.py` | `src/core/todo/services/ai_dedup_service.py` | Refactor to accept Admin Assistant config, OpenTelemetry, and to emit structured decisions for persistence. |

### Phase 3 – Actions & Orchestration

| PA Admin Component | Target Location | Migration Notes |
| --- | --- | --- |
| `src/pa_admin/actions/executor.py` | `src/core/todo/services/action_executor.py` | Replace tqdm console output with Admin Assistant logging. Persist `ActionResult` to existing audit/reversible-operation tables. |
| `src/pa_admin/actions/move.py`, `src/pa_admin/actions/rules.py` | `src/core/todo/services/move_service.py`, `src/core/todo/services/rule_service.py` | Integrate rule storage with Admin Assistant database (shift from YAML). |
| `src/pa_admin/actions/rollback.py` | `src/core/todo/services/rollback_service.py` | Re-implement using Admin Assistant’s reversible operation framework. |
| `src/pa_admin/persistence/backup.py`, `src/pa_admin/persistence/logging.py`, `src/pa_admin/persistence/plan_file.py` | Replace with database-backed equivalents | Convert file-based plan/log outputs into SQL-backed records. Maintain CSV export as optional command. |
| `src/pa_admin/cli/main.py` | `src/cli/commands/todo/*.py` | Add Typer command group mirroring existing CLI conventions, hooking into new services/orchestrators. |

### Phase 4 – Surface Area Integration

1. **CLI**: Introduce `admin-assistant todo plan|execute|rollback` commands. Provide `--dry-run`, `--commit`, `--batch` flags consistent with PA Admin terminology.  
2. **Background Jobs**: Register APScheduler jobs for recurring clean-ups, using the new orchestrator module.  
3. **Observability**: Route metrics and audit logs through Admin Assistant’s existing instrumentation hooks (`core/services/audit_log_service.py`, OTEL instrumentation).  
4. **Documentation**: Update Admin Assistant docs (CAP, CIS, CLI command references) to include To Do operations; link back to this migration record until the merge completes.  

### Phase 5 – Decommissioning PA Admin

Once parity is confirmed:

- Archive PA Admin CLI entrypoints (`todo_cleanup.py`, `src/pa_admin/cli/`) with pointers to Admin Assistant usage.  
- Migrate residual environment variables to Admin Assistant naming.  
- Retain PA Admin unit tests by porting them into Admin Assistant; remove duplicates post-port.  
- Flag the PA Admin repository as read-only / legacy with a final README update.

## 4. Cross-Cutting Concerns

1. **Configuration** – Consolidate all runtime settings into Admin Assistant’s configuration tables and environment variables. Avoid duplicated `.env` parsing.  
2. **Security** – Reuse Admin Assistant MSAL device login; delete PA Admin’s O365 token handling after parity.  
3. **Testing** – Migrate PA Admin fixtures into Admin Assistant’s `tests` tree. Ensure both unit and integration tests run under existing GitHub Actions workflows.  
4. **Telemetry** – Leverage existing OpenTelemetry spans/counters around orchestration to maintain visibility.  

## 5. Immediate Action Items

1. **Kick-off Phase 2**: Create scaffolding for `core.todo.services` in Admin Assistant and start porting clustering/exact-match logic.  
2. **Define Data Persistence**: Design SQL models for plans/actions so the orchestrator can store state without relying on filesystem artifacts.  
3. **Coordinate Repos**: Open tracking issues in both repositories referencing this document; link Admin Assistant PRs to the plan.  

## 6. Approval & Change Control

| Reviewer | Role | Sign-off |
| --- | --- | --- |
| Bruce Cherrington | Product Owner | ☐ |
| Admin Assistant Maintainer | Code Owner | ☐ |
| PA Admin Maintainer | Code Owner | ☐ |

> Update the checkboxes as sign-offs occur. When the migration is complete, move this document to **status: approved** and add links to final PRs.
