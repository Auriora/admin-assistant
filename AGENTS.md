# AGENTS

This repository uses centralized agent instructions located in the hidden directory `.agents/rules/`.

- The rule files in `.agents/rules/` are the single source of truth and take precedence over any guidance elsewhere in the repo.
- To avoid duplication or conflicts, this file intentionally does not restate operational commands, workflows, or protocols.

For general project context and developer documentation, refer to:
- `README.md` (project overview, commands, architecture)
- `docs/` (AI model configuration, Batch API, GPT-5 parameter notes, plan/execute workflow, migration guide)
- `CLAUDE.md` (editor-specific tips, if applicable)

If you are implementing or running agents/tools:
- Load `.agents/rules/` at task start and follow the highest-priority instructions found there.
- Log task-scoped notes and updates in `docs/updates/` using the repository template.

This document is intentionally minimal to prevent divergence from `.agents/rules/`. Consult those rule files first, and prefer updating them over this file when behavior or priorities change.
