from flask import Blueprint, render_template, redirect, request, session, url_for, flash, jsonify
from app.services import msgraph
from app.models import db, User
from datetime import datetime, timedelta
from app.services.msgraph import MsAuthError
from flask import current_app
from flask_login import login_user, logout_user, login_required, current_user
import requests
from app.services.calendar_service import CalendarService
from typing import cast

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    current_app.logger.debug('Rendering dashboard page')
    return render_template('home/dashboard.html', user=current_user)

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
    access_token = token['access_token']
    # Fetch user profile from Microsoft Graph
    headers = {'Authorization': f'Bearer {access_token}'}
    profile_resp = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
    if profile_resp.status_code != 200:
        current_app.logger.error('Failed to fetch user profile from Microsoft Graph.')
        flash('Failed to fetch user profile from Microsoft Graph.', 'danger')
        return redirect(url_for('main.index'))
    profile = profile_resp.json()
    email = profile.get('mail') or profile.get('userPrincipalName')
    name = profile.get('displayName', '')
    if not email:
        current_app.logger.error('No email found in Microsoft profile.')
        flash('No email found in Microsoft profile.', 'danger')
        return redirect(url_for('main.index'))
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, name=name) # type: ignore
        db.session.add(user)
        db.session.commit()
        current_app.logger.info(f"Created new user {email} from Microsoft login.")
    user.ms_access_token = token['access_token']
    user.ms_refresh_token = token.get('refresh_token')
    expires_in = token.get('expires_in', 3600)
    user.ms_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    # Fetch and store profile photo
    photo_url = None
    try:
        photo_resp = requests.get('https://graph.microsoft.com/v1.0/me/photo/$value', headers=headers)
        if photo_resp.status_code == 200:
            photo_path = f'static/assets/img/team/profile-photo-{user.id}.jpg'
            with open(photo_path, 'wb') as f:
                f.write(photo_resp.content)
            user.profile_photo_url = photo_path.replace('static/', '')
            photo_url = user.profile_photo_url
        else:
            user.profile_photo_url = None
    except Exception as e:
        current_app.logger.warning(f"Could not fetch profile photo: {e}")
        user.profile_photo_url = None
    db.session.commit()
    login_user(user)
    current_app.logger.info(f"Stored tokens for user {user.email}")
    flash('Microsoft 365 authentication successful and tokens stored securely!', 'success')
    return redirect(url_for('main.index'))

@main_bp.route('/ms365/calendar')
@login_required
def ms365_calendar():
    user = cast(User, current_user)
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

@main_bp.route('/archive/now', methods=['POST'])
@login_required
def archive_now():
    """
    Trigger manual archive for the current user. Returns JSON status for UI notification updates.
    """
    user = cast(User, current_user)
    current_app.logger.info(f"Manual archive started by {user.email}")  # type: ignore[attr-defined]
    # Notify UI: archive started
    try:
        today = datetime.utcnow().date()
        appointments = CalendarService.fetch_appointments_from_ms365(user, today)
        result = CalendarService.archive_appointments(user, appointments)
        if result["errors"]:
            current_app.logger.error(f"Manual archive errors: {result['errors']}")
            return jsonify({"status": "error", "message": "Archive failed.", "details": result["errors"]}), 500
        else:
            current_app.logger.info(f"Manual archive completed for {user.email}")  # type: ignore[attr-defined]
            return jsonify({"status": "success", "message": "Archive complete!"})
    except Exception as e:
        current_app.logger.exception(f"Manual archive exception: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500 