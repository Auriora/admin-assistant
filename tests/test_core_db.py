import importlib
import os

import core.db as db


def test_core_database_url_defined():
    # Ensure the module exposes CORE_DATABASE_URL and it's non-empty
    assert hasattr(db, 'CORE_DATABASE_URL')
    assert isinstance(db.CORE_DATABASE_URL, str)
    assert db.CORE_DATABASE_URL != ''


def test_get_session_returns_session_like_object():
    # get_session should return an object with common SQLAlchemy session methods
    sess = db.get_session()
    # minimal interface checks
    assert hasattr(sess, 'execute')
    assert hasattr(sess, 'close') or hasattr(sess, 'remove')
    # closing should be safe
    try:
        if hasattr(sess, 'close'):
            sess.close()
        elif hasattr(db.SessionLocal, 'remove'):
            db.SessionLocal.remove()
    except Exception:
        # ensure closing doesn't raise in normal circumstances
        assert False, "Closing session raised an unexpected exception"

