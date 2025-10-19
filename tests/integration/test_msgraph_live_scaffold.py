"""
MS Graph live test scaffold.

This test is marked as both integration and msgraph. It is SKIPPED by default unless
MSGRAPH_E2E_ENABLED=true and required credentials are provided via environment variables.

Expected environment variables when enabled (set via CI secrets or locally):
- MSGRAPH_E2E_ENABLED=true
- AZURE_TENANT_ID
- AZURE_CLIENT_ID
- AZURE_CLIENT_SECRET
- TEST_USER_EMAIL (email of the user context for client creation if needed)

When enabled, this test exercises the minimal happy path to obtain a token and
optionally instantiate a Graph client using project utilities.
"""
import os
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.msgraph]


def _env(var: str) -> str | None:
    val = os.environ.get(var)
    return val if val and val.strip() else None


def _should_run() -> tuple[bool, str | None]:
    if _env("MSGRAPH_E2E_ENABLED") != "true":
        return False, "MSGRAPH_E2E_ENABLED is not 'true'"
    missing = [
        name for name in [
            "AZURE_TENANT_ID",
            "AZURE_CLIENT_ID",
            "AZURE_CLIENT_SECRET",
        ]
        if not _env(name)
    ]
    if missing:
        return False, f"Missing required env vars: {', '.join(missing)}"
    return True, None


def _resolve_graph_client_func():
    """Resolve a get_graph_client callable from available utilities, or return None."""
    try:
        from core.utilities import get_graph_client as fn  # type: ignore
        return fn
    except Exception:
        pass
    try:
        from core.utilities.graph_utility import get_graph_client as fn  # type: ignore
        return fn
    except Exception:
        return None


def test_can_initialize_msgraph_auth_and_client_when_enabled():
    ok, reason = _should_run()
    if not ok:
        pytest.skip(f"Skipping MS Graph live test: {reason}")

    # Try to obtain an access token using project utilities if available
    try:
        from core.utilities import auth_utility
    except Exception as e:
        pytest.skip(f"auth_utility not available: {e}")

    token = auth_utility.get_cached_access_token()
    assert token and isinstance(token, str) and len(token) > 0

    # Resolve a Graph client factory function
    get_graph_client_fn = _resolve_graph_client_func()
    if get_graph_client_fn is None:
        pytest.skip("Graph client utility not available")

    # Build a minimal user stub if required by get_graph_client signature
    class _User:
        def __init__(self, email: str):
            self.email = email

    user_email = _env("TEST_USER_EMAIL") or ""
    user = _User(user_email) if user_email else None

    client = None
    try:
        client = get_graph_client_fn(user, token)  # type: ignore[arg-type]
    except TypeError:
        # Some variants: get_graph_client(access_token)
        client = get_graph_client_fn(token)  # type: ignore[call-arg]

    assert client is not None

