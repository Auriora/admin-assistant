import os
import types

import pytest

from core.utilities import user_resolution as ur


def test_get_os_username_order(monkeypatch):
    # Ensure precedence USER > USERNAME > LOGNAME
    monkeypatch.delenv('USER', raising=False)
    monkeypatch.delenv('USERNAME', raising=False)
    monkeypatch.delenv('LOGNAME', raising=False)

    monkeypatch.setenv('LOGNAME', 'logname_user')
    assert ur.get_os_username() == 'logname_user'

    monkeypatch.setenv('USERNAME', 'win_user')
    assert ur.get_os_username() == 'win_user'

    monkeypatch.setenv('USER', 'unix_user')
    assert ur.get_os_username() == 'unix_user'


def test_resolve_user_identifier_precedence(monkeypatch):
    # CLI arg should win
    monkeypatch.setenv('ADMIN_ASSISTANT_USER', 'admin_env')
    monkeypatch.setenv('USER', 'os_user')
    assert ur.resolve_user_identifier(cli_user='cli') == 'cli'

    # ENV should be next
    assert ur.resolve_user_identifier(cli_user=None) == 'admin_env'

    # If no ADMIN env, use OS username
    monkeypatch.delenv('ADMIN_ASSISTANT_USER', raising=False)
    assert ur.resolve_user_identifier(cli_user=None) == 'os_user'

    # If nothing, return None
    monkeypatch.delenv('USER', raising=False)
    monkeypatch.delenv('USERNAME', raising=False)
    monkeypatch.delenv('LOGNAME', raising=False)
    assert ur.resolve_user_identifier(cli_user=None) is None


def test_get_user_identifier_source(monkeypatch):
    # CLI argument
    assert ur.get_user_identifier_source('foo') == 'command-line argument'

    # Admin env
    monkeypatch.setenv('ADMIN_ASSISTANT_USER', 'admin')
    assert 'ADMIN_ASSISTANT_USER' in ur.get_user_identifier_source(None)
    monkeypatch.delenv('ADMIN_ASSISTANT_USER', raising=False)

    # OS env
    monkeypatch.setenv('LOGNAME', 'log')
    src = ur.get_user_identifier_source(None)
    assert 'LOGNAME' in src or 'USER' in src or 'USERNAME' in src

    # No source
    monkeypatch.delenv('LOGNAME', raising=False)
    monkeypatch.delenv('USER', raising=False)
    monkeypatch.delenv('USERNAME', raising=False)
    assert ur.get_user_identifier_source(None) == 'no source found'


class DummyService:
    def __init__(self, by_id=None, by_username=None):
        self._by_id = by_id or {}
        self._by_username = by_username or {}
        self.closed = False

    def get_by_id(self, user_id):
        return self._by_id.get(user_id)

    def get_by_username(self, username):
        return self._by_username.get(username)

    def close(self):
        self.closed = True


def test_resolve_user_success_by_id_and_username():
    # Create dummy user objects
    user_obj = types.SimpleNamespace(id=1, username='alice')

    svc = DummyService(by_id={1: user_obj}, by_username={'alice': user_obj})

    # Resolve by numeric cli_user
    res = ur.resolve_user(cli_user=1, user_service=svc)
    assert res is user_obj

    # Resolve by username (string)
    svc2 = DummyService(by_id={}, by_username={'bob': types.SimpleNamespace(id=2, username='bob')})
    res2 = ur.resolve_user(cli_user='bob', user_service=svc2)
    assert res2.username == 'bob'


def test_resolve_user_not_found_raises(monkeypatch):
    # When identifier is present but no matching user, ValueError
    svc = DummyService(by_id={}, by_username={})
    with pytest.raises(ValueError):
        ur.resolve_user(cli_user='someone', user_service=svc)


def test_resolve_user_returns_none_when_no_identifier(monkeypatch):
    # Ensure no envs and no cli -> None
    monkeypatch.delenv('ADMIN_ASSISTANT_USER', raising=False)
    monkeypatch.delenv('USER', raising=False)
    monkeypatch.delenv('USERNAME', raising=False)
    monkeypatch.delenv('LOGNAME', raising=False)

    res = ur.resolve_user(cli_user=None, user_service=DummyService())
    assert res is None

