# Tooling Reference

- **Version**: 1.0.0
- **Scope**: Project Scripts & Automation

## Summary

This document provides a reference for the core command-line interface (CLI) scripts and automation tooling used in this project. It should be updated with project-specific content after cloning the template.

## Specification

| Tool / Command | Description |
|---|---|
| `scripts/ci/run.sh` | Runs all CI checks, including linting and testing for enabled language layers. This is the main entrypoint for CI validation. |
| `scripts/dev/run-smoke-tests.sh` | Performs a quick validation of the repository's structure and configuration to ensure the template is sound. |
| `scripts/bootstrap/...` | Contains scripts for setting up local development environments. (Varies by language) |

## Usage Notes

- Most scripts are designed to be run from the repository root.
- Refer to the individual scripts in the `scripts/` directory for more detailed usage instructions and available options.

## Change Log

- 2025-10-13: Initial document created with baseline template scripts.
