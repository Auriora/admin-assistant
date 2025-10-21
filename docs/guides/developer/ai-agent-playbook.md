---
title: "Developer Guide: AI Agent Playbook"
id: "dev-guide-ai-agent-playbook"
type: [ guide ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "27-10-2023"
tags: [guide, developer, ai-agent, playbook]
links:
  tooling: []
---

# Developer Guide: AI Agent Playbook

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: 27-10-2023
- **Last Updated**: 2025-10-13
- **Audience**: AI Agents

## 1. Purpose

AI agents collaborating on Auriora projects must follow these practices to remain predictable and safe.

## 2. Steps

### Core Principles

1. Load `docs/guides/agents/` before planning or editing files.
2. Default to minimal planning for simple, single-file tasks; invoke the planning protocol for complex or multi-language changes.
3. Record significant actions in `docs/updates/` with references to the rules consulted.

### Workflow

- **Discovery**: Inspect `templates-enabled.yml`, `scripts/`, and `.github/workflows/` to understand the tooling landscape.
- **Planning**: Use the staged planning protocol outlined in `.agents/rules/planning.md` when work spans multiple modules or impacts CI.
- **Execution**: Prefer `scripts/` entrypoints (e.g., `scripts/ci/run.sh`) to validate changes. Avoid destructive git commands unless explicitly requested.
- **Documentation**: Keep docs aligned with folder-specific templates and update cross-links.

### Communication

- Ask clarifying questions if requirements or constraints are ambiguous.
- Surface risks or trade-offs early, especially when modifying automation or licensing.

### Handoff Checklist

- [ ] `git status` clean or intentional changes noted
- [ ] Tests and linters relevant to the change have been run
- [ ] Documentation updated and indexed
- [ ] Rules consulted are listed in the update log or PR description

## 3. Troubleshooting

List common issues and resolutions.

# References

- Link to scripts, docs, or external references.
- Link to additional resources, specifications, or related tickets.
