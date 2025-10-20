---
title: "Developer Guide: Template Adoption"
id: "dev-guide-template-adoption"
type: [ guide ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "2025-10-13"
tags: [guide, developer, template-adoption]
links:
  tooling: []
---

# Developer Guide: Template Adoption

- **Owner**: Auriora Team
- **Status**: Approved
- **Created Date**: DD-MM-YYYY
- **Last Updated**: 2025-10-13
- **Audience**: Developers | Maintainers

## 1. Purpose

This guide walks maintainers through the process of cloning the Auriora template into a new repository and configuring it for a new project. It covers initial setup, language layer activation, automation configuration, and documentation best practices.

## 2. Steps

### 1. Create the Repository

1.  Click **Use this template** on GitHub or copy the repository locally.
2.  Rename the remote and update project metadata (e.g., `README.md` title, badges, URLs).

### 2. Enable Language Layers

1.  Review `templates-enabled.yml` and enable the languages required for your project.
2.  Copy files from `templates/<language>/` into the root directory, adjusting namespaces/package names as needed.
3.  Run the corresponding setup scripts located under `scripts/<language>/`.

### 3. Configure Automation

1.  Update GitHub Secrets required by your chosen workflows (refer to `.github/workflows/` comments for specifics).
2.  Confirm that `scripts/ci/run.sh` passes successfully when run locally.
3.  Remove any unused workflows or language layers to keep your CI pipeline lean and efficient.

### 4. Documentation Checklist

1.  Replace placeholder `_template.md` references with project-specific copies where necessary.
2.  Populate `docs/updates/` with an initial setup log entry.
3.  Update `docs/0-project-management/` with the project's launch roadmap, if applicable.

### 5. Governance & Rules

1.  Review the `.agents/rules/` directory and record any adjustments in `docs/updates/`.
2.  Set up branch protection rules, `CODEOWNERS`, and required checks in your GitHub repository settings.

### 6. First Release

1.  Update `CHANGELOG.md` with details for the `0.1.0` release.
2.  Tag the release using the `release.yml` workflow or by manual tagging.

## 3. Troubleshooting

- **CI failures after enabling a language layer**: Ensure all dependencies for the language are installed and that `scripts/<language>/setup.sh` has been run.
- **Broken links in documentation**: Verify relative paths and update `index.md` files where necessary.

# References

- `templates-enabled.yml`
- `scripts/ci/run.sh`
- `docs/guides/developer/ai-agent-playbook.md`
- `docs/0-project-management/_template.roadmap.md`
