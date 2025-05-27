from flask import Blueprint, render_template, redirect, request, session, url_for, flash, jsonify
from app.services import msgraph
from app.models import db, User, Notification, NotificationPreference, NotificationClass
from datetime import datetime, timedelta, UTC
from app.services.msgraph import MsAuthError
from flask import current_app
from flask_login import login_user, logout_user, login_required, current_user
import requests
from core.services.calendar_fetch_service import fetch_appointments_from_ms365
from core.services.calendar_archive_service import archive_appointments
from typing import cast
from flask import abort
from sqlalchemy import desc

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
    user.ms_token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
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

def get_user_notification_channel(user_id, notification_class):
    pref = NotificationPreference.query.filter_by(user_id=user_id, notification_class=notification_class).first()
    if pref:
        return pref.channel
    # Default logic: can be 'toast', 'email', 'both', or 'none'
    return 'toast'

@main_bp.route('/archive/now', methods=['POST'])
@login_required
def archive_now():
    """
    Trigger manual archive for the current user. Accepts optional start_date and end_date in the request (defaults to today).
    Returns JSON status for UI notification updates.
    """
    user = cast(User, current_user)
    current_app.logger.info(f"Manual archive started by {user.email}")  # type: ignore[attr-defined]
    try:
        data = request.get_json(silent=True) or {}
        today = datetime.now(UTC).date()
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else today
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else today
        msgraph_session = msgraph.get_authenticated_session_for_user(user)
        appointments = fetch_appointments_from_ms365(user, start_date, end_date, msgraph_session, logger=current_app.logger)
        result = archive_appointments(user, appointments, start_date, end_date, db.session, logger=current_app.logger)
        channel = get_user_notification_channel(user.id, 'account_activity')
        notif = Notification(
            user_id=user.id,
            message='Archive process started.',
            type='archive',
            channel=channel,
            state='in-progress',
            pct_complete=0,
            progress='Starting archive...'
        )
        db.session.add(notif)
        db.session.commit()
        if result.get("status") == "overlap":
            current_app.logger.warning(f"Manual archive found overlaps: {result['conflicts']}")
            return jsonify({"status": "overlap", "conflicts": result["conflicts"]}), 409
        if result["errors"]:
            current_app.logger.error(f"Manual archive errors: {result['errors']}")
            return jsonify({"status": "error", "message": "Archive failed.", "details": result["errors"]}), 500
        else:
            current_app.logger.info(f"Manual archive completed for {user.email}")  # type: ignore[attr-defined]
            return jsonify({"status": "success", "message": "Archive complete!"})
    except Exception as e:
        current_app.logger.exception(f"Manual archive exception: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main_bp.route('/notifications')
@login_required
def get_notifications():
    """
    Return the current user's notifications as JSON, ordered by created_at descending.
    """
    user = cast(User, current_user)
    notifications = Notification.query.filter_by(user_id=user.id).order_by(desc(getattr(Notification, 'created_at'))).all()
    return jsonify([
        {
            'id': n.id,
            'message': n.message,
            'type': n.type,
            'channel': n.channel,
            'transaction_id': n.transaction_id,
            'pct_complete': n.pct_complete,
            'progress': n.progress,
            'state': n.state,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
        }
        for n in notifications
    ])

@main_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    user = cast(User, current_user)
    notification = Notification.query.filter_by(id=notification_id, user_id=user.id).first()
    if not notification:
        return jsonify({'success': False, 'error': 'Notification not found'}), 404
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@main_bp.route('/notification-preferences', methods=['GET'])
@login_required
def get_notification_preferences():
    user = cast(User, current_user)
    prefs = NotificationPreference.query.filter_by(user_id=user.id).all()
    return jsonify([
        {
            'id': p.id,
            'notification_class': p.notification_class,
            'channel': p.channel
        }
        for p in prefs
    ])

@main_bp.route('/admin/notification-classes', methods=['GET'])
@login_required
def list_notification_classes():
    classes = NotificationClass.query.all()
    return jsonify([
        {'id': c.id, 'key': c.key, 'label': c.label, 'description': c.description}
        for c in classes
    ])

@main_bp.route('/admin/notification-classes', methods=['POST'])
@login_required
def create_notification_class():
    data = request.get_json()
    key = data.get('key')
    label = data.get('label')
    description = data.get('description')
    if not key or not label:
        return jsonify({'success': False, 'error': 'Missing key or label'}), 400
    if NotificationClass.query.filter_by(key=key).first():
        return jsonify({'success': False, 'error': 'Key already exists'}), 400
    nc = NotificationClass(key=key, label=label, description=description)
    db.session.add(nc)
    db.session.commit()
    return jsonify({'success': True, 'id': nc.id, 'key': nc.key, 'label': nc.label, 'description': nc.description})

@main_bp.route('/admin/notification-classes/<int:class_id>', methods=['PUT'])
@login_required
def update_notification_class(class_id):
    nc = NotificationClass.query.get_or_404(class_id)
    data = request.get_json()
    nc.label = data.get('label', nc.label)
    nc.description = data.get('description', nc.description)
    db.session.commit()
    return jsonify({'success': True, 'id': nc.id, 'key': nc.key, 'label': nc.label, 'description': nc.description})

@main_bp.route('/admin/notification-classes/<int:class_id>', methods=['DELETE'])
@login_required
def delete_notification_class(class_id):
    nc = NotificationClass.query.get_or_404(class_id)
    db.session.delete(nc)
    db.session.commit()
    return jsonify({'success': True})

@main_bp.route('/notification-preferences', methods=['POST'])
@login_required
def set_notification_preference():
    user = cast(User, current_user)
    data = request.get_json()
    notification_class = data.get('notification_class')
    channel = data.get('channel')
    if not notification_class or not channel:
        return jsonify({'success': False, 'error': 'Missing notification_class or channel'}), 400
    # Backend validation for allowed notification classes
    if not NotificationClass.query.filter_by(key=notification_class).first():
        return jsonify({'success': False, 'error': 'Invalid notification_class'}), 400
    pref = NotificationPreference.query.filter_by(user_id=user.id, notification_class=notification_class).first()
    if pref:
        pref.channel = channel
    else:
        pref = NotificationPreference(user_id=user.id, notification_class=notification_class, channel=channel)
        db.session.add(pref)
    db.session.commit()
    return jsonify({'success': True, 'id': pref.id, 'notification_class': pref.notification_class, 'channel': pref.channel})

@main_bp.route('/settings')
@login_required
def settings():
    return render_template('home/settings.html', user=current_user) 