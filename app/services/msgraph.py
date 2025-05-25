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

def get_ms_oauth_session(state=None, token=None):
    client_id = current_app.config['MS_CLIENT_ID']
    client_secret = current_app.config['MS_CLIENT_SECRET']
    redirect_uri = current_app.config['MS_REDIRECT_URI']
    tenant_id = current_app.config['MS_TENANT_ID']
    auth_base = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0'
    return OAuth2Session(
        client_id,
        redirect_uri=redirect_uri,
        scope=MS_SCOPES,
        state=state,
        token=token
    ), auth_base

def get_authorization_url():
    oauth, auth_base = get_ms_oauth_session()
    authorization_url, state = oauth.authorization_url(f'{auth_base}/authorize')
    return authorization_url, state

def fetch_token(authorization_response):
    oauth, auth_base = get_ms_oauth_session(state=session.get('oauth_state'))
    token = oauth.fetch_token(
        f'{auth_base}/token',
        authorization_response=authorization_response,
        client_secret=current_app.config['MS_CLIENT_SECRET']
    )
    return token

def is_token_expired(user):
    if not user.ms_token_expires_at:
        return True
    return user.ms_token_expires_at <= datetime.utcnow()

def refresh_token(user):
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
        return token['access_token']
    else:
        # Clear tokens and require re-authentication
        user.ms_access_token = None
        user.ms_refresh_token = None
        user.ms_token_expires_at = None
        db.session.commit()
        raise MsAuthError('Microsoft 365 authentication expired or revoked. Please re-authenticate.')

def get_authenticated_session_for_user(user):
    if is_token_expired(user):
        refresh_token(user)
    session_obj = requests.Session()
    session_obj.headers.update({'Authorization': f"Bearer {user.ms_access_token}"})
    return session_obj 