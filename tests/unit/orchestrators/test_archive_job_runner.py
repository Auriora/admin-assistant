import pytest

from core.orchestrators.archive_job_runner import ArchiveJobRunner


class DummyUser:
    def __init__(self, id, email):
        self.id = id
        self.email = email


class DummyConfig:
    def __init__(self, source_calendar_uri="", destination_calendar_uri=""):
        self.source_calendar_uri = source_calendar_uri
        self.destination_calendar_uri = destination_calendar_uri


def test_run_archive_job_user_not_found(monkeypatch):
    runner = ArchiveJobRunner()
    # Make user lookup return None
    def _no_user(_: int) -> None:
        return None

    runner.user_service.get_by_id = _no_user

    res = runner.run_archive_job(user_id=1, archive_config_id=2)
    assert res.get("status") == "error"
    assert "No user found" in res.get("error")


def test_run_archive_job_config_not_found(monkeypatch):
    runner = ArchiveJobRunner()

    def _user(user_id: int) -> DummyUser:
        return DummyUser(user_id, "bob@example.com")

    def _no_archive_config(_: int):
        return None

    runner.user_service.get_by_id = _user
    runner.archive_config_service.get_by_id = _no_archive_config

    res = runner.run_archive_job(user_id=1, archive_config_id=2)
    assert res.get("status") == "error"
    assert "No archive configuration" in res.get("error")


def test_run_archive_job_no_token(monkeypatch):
    runner = ArchiveJobRunner()

    def _user_for_token(user_id: int) -> DummyUser:
        return DummyUser(user_id, "bob@example.com")

    def _config(_: int) -> DummyConfig:
        return DummyConfig("a", "b")

    runner.user_service.get_by_id = _user_for_token
    runner.archive_config_service.get_by_id = _config

    # Patch get_cached_access_token to return falsy
    monkeypatch.setattr("core.utilities.auth_utility.get_cached_access_token", lambda: None)

    res = runner.run_archive_job(user_id=1, archive_config_id=2)
    assert res.get("status") == "error"
    assert "No valid MS Graph token" in res.get("error")


def test_run_archive_job_success(monkeypatch):
    # Test successful routing to orchestrator with provided token and session
    runner = ArchiveJobRunner()
    user = DummyUser(5, "alice@example.com")
    cfg = DummyConfig("msgraph://calendars/primary", "msgraph://calendars/Archive")

    def _existing_user(_: int) -> DummyUser:
        return user

    def _existing_config(_: int) -> DummyConfig:
        return cfg

    runner.user_service.get_by_id = _existing_user
    runner.archive_config_service.get_by_id = _existing_config

    # Patch token and graph client
    monkeypatch.setattr("core.utilities.auth_utility.get_cached_access_token", lambda: "token123")
    monkeypatch.setattr("core.utilities.get_graph_client", lambda user, access_token: object())

    # Patch DB session
    monkeypatch.setattr("core.db.get_session", lambda: object())

    called = {}

    def fake_archive_user_appointments_with_config(**kwargs):
        called.update(kwargs)
        return {"status": "ok", "details": "archived"}

    # Replace orchestrator on runner instance
    runner.orchestrator.archive_user_appointments_with_config = fake_archive_user_appointments_with_config

    res = runner.run_archive_job(user_id=user.id, archive_config_id=123)
    assert res.get("status") == "ok"
    # Ensure orchestrator received expected keys
    assert "user" in called
    assert "msgraph_client" in called
    assert "archive_config" in called
    assert "db_session" in called
    assert called["archive_config"] == cfg


def test_run_archive_job_date_handling(monkeypatch):
    from datetime import date

    # If only start_date provided, end_date should be set to same day
    runner = ArchiveJobRunner()
    user = DummyUser(7, "joe@example.com")
    cfg = DummyConfig("msgraph://calendars/primary", "msgraph://calendars/Archive")
    def _date_user(_: int) -> DummyUser:
        return user

    def _date_config(_: int) -> DummyConfig:
        return cfg

    runner.user_service.get_by_id = _date_user
    runner.archive_config_service.get_by_id = _date_config
    monkeypatch.setattr("core.utilities.auth_utility.get_cached_access_token", lambda: "token123")
    monkeypatch.setattr("core.utilities.get_graph_client", lambda user, access_token: object())
    monkeypatch.setattr("core.db.get_session", lambda: object())

    called = {}

    def fake_archive_user_appointments_with_config(**kwargs):
        called.update(kwargs)
        return {"status": "ok"}

    runner.orchestrator.archive_user_appointments_with_config = fake_archive_user_appointments_with_config

    ref = date(2025, 10, 10)
    res = runner.run_archive_job(user_id=user.id, archive_config_id=1, start_date=ref)
    assert res.get("status") == "ok"
    assert "start_date" in called and "end_date" in called
    assert called["start_date"] == ref
    assert called["end_date"] == ref

    # If neither provided, the runner should set a 7-day window ending today
    called.clear()
    res = runner.run_archive_job(user_id=user.id, archive_config_id=1, start_date=None, end_date=None)
    assert res.get("status") == "ok"
    assert called["end_date"] is not None
    assert (called["end_date"] - called["start_date"]).days == 7
