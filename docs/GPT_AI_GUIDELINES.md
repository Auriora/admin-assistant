# GPT AI Code Generation Guidelines

This file contains guidelines for AI-generated code in the `admin-assistant` project. All contributors and AI agents must adhere to these standards to ensure maintainability, clarity, and quality. This file must be updated as new requirements or conventions are established.

## General Principles
- **All classes must follow SOLID principles**: Ensure code is modular, extensible, and easy to maintain.
- **Documentation as code**: All code must be self-documenting and include comprehensive docstrings and comments where necessary.
- **No magic numbers or literals**: All such values must be defined as named constants with clear, descriptive names.
- **Comprehensive documentation**: Every class, method, and function must include docstrings explaining its purpose, parameters, and return values.
- **Consistent naming conventions**: Use `snake_case` for variables and functions, `PascalCase` for classes, and `UPPER_CASE` for constants.
- **Type annotations**: All functions and methods must include type hints for parameters and return values.
- **Error handling**: Implement robust error handling and logging. Avoid silent failures.
- **Security best practices**: Never log or expose sensitive information (e.g., credentials, tokens). Use environment variables for secrets.
- **Testability**: Code should be written to facilitate unit and integration testing. Avoid hard-coded dependencies; use dependency injection where appropriate.
- **Separation of concerns**: Keep business logic, data access, and presentation layers separate.
- **Single source of truth**: Avoid duplication of logic or configuration.
- **Extensibility**: Design code to be easily extended for future features.
- **Performance awareness**: Write efficient code and avoid unnecessary computations or memory usage.
- **Accessibility**: Where applicable, ensure user-facing features are accessible.

## Project-Specific Notes
- This file must be referenced in all AI code generation settings and updated as new requirements arise.
- All code must comply with Microsoft 365 API usage policies and data privacy requirements.

---
_Last updated: [2025-05-25]_