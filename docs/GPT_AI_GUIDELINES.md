# GPT AI Code Generation Guidelines

This file contains guidelines for AI-generated code in the `admin-assistant` project. All contributors and AI agents must adhere to these standards to ensure maintainability, clarity, and quality. This file must be updated as new requirements or conventions are established.

## General Principles
- **All classes must follow SOLID principles**: Ensure code is modular, extensible, and easy to maintain.
- **Accessibility**: Where applicable, ensure user-facing features are accessible.
- **Comprehensive documentation**: Every class, method, and function must include docstrings explaining its purpose, parameters, and return values.
- **Consistent naming conventions**: Use `snake_case` for variables and functions, `PascalCase` for classes, and `UPPER_CASE` for constants.
- **Documentation as code**: All code must be self-documenting and include comprehensive docstrings and comments where necessary.
- **Don't Repeat Yourself (DRY)**: Avoid code duplication by abstracting common functionality into reusable components, functions, and classes.
- **Error handling**: Implement robust error handling and logging. Avoid silent failures.
- **Extensibility**: Design code to be easily extended for future features.
- **No magic numbers or literals**: All such values must be defined as named constants with clear, descriptive names.
- **Performance awareness**: Write efficient code and avoid unnecessary computations or memory usage.
- **Prioritise Off-The-Shelf (OTS)**: Use established libraries and frameworks (like Flask, SQLAlchemy, etc.) rather than creating custom solutions when appropriate functionality already exists.
- **Security best practices**: Never log or expose sensitive information (e.g., credentials, tokens). Use environment variables for secrets.
- **Separation of concerns**: Keep business logic, data access, and presentation layers separate.
- **Single source of truth**: Avoid duplication of logic or configuration.
- **Testability**: Code should be written to facilitate unit and integration testing. Avoid hard-coded dependencies; use dependency injection where appropriate.
- **Type annotations**: All functions and methods must include type hints for parameters and return values.
- **Observability:** All new code must use OpenTelemetry for distributed tracing. Follow the guidelines in `docs/guidelines/logging.md` for best practices.

## SRS and Design Alignment
- **All AI-generated code and documentation must align with the current Software Requirements Specification (SRS) in `docs/1-requirements/.**` and the design documentation in `docs/2-design/.**`
- The SRS defines the authoritative requirements, use cases, and constraints. The design documentation provides architectural, data model, and feature-specific design details. Any generated code must directly support and not contradict the SRS or design documentation.
- When the SRS or design documentation is updated, these guidelines and all generated code must be reviewed for continued compliance.

## Project-Specific Notes
- This file must be referenced in all AI code generation settings and updated as new requirements arise.
- All code must comply with Microsoft 365 API usage policies and data privacy requirements.

## Project Directory Structure & Frameworks
- The project uses the following structure:

```
admin-assistant/
│
├── app/
│   ├── __init__.py
│   ├── models.py         # SQLAlchemy models
│   ├── routes/
│   │   ├── __init__.py
│   │   └── main.py       # Flask routes/views
│   ├── services/
│   │   ├── __init__.py
│   │   └── ...           # Business logic modules
│   ├── templates/
│   │   └── ...           # Jinja2 HTML templates (Bootstrap)
│   ├── static/
│   │   ├── css/
│   │   │   └── bootstrap.min.css
│   │   └── js/
│   │       └── bootstrap.bundle.min.js
│   └── config.py         # Configuration (env, DB, etc.)
│
├── tests/
│   ├── __init__.py
│   └── test_basic.py     # Pytest starter
│
├── migrations/           # For Alembic/Flask-Migrate (optional, for DB migrations)
│
├── .env                  # Environment variables (not committed)
├── .gitignore
├── requirements.txt
├── run.py                # Entry point for Flask app
│
└── docs/                 # Documentation
```

- **Flask** is used as the web framework, following the application factory pattern for modularity and testability.
- **Bootstrap** is used for responsive UI, included in the `static/` and `templates/` folders.
- **SQLAlchemy** is used for ORM, with models defined in `app/models.py`.
- **Pytest** is used for testing, with tests in the `tests/` directory.
- **SQLite** is the default development database, configurable via `app/config.py`.

---
_Last updated: [2025-05-25]_