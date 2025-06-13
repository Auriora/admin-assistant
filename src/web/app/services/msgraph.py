import os
from datetime import UTC, datetime, timedelta

import msal
import requests
from flask import current_app, session, url_for

# Scopes required for calendar access
MS_SCOPES = ["Calendars.ReadWrite", "User.Read"]


class MsAuthError(Exception):
    pass


try:
    from opentelemetry import trace

    tracer = trace.get_tracer(__name__)
except ImportError:
    tracer = None


def get_msal_app():
    client_id = current_app.config["MS_CLIENT_ID"]
    client_secret = current_app.config["MS_CLIENT_SECRET"]
    authority = (
        f"https://login.microsoftonline.com/{current_app.config['MS_TENANT_ID']}"
    )
    return msal.ConfidentialClientApplication(
        client_id, authority=authority, client_credential=client_secret
    )


def get_authorization_url():
    msal_app = get_msal_app()
    redirect_uri = current_app.config["MS_REDIRECT_URI"]
    current_app.logger.debug(f"redirect_uri in get_authorization_url: {redirect_uri}")
    scopes = MS_SCOPES
    state = os.urandom(16).hex()
    auth_url = msal_app.get_authorization_request_url(
        scopes, state=state, redirect_uri=redirect_uri
    )
    current_app.logger.debug(
        f"[MSAL] Using tenant_id: {current_app.config['MS_TENANT_ID']}"
    )
    current_app.logger.info(f"[MSAL] Generated Microsoft authorization URL: {auth_url}")
    current_app.logger.debug(f"[MSAL] Full authorization URL: {auth_url}")
    return auth_url, state


def fetch_token(authorization_response):
    msal_app = get_msal_app()
    redirect_uri = current_app.config["MS_REDIRECT_URI"]
    current_app.logger.debug(f"redirect_uri in fetch_token: {redirect_uri}")
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(authorization_response)
    code = parse_qs(parsed.query).get("code", [None])[0]
    if not code:
        raise MsAuthError("No authorization code found in callback URL.")
    scopes = MS_SCOPES
    result = msal_app.acquire_token_by_authorization_code(
        code, scopes=scopes, redirect_uri=redirect_uri
    )
    if "access_token" in result:
        current_app.logger.info("[MSAL] Fetched Microsoft OAuth token.")
        return result
    else:
        current_app.logger.error(f"[MSAL] Token acquisition failed: {result}")
        raise MsAuthError(
            "Microsoft 365 authentication failed. "
            + str(result.get("error_description", ""))
        )


def is_token_expired(user):
    if tracer:
        with tracer.start_as_current_span("msgraph.is_token_expired") as span:
            if user and hasattr(user, "email"):
                span.set_attribute("user.email", getattr(user, "email", ""))
            return _is_token_expired_impl(user)
    return _is_token_expired_impl(user)


def _is_token_expired_impl(user):
    if not user.ms_token_expires_at:
        current_app.logger.debug("User token has no expiry; treating as expired.")
        return True
    expires_at = user.ms_token_expires_at
    if expires_at.tzinfo is None:
        # Assume UTC if naive
        expires_at = expires_at.replace(tzinfo=UTC)
    expired = expires_at <= datetime.now(UTC)
    if expired:
        current_app.logger.info(f"Token for user {user.email} is expired.")
    return expired


def refresh_token(user):
    if tracer:
        with tracer.start_as_current_span("msgraph.refresh_token") as span:
            if user and hasattr(user, "email"):
                span.set_attribute("user.email", getattr(user, "email", ""))
            return _refresh_token_impl(user)
    return _refresh_token_impl(user)


def _refresh_token_impl(user):
    # Import db here to avoid circular import
    from app.models import db

    client_id = current_app.config["MS_CLIENT_ID"]
    client_secret = current_app.config["MS_CLIENT_SECRET"]
    tenant_id = current_app.config["MS_TENANT_ID"]
    auth_base = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0"
    token_url = f"{auth_base}/token"
    refresh_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": user.ms_refresh_token,
        "scope": " ".join(MS_SCOPES),
    }
    resp = requests.post(token_url, data=refresh_data)
    if resp.status_code == 200:
        token = resp.json()
        user.ms_access_token = token["access_token"]
        user.ms_refresh_token = token.get("refresh_token", user.ms_refresh_token)
        expires_in = token.get("expires_in", 3600)
        user.ms_token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
        db.session.commit()
        current_app.logger.info(f"Refreshed token for user {user.email}")
        return token["access_token"]
    else:
        # Clear tokens and require re-authentication
        user.ms_access_token = None
        user.ms_refresh_token = None
        user.ms_token_expires_at = None
        db.session.commit()
        current_app.logger.error(
            f"Failed to refresh token for user {user.email}: {resp.text}"
        )
        raise MsAuthError(
            "Microsoft 365 authentication expired or revoked. Please re-authenticate."
        )


def get_authenticated_session_for_user(user):
    if tracer:
        with tracer.start_as_current_span(
            "msgraph.get_authenticated_session_for_user"
        ) as span:
            if user and hasattr(user, "email"):
                span.set_attribute("user.email", getattr(user, "email", ""))
            return _get_authenticated_session_for_user_impl(user)
    return _get_authenticated_session_for_user_impl(user)


def _get_authenticated_session_for_user_impl(user):
    if is_token_expired(user):
        current_app.logger.info(f"Refreshing expired token for user {user.email}")
        refresh_token(user)
    session_obj = requests.Session()
    session_obj.headers.update({"Authorization": f"Bearer {user.ms_access_token}"})
    current_app.logger.debug(f"Created authenticated session for user {user.email}")
    return session_obj
