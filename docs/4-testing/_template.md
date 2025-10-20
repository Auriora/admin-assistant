---
title: "Test Strategy: {{title}}"
id: "test-{{id}}"
type: [ testing ]
status: [ draft | in_review | approved ]
owner: "{{owner}}" # e.g., QA Team, Lead Tester
last_reviewed: "{{DD-MM-YYYY}}"
tags: [testing, strategy, qa, tag1, tag2] # Practical tags for organization and search
links:
  tooling: [ruff, mypy, bandit]
---

# Test Strategy: {{title}}

- **Owner**: {{owner}} # e.g., QA Team, Lead Tester
- **Status**: [Draft | In Review | Approved]
- **Created Date**: DD-MM-YYYY
- **Last Updated**: DD-MM-YYYY
- **Audience**: [e.g., QA Team, Developers, Stakeholders]
- **Scope**: [e.g., Entire project, specific module, feature X]

## 1. Purpose

[Establish the objectives, quality targets, and gating criteria for testing this project or component.] Clearly state the objective and scope of this test strategy document.

## 2. Test Matrix

| Level | Purpose | Tooling | Owner |
| --- | --- | --- | --- |
| Unit | [e.g., Baseline correctness] | [e.g., pytest, vitest] | [e.g., Development Team] |
| Integration | [e.g., Component interaction] | [e.g., API tests, end-to-end frameworks] | [e.g., QA Team] |
| End-to-End | [e.g., User journey validation] | [e.g., Playwright, Cypress] | [e.g., QA Team] |

## 3. Environments

[List required testing environments, data fixtures, and any necessary access credentials (redacted).]

## 4. Automation

- [Describe CI jobs and triggers related to testing.]
- [Specify expectations for reporting and artifacts.]

## 5. Manual Validation

[Document any exploratory or manual testing steps that supplement automation.]

## 6. Risks & Mitigations

[Highlight known gaps in testing, potential risks, and planned mitigations.]

<!-- Add more numbered sections as needed, e.g., ## 7. [Another Section Title] -->

# References

- Link to additional resources, specifications, or related tickets.
