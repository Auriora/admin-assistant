import os
import requests
from flask import current_app, url_for, session
from requests_oauthlib import OAuth2Session
from app.models import db, User
from datetime import datetime, timedelta

# Scopes required for calendar access
MS_SCOPES = ['Calendars.ReadWrite', 'offline_access', 'User.Read']

class MsAuthError(Exception):
    pass

try:
    from opentelemetry import trace
    tracer = trace.get_tracer(__name__)
except ImportError:
    tracer = None

def get_ms_oauth_session(state=None, token=None):
    if tracer:
        with tracer.start_as_current_span("msgraph.get_ms_oauth_session"):
            return _get_ms_oauth_session_impl(state, token)
    return _get_ms_oauth_session_impl(state, token)

def _get_ms_oauth_session_impl(state=None, token=None):
    client_id = current_app.config['MS_CLIENT_ID']
    client_secret = current_app.config['MS_CLIENT_SECRET']
    redirect_uri = current_app.config['MS_REDIRECT_URI']
    tenant_id = current_app.config['MS_TENANT_ID']
    auth_base = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0'
    current_app.logger.debug(f"Creating OAuth2Session for tenant {tenant_id}")
    return OAuth2Session(
        client_id,
        redirect_uri=redirect_uri,
        scope=MS_SCOPES,
        state=state,
        token=token
    ), auth_base

def get_authorization_url():
    if tracer:
        with tracer.start_as_current_span("msgraph.get_authorization_url"):
            return _get_authorization_url_impl()
    return _get_authorization_url_impl()

def _get_authorization_url_impl():
    oauth, auth_base = get_ms_oauth_session()
    authorization_url, state = oauth.authorization_url(f'{auth_base}/authorize')
    current_app.logger.info(f"Generated Microsoft authorization URL: {authorization_url}")
    return authorization_url, state

def fetch_token(authorization_response):
    if tracer:
        with tracer.start_as_current_span("msgraph.fetch_token"):
            return _fetch_token_impl(authorization_response)
    return _fetch_token_impl(authorization_response)

def _fetch_token_impl(authorization_response):
    oauth, auth_base = get_ms_oauth_session(state=session.get('oauth_state'))
    token = oauth.fetch_token(
        f'{auth_base}/token',
        authorization_response=authorization_response,
        client_secret=current_app.config['MS_CLIENT_SECRET']
    )
    current_app.logger.info("Fetched Microsoft OAuth token.")
    return token

def is_token_expired(user):
    if tracer:
        with tracer.start_as_current_span("msgraph.is_token_expired") as span:
            if user and hasattr(user, 'email'):
                span.set_attribute("user.email", getattr(user, 'email', ''))
            return _is_token_expired_impl(user)
    return _is_token_expired_impl(user)

def _is_token_expired_impl(user):
    if not user.ms_token_expires_at:
        current_app.logger.debug("User token has no expiry; treating as expired.")
        return True
    expired = user.ms_token_expires_at <= datetime.utcnow()
    if expired:
        current_app.logger.info(f"Token for user {user.email} is expired.")
    return expired

def refresh_token(user):
    if tracer:
        with tracer.start_as_current_span("msgraph.refresh_token") as span:
            if user and hasattr(user, 'email'):
                span.set_attribute("user.email", getattr(user, 'email', ''))
            return _refresh_token_impl(user)
    return _refresh_token_impl(user)

def _refresh_token_impl(user):
    client_id = current_app.config['MS_CLIENT_ID']
    client_secret = current_app.config['MS_CLIENT_SECRET']
    tenant_id = current_app.config['MS_TENANT_ID']
    auth_base = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0'
    token_url = f'{auth_base}/token'
    refresh_data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': user.ms_refresh_token,
        'scope': ' '.join(MS_SCOPES),
    }
    resp = requests.post(token_url, data=refresh_data)
    if resp.status_code == 200:
        token = resp.json()
        user.ms_access_token = token['access_token']
        user.ms_refresh_token = token.get('refresh_token', user.ms_refresh_token)
        expires_in = token.get('expires_in', 3600)
        user.ms_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        db.session.commit()
        current_app.logger.info(f"Refreshed token for user {user.email}")
        return token['access_token']
    else:
        # Clear tokens and require re-authentication
        user.ms_access_token = None
        user.ms_refresh_token = None
        user.ms_token_expires_at = None
        db.session.commit()
        current_app.logger.error(f"Failed to refresh token for user {user.email}: {resp.text}")
        raise MsAuthError('Microsoft 365 authentication expired or revoked. Please re-authenticate.')

def get_authenticated_session_for_user(user):
    if tracer:
        with tracer.start_as_current_span("msgraph.get_authenticated_session_for_user") as span:
            if user and hasattr(user, 'email'):
                span.set_attribute("user.email", getattr(user, 'email', ''))
            return _get_authenticated_session_for_user_impl(user)
    return _get_authenticated_session_for_user_impl(user)

def _get_authenticated_session_for_user_impl(user):
    if is_token_expired(user):
        current_app.logger.info(f"Refreshing expired token for user {user.email}")
        refresh_token(user)
    session_obj = requests.Session()
    session_obj.headers.update({'Authorization': f"Bearer {user.ms_access_token}"})
    current_app.logger.debug(f"Created authenticated session for user {user.email}")
    return session_obj 