import os
import stat

import core.utilities.auth_utility as auth


def test_ensure_secure_cache_dir(tmp_path, monkeypatch):
    # Point CACHE_DIR to a temporary directory
    tmp_cache = tmp_path / "cachedir"
    monkeypatch.setattr(auth, 'CACHE_DIR', str(tmp_cache))

    # Remove if exists
    if tmp_cache.exists():
        for p in tmp_cache.iterdir():
            p.unlink()
        tmp_cache.rmdir()

    auth.ensure_secure_cache_dir()
    assert tmp_cache.exists()
    mode = os.stat(str(tmp_cache)).st_mode
    # Check owner-only permissions (0700)
    assert (mode & 0o777) == 0o700


class FakeApp:
    def __init__(self, token=None):
        self._token = token

    def get_accounts(self):
        return ["acct"] if self._token else []

    def acquire_token_silent(self, scopes, account=None):
        if self._token:
            return {"access_token": self._token}
        return None


def test_get_cached_access_token_returns_token(monkeypatch):
    fake_app = FakeApp(token="tok123")
    fake_cache = object()

    monkeypatch.setattr(auth, 'get_msal_app', lambda: (fake_app, fake_cache))

    token = auth.get_cached_access_token()
    assert token == "tok123"


def test_get_cached_access_token_none_when_no_accounts(monkeypatch):
    fake_app = FakeApp(token=None)
    fake_cache = object()
    monkeypatch.setattr(auth, 'get_msal_app', lambda: (fake_app, fake_cache))

    token = auth.get_cached_access_token()
    assert token is None

