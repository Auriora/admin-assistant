from flask import Blueprint, render_template, redirect, request, session, url_for, flash
from app.services import msgraph
from app.models import db, User
from datetime import datetime, timedelta
from app.services.msgraph import MsAuthError
from flask import current_app
from flask_login import login_user, logout_user, login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    current_app.logger.debug('Rendering index page')
    return render_template('index.html')

@main_bp.route('/ms365/login')
def ms365_login():
    auth_url, state = msgraph.get_authorization_url()
    session['oauth_state'] = state
    current_app.logger.info(f"Initiating Microsoft 365 login, state={state}")
    return redirect(auth_url)

@main_bp.route('/ms365/auth/callback')
def ms365_auth_callback():
    if 'error' in request.args:
        current_app.logger.warning(f"Microsoft authentication failed: {request.args['error_description']}")
        flash('Microsoft authentication failed: ' + request.args['error_description'], 'danger')
        return redirect(url_for('main.index'))
    token = msgraph.fetch_token(request.url)
    user = User.query.first()
    if user:
        user.ms_access_token = token['access_token']
        user.ms_refresh_token = token.get('refresh_token')
        expires_in = token.get('expires_in', 3600)
        user.ms_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        db.session.commit()
        login_user(user)
        current_app.logger.info(f"Stored tokens for user {user.email}")
        flash('Microsoft 365 authentication successful and tokens stored securely!', 'success')
    else:
        current_app.logger.error('No user found to store tokens.')
        flash('No user found to store tokens.', 'danger')
    return redirect(url_for('main.index'))

@main_bp.route('/ms365/calendar')
@login_required
def ms365_calendar():
    user = current_user
    if not user or not user.ms_access_token:
        current_app.logger.warning('User not authenticated with Microsoft 365')
        flash('Please authenticate with Microsoft 365 first.', 'warning')
        return redirect(url_for('main.index'))
    try:
        session_obj = msgraph.get_authenticated_session_for_user(user)
        current_app.logger.info(f"User {user.email} accessed calendar successfully.")
        # Placeholder: fetch calendar events here using session_obj
        return 'Authenticated with Microsoft 365! Calendar access ready.'
    except MsAuthError as e:
        current_app.logger.error(f"MsAuthError: {str(e)}")
        flash(str(e), 'danger')
        return redirect(url_for('main.ms365_login'))
    except Exception as e:
        current_app.logger.exception(f"Authentication error: {str(e)}")
        flash(f'Authentication error: {str(e)}', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/login')
def login():
    return redirect(url_for('main.ms365_login'))

@main_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index')) 