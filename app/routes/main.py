from flask import Blueprint, render_template, redirect, request, session, url_for, flash
from app.services import msgraph
from app.models import db, User
from datetime import datetime, timedelta
from app.services.msgraph import MsAuthError

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/ms365/login')
def ms365_login():
    auth_url, state = msgraph.get_authorization_url()
    session['oauth_state'] = state
    return redirect(auth_url)

@main_bp.route('/ms365/auth/callback')
def ms365_auth_callback():
    if 'error' in request.args:
        flash('Microsoft authentication failed: ' + request.args['error_description'], 'danger')
        return redirect(url_for('main.index'))
    token = msgraph.fetch_token(request.url)
    # Store tokens in the database for the single user
    user = User.query.first()
    if user:
        user.ms_access_token = token['access_token']
        user.ms_refresh_token = token.get('refresh_token')
        expires_in = token.get('expires_in', 3600)
        user.ms_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        db.session.commit()
        flash('Microsoft 365 authentication successful and tokens stored securely!', 'success')
    else:
        flash('No user found to store tokens.', 'danger')
    return redirect(url_for('main.index'))

@main_bp.route('/ms365/calendar')
def ms365_calendar():
    user = User.query.first()
    if not user or not user.ms_access_token:
        flash('Please authenticate with Microsoft 365 first.', 'warning')
        return redirect(url_for('main.index'))
    try:
        session_obj = msgraph.get_authenticated_session_for_user(user)
        # Placeholder: fetch calendar events here using session_obj
        return 'Authenticated with Microsoft 365! Calendar access ready.'
    except MsAuthError as e:
        flash(str(e), 'danger')
        return redirect(url_for('main.ms365_login'))
    except Exception as e:
        flash(f'Authentication error: {str(e)}', 'danger')
        return redirect(url_for('main.index')) 