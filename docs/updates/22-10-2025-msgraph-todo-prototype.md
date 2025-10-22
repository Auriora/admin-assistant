---
title: "Update: MS Graph To Do Repository Prototype"
id: "update-msgraph-todo-prototype"
type: [ update ]
status: [ draft ]
owner: "Codex Agent"
last_reviewed: "22-10-2025"
tags: [update, todo, graph]
links:
  tooling: [pytest]
---

# Update: MS Graph To Do Repository Prototype

- **Owner**: Codex Agent
- **Created Date**: 22-10-2025
- **Audience**: [Developers, Integrators]
- **Related**: n/a
- **Scope**: core/data-access

## 1. Purpose

Capture the prototype work that adds a Microsoft Graph-backed To Do repository capable of reading all incomplete tasks (including flagged emails) and applying updates. This foundation will let future orchestration deliver parity with the Microsoft To Do experience.

## 2. Summary

- Introduced `core.todo` domain models for tasks, linked resources, and Graph date metadata.
- Added an MS Graph repository that enumerates every list, follows `@odata.nextLink`, and enriches flagged emails with body preview/content when Graph omits it.
- Implemented `update_task` to send Graph PATCH requests with `If-Match` support and refresh the task before returning.
- The repository guarantees the following fields today: core identifiers, all Graph date blocks (due/start/reminder), status, importance, attachment flags, categories, body content + preview, etag, linked resource metadata (application, display name, external id, web link, preview/body), and raw Graph payload.
- Known limitations / TODOs: no CLI wiring yet, create/delete not implemented, no batching for bulk updates, message enrichment skips when Graph blocks access, and Graph throttling/backoff is still TODO.

## 3. Implementation Notes

- Key modules: `src/core/todo/models.py`, `src/core/todo/repositories/msgraph_task_repository.py`.
- Reused `core.utilities.graph_utility.get_graph_client` for token handling; HTTP is performed with signed REST calls to minimise SDK friction.
- Tests (`tests/unit/todo/test_msgraph_task_repository.py`) mock Graph responses for pagination, flagged email enrichment, and update flows.
- Rules consulted: Coding Standards (priority 100), General Preferences (priority 50), Documentation Conventions (priority 20), Testing Conventions (priority 25).
- Tests executed: `pytest tests/unit/todo/test_msgraph_task_repository.py`.

## 4. Documentation & Links

- Prototype notes only; no public CLI or API surface changed yet.
- Requirements reference: `docs/1-requirements/REQ-Microsoft-ToDo-MCP-Spec.md`.

# References

- Microsoft Graph To Do API docs: https://learn.microsoft.com/graph/api/resources/todo-overview
