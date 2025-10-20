---
title: "Developer Guide: Language Layer Selection"
id: "dev-guide-language-layer-selection"
type: [ guide ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "27-10-2023"
tags: [guide, developer, language-selection]
links:
  tooling: []
---

# Developer Guide: Language Layer Selection

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: DD-MM-YYYY
- **Last Updated**: 2025-10-13
- **Audience**: Project maintainers, AI agents helping with setup

## 1. Purpose

This guide helps project maintainers and AI agents select the minimal set of language modules that satisfy project requirements while keeping CI fast when preparing a new Auriora repository.

## 2. Steps

### Preparation

- Review product requirements in `docs/1-requirements/` to identify languages and tooling expectations.
- Confirm which teams will maintain the project and their preferred ecosystem.
- Ensure `templates-enabled.yml` is up to date with the language layers you plan to use.

### Procedure

1. Open `templates-enabled.yml` and set `true` for each required language layer.
2. Copy the matching files from `templates/<language>/` into the repository root (replace placeholder names as necessary).
3. Run `scripts/bootstrap/setup-environment.sh` to install dependencies.
4. Execute `scripts/ci/run.sh` and address any missing tooling or configuration errors.
5. Update documentation to reflect chosen languages (e.g., note runtime versions in `README.md`).

### Rollback / Recovery

- To remove a language module, set the flag back to `false`, delete the copied files, and re-run the bootstrap script.
- If CI fails due to missing toolchains, comment out the language layer temporarily and add a follow-up task to restore it.

### Post Actions

- Record the decision in `docs/2-architecture/` or `docs/updates/` as appropriate.
- Align Dependabot configuration with the enabled ecosystems.

## 3. Troubleshooting

List common issues and resolutions.

# References

- Link to scripts, docs, or external references.
- Link to additional resources, specifications, or related tickets.
