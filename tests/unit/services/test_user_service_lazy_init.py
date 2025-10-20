import sys


def test_user_service_does_not_import_db_on_init():
    # Ensure prior imports are cleared
    sys.modules.pop('core.repositories.user_repository', None)
    sys.modules.pop('core.db', None)

    from core.services.user_service import UserService

    # Constructing the service should not import DB-backed modules
    unused_service = UserService()
    assert 'core.repositories.user_repository' not in sys.modules
    assert 'core.db' not in sys.modules


def test_user_service_imports_repo_only_on_access():
    # Ensure prior imports are cleared
    sys.modules.pop('core.repositories.user_repository', None)
    sys.modules.pop('core.db', None)

    from core.services.user_service import UserService

    svc = UserService()

    # Accessing repository triggers import (may create engine/session); swallow any runtime errors
    try:
        _ = svc.repository
    except Exception:
        # It's OK if accessing the repository triggers DB-related errors in this environment;
        # this test only verifies that imports happen lazily on first access.
        pass

    assert 'core.repositories.user_repository' in sys.modules
    assert 'core.db' in sys.modules
