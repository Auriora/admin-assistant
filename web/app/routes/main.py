from flask import Blueprint, render_template, redirect, request, session, url_for, flash, jsonify
from web.app.services import msgraph
from web.app.models import db, User
from datetime import datetime, timedelta, UTC, date
from web.app.services.msgraph import MsAuthError
from flask import current_app
from flask_login import login_user, logout_user, login_required, current_user
import requests
from core.services.calendar_io_service import fetch_appointments
from core.orchestrators.calendar_archive_orchestrator import CalendarArchiveOrchestrator
from core.services.archive_configuration_service import ArchiveConfigurationService
from typing import cast
from flask import abort
from sqlalchemy import desc
from sqlalchemy.orm import Session as SQLAlchemySession

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
    # Fetch and store profile photo securely
    photo_url = None
    try:
        photo_resp = requests.get('https://graph.microsoft.com/v1.0/me/photo/$value', headers=headers)
        if photo_resp.status_code == 200:
            # Validate content type
            content_type = photo_resp.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                current_app.logger.warning(f"Invalid content type for profile photo: {content_type}")
                user.profile_photo_url = None
            else:
                # Validate file size (max 5MB)
                content_length = len(photo_resp.content)
                if content_length > 5 * 1024 * 1024:
                    current_app.logger.warning(f"Profile photo too large: {content_length} bytes")
                    user.profile_photo_url = None
                else:
                    # Secure file path construction
                    import os
                    import uuid

                    # Generate secure filename
                    file_extension = '.jpg'  # Default to jpg for MS Graph photos
                    secure_filename = f'profile-{user.id}-{uuid.uuid4().hex[:8]}{file_extension}'

                    # Ensure directory exists and is secure
                    photo_dir = os.path.join(current_app.static_folder, 'assets', 'img', 'team')
                    os.makedirs(photo_dir, mode=0o755, exist_ok=True)

                    # Construct secure file path
                    photo_path = os.path.join(photo_dir, secure_filename)

                    # Write file securely
                    with open(photo_path, 'wb') as f:
                        f.write(photo_resp.content)

                    # Set secure file permissions
                    os.chmod(photo_path, 0o644)

                    # Store relative URL
                    user.profile_photo_url = f'assets/img/team/{secure_filename}'
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
        # Fetch archive configuration for the user
        archive_config_service = ArchiveConfigurationService()
        archive_config = archive_config_service.get_active_for_user(user.id)
        if not archive_config:
            return jsonify({"status": "error", "message": "No active archive configuration found for user."}), 400
        # Access the actual values, not the Column objects
        source_calendar_uri = getattr(archive_config, 'source_calendar_uri', None)
        archive_calendar_uri = getattr(archive_config, 'destination_calendar_uri', None)
        if not source_calendar_uri or not archive_calendar_uri:
            return jsonify({"status": "error", "message": "Archive configuration is missing calendar IDs."}), 400
        appointments = fetch_appointments(user, start_date, end_date, msgraph_session, logger=current_app.logger)
        result = CalendarArchiveOrchestrator().archive_user_appointments(
            user=user,
            msgraph_client=msgraph_session,
            source_calendar_uri=source_calendar_uri,
            archive_calendar_id=archive_calendar_uri,
            start_date=start_date,
            end_date=end_date,
            db_session=cast(SQLAlchemySession, db.session),
            logger=current_app.logger
        )
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

@main_bp.route('/settings')
@login_required
def settings():
    return render_template('home/settings.html', user=current_user)


# --- Background Job Management Routes ---

@main_bp.route('/jobs/schedule', methods=['POST'])
@login_required
def schedule_archive_job():
    """
    Schedule a recurring archive job for the current user.
    Accepts JSON with schedule_type, hour, minute, day_of_week, archive_config_id.
    """
    user = cast(User, current_user)
    current_app.logger.info(f"Schedule archive job requested by {user.email}")

    try:
        data = request.get_json() or {}
        schedule_type = data.get('schedule_type', 'daily')
        hour = int(data.get('hour', 23))
        minute = int(data.get('minute', 59))
        day_of_week = data.get('day_of_week')
        archive_config_id = data.get('archive_config_id')

        # Validate parameters
        if schedule_type not in ['daily', 'weekly']:
            return jsonify({"status": "error", "message": "Invalid schedule_type. Must be 'daily' or 'weekly'."}), 400

        if not (0 <= hour <= 23):
            return jsonify({"status": "error", "message": "Hour must be between 0 and 23."}), 400

        if not (0 <= minute <= 59):
            return jsonify({"status": "error", "message": "Minute must be between 0 and 59."}), 400

        if schedule_type == 'weekly' and day_of_week is not None:
            day_of_week = int(day_of_week)
            if not (0 <= day_of_week <= 6):
                return jsonify({"status": "error", "message": "Day of week must be between 0 (Monday) and 6 (Sunday)."}), 400

        # Get archive configuration
        if archive_config_id:
            archive_config_service = ArchiveConfigurationService()
            archive_config = archive_config_service.get_by_id(int(archive_config_id))
            if not archive_config or archive_config.user_id != user.id:
                return jsonify({"status": "error", "message": "Archive configuration not found or not owned by user."}), 400
        else:
            # Use active configuration
            archive_config_service = ArchiveConfigurationService()
            archive_config = archive_config_service.get_active_for_user(user.id)
            if not archive_config:
                return jsonify({"status": "error", "message": "No active archive configuration found for user."}), 400
            archive_config_id = archive_config.id

        # Schedule the job
        scheduled_archive_service = current_app.scheduled_archive_service
        if schedule_type == 'daily':
            result = scheduled_archive_service.update_user_schedule(
                user_id=user.id,
                schedule_type='daily',
                hour=hour,
                minute=minute
            )
        else:  # weekly
            result = scheduled_archive_service.update_user_schedule(
                user_id=user.id,
                schedule_type='weekly',
                hour=hour,
                minute=minute,
                day_of_week=day_of_week
            )

        if result['failed_jobs']:
            return jsonify({
                "status": "partial_success",
                "message": "Some jobs failed to schedule.",
                "updated_jobs": result['updated_jobs'],
                "failed_jobs": result['failed_jobs']
            }), 207
        else:
            return jsonify({
                "status": "success",
                "message": f"Archive job scheduled successfully ({schedule_type}).",
                "updated_jobs": result['updated_jobs']
            })

    except Exception as e:
        current_app.logger.exception(f"Schedule archive job exception: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@main_bp.route('/jobs/trigger', methods=['POST'])
@login_required
def trigger_manual_archive_job():
    """
    Trigger a manual archive job for the current user.
    Accepts JSON with optional start_date, end_date, archive_config_id.
    """
    user = cast(User, current_user)
    current_app.logger.info(f"Manual archive job trigger requested by {user.email}")

    try:
        data = request.get_json() or {}
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        archive_config_id = data.get('archive_config_id')

        # Parse dates
        start_date = None
        end_date = None
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        # Get archive configuration
        if archive_config_id:
            archive_config_service = ArchiveConfigurationService()
            archive_config = archive_config_service.get_by_id(int(archive_config_id))
            if not archive_config or archive_config.user_id != user.id:
                return jsonify({"status": "error", "message": "Archive configuration not found or not owned by user."}), 400
        else:
            # Use active configuration
            archive_config_service = ArchiveConfigurationService()
            archive_config = archive_config_service.get_active_for_user(user.id)
            if not archive_config:
                return jsonify({"status": "error", "message": "No active archive configuration found for user."}), 400
            archive_config_id = archive_config.id

        # Trigger the job
        background_job_service = current_app.background_job_service
        job_id = background_job_service.trigger_manual_archive(
            user_id=user.id,
            archive_config_id=archive_config_id,
            start_date=start_date,
            end_date=end_date
        )

        return jsonify({
            "status": "success",
            "message": "Manual archive job triggered successfully.",
            "job_id": job_id
        })

    except Exception as e:
        current_app.logger.exception(f"Manual archive job trigger exception: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@main_bp.route('/jobs/status')
@login_required
def get_job_status():
    """
    Get job status for the current user.
    """
    user = cast(User, current_user)

    try:
        scheduled_archive_service = current_app.scheduled_archive_service
        status = scheduled_archive_service.get_user_schedule_status(user.id)

        return jsonify({
            "status": "success",
            "data": status
        })

    except Exception as e:
        current_app.logger.exception(f"Get job status exception: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@main_bp.route('/jobs/remove', methods=['POST'])
@login_required
def remove_scheduled_jobs():
    """
    Remove all scheduled jobs for the current user.
    """
    user = cast(User, current_user)
    current_app.logger.info(f"Remove scheduled jobs requested by {user.email}")

    try:
        scheduled_archive_service = current_app.scheduled_archive_service
        result = scheduled_archive_service.remove_user_schedule(user.id)

        if result['failed_removals']:
            return jsonify({
                "status": "partial_success",
                "message": "Some jobs failed to remove.",
                "removed_jobs": result['removed_jobs'],
                "failed_removals": result['failed_removals']
            }), 207
        else:
            return jsonify({
                "status": "success",
                "message": "All scheduled jobs removed successfully.",
                "removed_jobs": result['removed_jobs']
            })

    except Exception as e:
        current_app.logger.exception(f"Remove scheduled jobs exception: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@main_bp.route('/jobs/health')
@login_required
def job_health_check():
    """
    Perform health check on the job scheduling system.
    """
    try:
        scheduled_archive_service = current_app.scheduled_archive_service
        health = scheduled_archive_service.health_check()

        return jsonify({
            "status": "success",
            "data": health
        })

    except Exception as e:
        current_app.logger.exception(f"Job health check exception: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500