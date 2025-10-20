import pathlib

import pytest


_UNIT_ROOT = pathlib.Path(__file__).parent.resolve()


def pytest_collection_modifyitems(config, items):
    """Ensure every test under tests/unit/ carries the unit marker."""
    for item in items:
        try:
            path = pathlib.Path(item.fspath).resolve()
        except Exception:
            continue
        if _UNIT_ROOT in path.parents or path == _UNIT_ROOT:
            item.add_marker(pytest.mark.unit)
