# Licensing Guidance

- **Version**: 1.0.0
- **Scope**: Project Licensing & Compliance

## Summary

This document provides guidance on how to select, apply, and document software licenses for projects derived from this template. Auriora projects default to the GNU GPLv3, and this guide outlines the process for using an alternative.

## Specification

### Decision Flow

1.  **Identify upstream dependencies**: Collect licenses for all reused code, libraries, and assets.
2.  **Assess compatibility**: Verify that the default GPLv3 is compatible with all dependencies. If not, select an alternative from the `templates/licenses/` directory.
3.  **Record the decision**: Document the rationale for any license change in an ADR (`docs/2-architecture/`) or RFC (`docs/plans/`).
4.  **Notify stakeholders**: Ensure the decision is reviewed and approved by the relevant parties (e.g., Governance Council).

### Required Updates When Changing Licenses

- Replace the root `LICENSE` file with the new license text.
- Update license badges or references in the main `README.md`.
- Note the change in `CHANGELOG.md` and create an entry in `docs/updates/`.
- Check source files for embedded license headers and update them if necessary.

## Usage Notes

- Always consult with the Auriora Governance Council before applying a non-standard license.
- External resources for checking compatibility:
  - [GNU License Compatibility](https://www.gnu.org/licenses/license-compatibility.html)
  - [Choose a License](https://choosealicense.com/)

## Change Log

- 2025-10-13: Initial document created with standard guidance for Auriora projects.
