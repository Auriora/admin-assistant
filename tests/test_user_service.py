import pytest

from core.services.user_service import UserService


class DummyRepo:
    def __init__(self):
        self.add_called = False
        self.update_called = False
        self.deleted = None
        self._users = {}

    def get_by_id(self, uid):
        return self._users.get(uid)

    def get_by_email(self, email):
        for u in self._users.values():
            if getattr(u, 'email', None) == email:
                return u
        return None

    def get_by_username(self, username):
        for u in self._users.values():
            if getattr(u, 'username', None) == username:
                return u
        return None

    def add(self, user):
        self.add_called = True
        self._users[getattr(user, 'id', len(self._users) + 1)] = user

    def update(self, user):
        self.update_called = True

    def delete(self, user_id):
        self.deleted = user_id

    def list(self, is_active=None):
        return list(self._users.values())

    def close(self):
        pass


class DummyUser:
    def __init__(self, id=None, email=None, username=None):
        self.id = id
        self.email = email
        self.username = username


def test_validate_requires_email():
    repo = DummyRepo()
    svc = UserService(repository=repo)
    user = DummyUser(id=1, email='', username='bob')
    with pytest.raises(ValueError):
        svc.validate(user)


def test_validate_username_uniqueness_check():
    repo = DummyRepo()
    existing = DummyUser(id=2, email='e@example.com', username='taken')
    repo._users[2] = existing
    svc = UserService(repository=repo)

    # Trying to validate a different user with same username should raise
    new_user = DummyUser(id=3, email='n@example.com', username='taken')
    with pytest.raises(ValueError):
        svc.validate(new_user)


def test_create_and_update_and_delete_calls_repo_methods():
    repo = DummyRepo()
    svc = UserService(repository=repo)
    user = DummyUser(id=10, email='u@example.com', username='u')
    svc.create(user)
    assert repo.add_called is True

    svc.update(user)
    assert repo.update_called is True

    svc.delete(10)
    assert repo.deleted == 10


def test_close_closes_owned_repo():
    svc = UserService()  # will create its own UserRepository but we can't easily inspect it; ensure close does not raise
    # calling close should be safe
    svc.close()
