---
title: "Update: Link Checker Refinement"
id: "update-link-checker-refinement"
type: [ update ]
status: [ approved ]
owner: "Codex Agent"
last_reviewed: "21-10-2025"
tags: [update, tooling, documentation]
links:
  tooling: [python]
---

# Update: Link Checker Refinement

- **Owner**: Codex Agent
- **Created Date**: 21-10-2025
- **Audience**: Developers
- **Related**: scripts/link_checker.py
- **Scope**: docs tooling

## 1. Purpose

Improve the Markdown link checker so that canonical path cleanups stop obscuring genuinely missing documentation links.

## 2. Summary

- Separated canonical path recommendations from missing-target failures so contributors can focus on real breakages.
- Added an opt-in `--fail-on-style` flag to promote canonical enforcement when needed without blocking day-to-day checks.
- Retained automatic fixes for canonical issues while continuing to report unresolved links.

## 3. Implementation Notes

- Updated `scripts/link_checker.py` to track canonical mismatches independently from missing targets and directory errors.
- Verified new behaviour via `python scripts/link_checker.py` (non-zero exit caused only by unresolved links).
- No additional follow-up required beyond addressing the outstanding missing targets that the checker now highlights.

## 4. Documentation & Links

- N/A

# References

- None
