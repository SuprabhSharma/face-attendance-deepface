"""
Authentication routes for user login, registration, and session management.
Handles user authentication flow using Flask-Login for session management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
import logging
import os
import re
import secrets
from datetime import timedelta
from app.models.db import (
    is_face_enrolled,
    authenticate_user,
    create_user,
    get_user_by_username,
    get_user_by_email,
    get_user_by_id,
    update_user_profile_picture,
    update_user_password,
    hash_password,
    hash_otp,
    create_or_replace_pending_verification,
    get_active_pending_by_email,
    increment_pending_attempt,
    mark_pending_used,
    update_pending_resend,
    create_or_replace_password_reset_otp,
    get_active_password_reset_by_email,
    increment_password_reset_attempt,
    mark_password_reset_used,
    update_password_reset_resend,
    _utc_now,
    _parse_utc,
    _to_utc_iso,
)
from app.services.email_service import email_service

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Get logger
logger = logging.getLogger('auth')


class User:
    """User object for Flask-Login with full attributes including profile photo and biometric enrollment state"""
    def __init__(self, user_id, username, email, full_name=None, profile_picture=None, role='user', is_active=True, is_enrolled=False):
        self.id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name or username
        self.profile_picture = profile_picture
        self.role = role
        self.is_active = is_active
        self.is_enrolled = bool(is_enrolled)
        self.is_authenticated = True
    
    def get_id(self):
        """Return user ID as a string (required by Flask-Login)"""
        return str(self.id)
    
    def is_anonymous(self):
        return False


def validate_username(username):
    """Validate name used as username — allows letters, spaces, dots"""
    if len(username) < 2 or len(username) > 50:
        return False, "Name must be 2-50 characters"
    return True, ""


def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[a-zA-Z]', password):
        return False, "Password must contain letters"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain numbers"
    return True, ""


def validate_email(email):
    """Validate email format (must be Gmail)"""
    if not re.match(r'^[a-zA-Z0-9._%+-]+@gmail\.com$', email):
        return False, "Email must be a valid Gmail address (@gmail.com)"
    return True, ""


def _render_login_template(login_mode='user'):
    return render_template(
        'auth/login.html',
        login_mode=login_mode,
        is_admin_login=login_mode == 'admin'
    )


def _handle_login(login_mode='user'):
    """Shared login handler for user and admin entry points."""
    if current_user.is_authenticated:
        if login_mode == 'admin' and current_user.role == 'admin':
            return redirect(url_for('views.admin_dashboard'))
        return redirect(url_for('views.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        if not username or not password:
            flash('Please enter username and password', 'error')
            logger.warning(f"Login attempt with missing credentials from {request.remote_addr}")
            redirect_endpoint = 'auth.admin_login' if login_mode == 'admin' else 'auth.login'
            return redirect(url_for(redirect_endpoint))

        user_data = authenticate_user(username, password)

        if user_data:
            if user_data.get('status') == 'inactive':
                flash('Your account has been deactivated. Contact administrator.', 'error')
                logger.warning(f"Login attempt on inactive account: {username}")
                redirect_endpoint = 'auth.admin_login' if login_mode == 'admin' else 'auth.login'
                return redirect(url_for(redirect_endpoint))

            if login_mode == 'admin' and user_data.get('role') != 'admin':
                flash('Only administrator accounts can use the admin login.', 'error')
                logger.warning(f"Non-admin tried admin login: {username} from {request.remote_addr}")
                return redirect(url_for('auth.admin_login'))

            if login_mode == 'user' and user_data.get('role') == 'admin':
                flash('Please use the Admin Login section for administrator accounts.', 'error')
                logger.warning(f"Admin tried user login route: {username} from {request.remote_addr}")
                return redirect(url_for('auth.login'))

            user = User(
                user_id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                full_name=user_data.get('full_name'),
                profile_picture=user_data.get('profile_picture'),
                role=user_data.get('role', 'user'),
                is_enrolled=is_face_enrolled(user_data.get('embedding'))
            )

            login_user(user, remember=remember)
            logger.info(f"User logged in: {username} from {request.remote_addr}")

            flash(f'Welcome back, {user_data["full_name"]}!', 'success')

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)

            if user.role == 'admin':
                return redirect(url_for('views.admin_dashboard'))
            return redirect(url_for('views.dashboard'))

        flash('Invalid username or password', 'error')
        logger.warning(f"Failed login attempt for username: {username} from {request.remote_addr}")
        redirect_endpoint = 'auth.admin_login' if login_mode == 'admin' else 'auth.login'
        return redirect(url_for(redirect_endpoint))

    return _render_login_template(login_mode)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    return _handle_login('user')


@auth_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """Administrator login route."""
    return _handle_login('admin')


def _otp_config():
    return {
        'expires_minutes': int(os.getenv('OTP_EXPIRES_MINUTES', '10')),
        'max_attempts': int(os.getenv('OTP_MAX_ATTEMPTS', '5')),
        'resend_cooldown': int(os.getenv('OTP_RESEND_COOLDOWN_SECONDS', '60')),
        'max_resends': int(os.getenv('OTP_MAX_RESENDS', '3')),
    }


def _generate_otp() -> str:
    """Cryptographically secure six-digit numeric OTP."""
    return f'{secrets.randbelow(1_000_000):06d}'


def _generate_reset_otp() -> str:
    """Cryptographically secure four-digit numeric OTP for password recovery."""
    return f'{secrets.randbelow(10_000):04d}'


def _mask_email(email: str) -> str:
    if not email or '@' not in email:
        return '***'
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = local[0] + '*'
    else:
        masked_local = local[0] + ('*' * min(len(local) - 2, 6)) + local[-1]
    return f'{masked_local}@{domain}'


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Step 1 of registration: validate fields, check duplicates, send OTP.
    User account is NOT created until OTP is verified at /auth/verify-email.
    """
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        errors = []

        if not full_name:
            errors.append('Your name is required.')
        elif len(full_name) < 2 or len(full_name) > 50:
            errors.append('Name must be 2–50 characters.')

        if not email:
            errors.append('Email address is required.')
        else:
            is_valid, msg = validate_email(email)
            if not is_valid:
                errors.append(msg)

        if not password:
            errors.append('Password is required.')
        else:
            is_valid, msg = validate_password(password)
            if not is_valid:
                errors.append(msg)

        if password != confirm_password:
            errors.append('Passwords do not match.')

        username = full_name

        if not errors:
            if get_user_by_username(username):
                errors.append(
                    f'The name "{full_name}" is already registered. Please sign in or use a different name.'
                )
            if get_user_by_email(email):
                errors.append('This email is already registered. Please sign in.')

        if errors:
            for error in errors:
                flash(error, 'error')
            logger.warning('Registration validation failed for email=%s', email or '(empty)')
            return redirect(url_for('auth.register'))

        cfg = _otp_config()
        otp = _generate_otp()
        password_hash = hash_password(password)
        otp_hash_value = hash_otp(otp)
        expires_at = _utc_now() + timedelta(minutes=cfg['expires_minutes'])

        try:
            create_or_replace_pending_verification(
                email=email,
                full_name=full_name,
                username=username,
                password_hash=password_hash,
                otp_hash=otp_hash_value,
                expires_at=expires_at,
                resend_count=0,
            )
        except Exception as e:
            logger.error('Failed to store pending verification for %s: %s', email, type(e).__name__)
            flash('An error occurred during registration. Please try again.', 'error')
            return redirect(url_for('auth.register'))

        sent = email_service.send_registration_otp(email, full_name, otp)
        # Do not keep OTP in any variable beyond this point in logs
        del otp

        if not sent:
            flash(
                'We could not send the verification email right now. '
                'Please try again in a moment. If the problem continues, contact support.',
                'error',
            )
            logger.error('SMTP send failed during registration for %s — account not created', email)
            return redirect(url_for('auth.register'))

        session['pending_verify_email'] = email
        flash('A verification code has been sent to your Gmail. Enter it below to finish registration.', 'success')
        return redirect(url_for('auth.verify_email', email=email))

    return render_template('auth/register.html')


@auth_bp.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    """
    Step 2: verify six-digit OTP and create the user with is_verified=1.
    """
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))

    email = (
        request.values.get('email')
        or session.get('pending_verify_email')
        or ''
    ).strip().lower()

    if not email:
        flash('Start registration again to receive a verification code.', 'error')
        return redirect(url_for('auth.register'))

    pending = get_active_pending_by_email(email)
    cfg = _otp_config()
    masked = _mask_email(email)

    if request.method == 'GET':
        if not pending:
            flash('No pending verification found for this email. Please register again.', 'error')
            return redirect(url_for('auth.register'))
        expires_at = _parse_utc(pending.get('expires_at'))
        last_sent = _parse_utc(pending.get('last_sent_at'))
        now = _utc_now()
        seconds_left = max(0, int((expires_at - now).total_seconds())) if expires_at else 0
        cooldown_left = 0
        if last_sent:
            elapsed = int((now - last_sent).total_seconds())
            cooldown_left = max(0, cfg['resend_cooldown'] - elapsed)
        return render_template(
            'auth/verify_email.html',
            email=email,
            masked_email=masked,
            expires_seconds=seconds_left,
            resend_cooldown=cooldown_left,
            max_resends=cfg['max_resends'],
            resend_count=int(pending.get('resend_count') or 0),
        )

    # POST — verify OTP
    if not pending:
        flash('No pending verification found. Please register again.', 'error')
        return redirect(url_for('auth.register'))

    otp_digits = ''.join(
        (request.form.get(f'otp_{i}', '') or '') for i in range(6)
    ).strip()
    if not otp_digits:
        otp_digits = (request.form.get('otp') or '').strip()

    if not re.fullmatch(r'\d{6}', otp_digits):
        flash('Enter the 6-digit code from your email.', 'error')
        return redirect(url_for('auth.verify_email', email=email))

    expires_at = _parse_utc(pending.get('expires_at'))
    if not expires_at or _utc_now() > expires_at:
        flash('This verification code has expired. Request a new one.', 'error')
        return redirect(url_for('auth.verify_email', email=email))

    attempts = int(pending.get('attempt_count') or 0)
    if attempts >= cfg['max_attempts']:
        flash('Too many incorrect attempts. Request a new code or register again.', 'error')
        return redirect(url_for('auth.verify_email', email=email))

    if hash_otp(otp_digits) != pending.get('otp_hash'):
        new_count = increment_pending_attempt(pending['id'])
        remaining = max(0, cfg['max_attempts'] - new_count)
        if remaining <= 0:
            flash('Too many incorrect attempts. Request a new code or register again.', 'error')
        else:
            flash(f'Invalid verification code. {remaining} attempt(s) remaining.', 'error')
        return redirect(url_for('auth.verify_email', email=email))

    # Final duplicate check before insert (race-safe)
    if get_user_by_username(pending['username']) or get_user_by_email(pending['email']):
        mark_pending_used(pending['id'])
        flash('This name or email is already registered. Please sign in.', 'error')
        return redirect(url_for('auth.login'))

    result = create_user(
        username=pending['username'],
        email=pending['email'],
        full_name=pending['full_name'],
        role='user',
        is_verified=1,
        password_hash=pending['password_hash'],
    )

    if isinstance(result, tuple):
        mark_pending_used(pending['id'])
        flash(result[1] if result[1] else 'Could not create account. Please try again.', 'error')
        return redirect(url_for('auth.register'))

    mark_pending_used(pending['id'])
    session.pop('pending_verify_email', None)
    logger.info('User verified and created: %s (%s)', pending['full_name'], pending['email'])
    flash('Email verified successfully! Your account is ready. Please sign in.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend registration OTP with cooldown and max-resend limits."""
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))

    email = (request.form.get('email') or session.get('pending_verify_email') or '').strip().lower()
    if not email:
        flash('Start registration again to receive a verification code.', 'error')
        return redirect(url_for('auth.register'))

    pending = get_active_pending_by_email(email)
    if not pending:
        flash('No pending verification found. Please register again.', 'error')
        return redirect(url_for('auth.register'))

    cfg = _otp_config()
    resend_count = int(pending.get('resend_count') or 0)
    if resend_count >= cfg['max_resends']:
        flash('Maximum resend limit reached. Please register again later.', 'error')
        return redirect(url_for('auth.verify_email', email=email))

    last_sent = _parse_utc(pending.get('last_sent_at'))
    if last_sent:
        elapsed = int((_utc_now() - last_sent).total_seconds())
        if elapsed < cfg['resend_cooldown']:
            wait = cfg['resend_cooldown'] - elapsed
            flash(f'Please wait {wait} second(s) before requesting a new code.', 'error')
            return redirect(url_for('auth.verify_email', email=email))

    otp = _generate_otp()
    otp_hash_value = hash_otp(otp)
    expires_at = _utc_now() + timedelta(minutes=cfg['expires_minutes'])
    new_resend = resend_count + 1

    updated = update_pending_resend(pending['id'], otp_hash_value, expires_at, new_resend)
    if not updated:
        flash('Could not refresh the verification code. Please register again.', 'error')
        return redirect(url_for('auth.register'))

    sent = email_service.send_registration_otp(email, pending['full_name'], otp)
    del otp

    if not sent:
        flash(
            'We could not send the verification email right now. Please try again shortly.',
            'error',
        )
        return redirect(url_for('auth.verify_email', email=email))

    flash('A new verification code has been sent to your Gmail.', 'success')
    return redirect(url_for('auth.verify_email', email=email))


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user and end session"""
    username = current_user.username
    logout_user()
    logger.info(f"User logged out: {username}")
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    """
    User profile page showing account information.
    Renders Admin Console for admins, or Attendance History for employees.
    """
    user_data = get_user_by_id(current_user.id)

    if not user_data:
        logout_user()
        flash('User account not found', 'error')
        return redirect(url_for('auth.login'))

    admin_stats = {}
    if user_data.get('role') == 'admin':
        from app.models.db import get_all_users, get_currently_on_duty_count
        all_users = get_all_users()
        on_duty_cnt, shift_msg, is_shift_active = get_currently_on_duty_count()
        employees_count = sum(1 for u in all_users if u.get('role') != 'admin')
        checkin_rate = round((on_duty_cnt / employees_count) * 100) if employees_count > 0 else 0

        admin_stats = {
            'total_users': len(all_users),
            'enrolled_biometrics': sum(1 for u in all_users if u.get('role') != 'admin' and is_face_enrolled(u.get('embedding'))),
            'active_employees': employees_count,
            'on_duty_count': on_duty_cnt,
            'shift_msg': shift_msg,
            'is_shift_active': is_shift_active,
            'checkin_rate': checkin_rate
        }

    return render_template('auth/profile.html', user=user_data, admin_stats=admin_stats)


@auth_bp.route('/update-profile-picture', methods=['POST'])
@login_required
def update_profile_picture_route():
    """Upload or update user profile picture in real-time"""
    try:
        data = request.get_json(silent=True) or {}
        image_data = data.get('image')

        # Also support multipart file uploads
        if not image_data and 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                import base64
                file_bytes = file.read()
                mime = file.mimetype or 'image/jpeg'
                b64 = base64.b64encode(file_bytes).decode('utf-8')
                image_data = f"data:{mime};base64,{b64}"

        if not image_data:
            return jsonify({'success': False, 'message': 'No image provided'}), 400

        # Validate base64 data URL
        if not (image_data.startswith('data:image/') or image_data.startswith('http')):
            return jsonify({'success': False, 'message': 'Invalid image format'}), 400

        update_user_profile_picture(current_user.id, image_data)
        logger.info(f"Updated profile picture for user #{current_user.id} ({current_user.username})")
        return jsonify({
            'success': True,
            'message': 'Profile picture updated successfully',
            'profile_picture': image_data
        })
    except Exception as e:
        logger.error(f"Error updating profile picture: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@auth_bp.route('/remove-profile-picture', methods=['POST'])
@login_required
def remove_profile_picture_route():
    """Remove user profile picture"""
    try:
        update_user_profile_picture(current_user.id, None)
        logger.info(f"Removed profile picture for user #{current_user.id} ({current_user.username})")
        return jsonify({'success': True, 'message': 'Profile picture removed successfully'})
    except Exception as e:
        logger.error(f"Error removing profile picture: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Get current user data
        user_data = get_user_by_id(current_user.id)
        
        # Verify old password
        if not authenticate_user(user_data['username'], old_password):
            flash('Current password is incorrect', 'error')
            logger.warning(f"Failed password change attempt for user: {current_user.username}")
            return redirect(url_for('auth.change_password'))
        
        # Validate new password
        is_valid, msg = validate_password(new_password)
        if not is_valid:
            flash(msg, 'error')
            return redirect(url_for('auth.change_password'))
        
        # Check passwords match
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('auth.change_password'))
        
        # Check not same as old password
        if old_password == new_password:
            flash('New password must be different from current password', 'error')
            return redirect(url_for('auth.change_password'))
        
        # Update password
        try:
            from app.models.db import update_user_password
            update_user_password(current_user.id, new_password)
            logger.info(f"Password changed for user: {current_user.username}")
            flash('Password changed successfully!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            logger.error(f"Error changing password for user {current_user.id}: {str(e)}")
            flash('An error occurred while changing password', 'error')
            return redirect(url_for('auth.change_password'))
    
    return render_template('auth/change_password.html', user=current_user)



@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Step 1: request a 4-digit recovery OTP by Gmail address."""
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        # Always show the same response (no account enumeration)
        generic_msg = (
            'If an account exists for that Gmail address, a 4-digit recovery code '
            'has been sent. Check your inbox (and Spam).'
        )

        is_valid, msg = validate_email(email) if email else (False, 'Email required')
        if not is_valid:
            flash(msg if email else 'Please enter your Gmail address.', 'error')
            return redirect(url_for('auth.forgot_password'))

        user = get_user_by_email(email)
        if user and user.get('status') != 'inactive':
            cfg = _otp_config()
            otp = _generate_reset_otp()
            expires_at = _utc_now() + timedelta(minutes=cfg['expires_minutes'])
            try:
                create_or_replace_password_reset_otp(
                    user_id=user['id'],
                    email=email,
                    otp_hash=hash_otp(otp),
                    expires_at=expires_at,
                    resend_count=0,
                )
                full_name = user.get('full_name') or user.get('username') or 'there'
                sent = email_service.send_password_reset_otp(email, full_name, otp)
                if not sent:
                    logger.error('Password-reset OTP SMTP send failed for %s', email)
                    flash(
                        'Could not send the recovery email right now. '
                        'Check SMTP settings or try again shortly.',
                        'error',
                    )
                    return redirect(url_for('auth.forgot_password'))
            except Exception:
                logger.exception('Password-reset OTP create/send failed')
                flash('Something went wrong. Please try again.', 'error')
                return redirect(url_for('auth.forgot_password'))

        session['pwd_reset_email'] = email
        flash(generic_msg, 'success')
        return redirect(url_for('auth.verify_reset_otp'))

    return render_template('auth/forgot_password.html')


@auth_bp.route('/verify-reset-otp', methods=['GET', 'POST'])
def verify_reset_otp():
    """Step 2: enter the 4-digit recovery code."""
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))

    email = (session.get('pwd_reset_email') or '').strip().lower()
    if not email:
        flash('Start password recovery by entering your email first.', 'error')
        return redirect(url_for('auth.forgot_password'))

    cfg = _otp_config()
    pending = get_active_password_reset_by_email(email)
    cooldown_remaining = 0
    if pending and pending.get('last_sent_at'):
        last = _parse_utc(pending['last_sent_at'])
        if last:
            elapsed = (_utc_now() - last).total_seconds()
            cooldown_remaining = max(0, int(cfg['resend_cooldown'] - elapsed))

    if request.method == 'POST':
        otp = ''.join(ch for ch in request.form.get('otp', '') if ch.isdigit())
        if len(otp) != 4:
            flash('Enter the 4-digit code from your email.', 'error')
            return redirect(url_for('auth.verify_reset_otp'))

        pending = get_active_password_reset_by_email(email)
        if not pending:
            flash('No active recovery code. Request a new one.', 'error')
            return redirect(url_for('auth.forgot_password'))

        expires = _parse_utc(pending.get('expires_at'))
        if not expires or _utc_now() > expires:
            mark_password_reset_used(pending['id'])
            flash('This code has expired. Request a new one.', 'error')
            return redirect(url_for('auth.forgot_password'))

        attempts = int(pending.get('attempt_count') or 0)
        if attempts >= cfg['max_attempts']:
            mark_password_reset_used(pending['id'])
            flash('Too many incorrect attempts. Request a new code.', 'error')
            return redirect(url_for('auth.forgot_password'))

        if hash_otp(otp) != pending.get('otp_hash'):
            new_count = increment_password_reset_attempt(pending['id'])
            left = max(0, cfg['max_attempts'] - new_count)
            flash(f'Incorrect code. {left} attempt(s) remaining.', 'error')
            return redirect(url_for('auth.verify_reset_otp'))

        # Success — single-use OTP
        mark_password_reset_used(pending['id'])
        session['pwd_reset_user_id'] = int(pending['user_id'])
        session['pwd_reset_authorized_until'] = _to_utc_iso(
            _utc_now() + timedelta(minutes=15)
        )
        session.modified = True
        session.pop('pwd_reset_email', None)
        flash('Identity verified. You can set a new password or continue without changing it.', 'success')
        return redirect(url_for('auth.reset_password_options'))

    return render_template(
        'auth/verify_reset_otp.html',
        email=email,
        masked_email=_mask_email(email),
        expires_minutes=cfg['expires_minutes'],
        cooldown_remaining=cooldown_remaining,
        max_resends=cfg['max_resends'],
        resend_count=int((pending or {}).get('resend_count') or 0),
    )


@auth_bp.route('/resend-reset-otp', methods=['POST'])
def resend_reset_otp():
    """Resend password-recovery OTP with cooldown and max-resend limits."""
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))

    email = (session.get('pwd_reset_email') or '').strip().lower()
    if not email:
        flash('Start password recovery by entering your email first.', 'error')
        return redirect(url_for('auth.forgot_password'))

    cfg = _otp_config()
    pending = get_active_password_reset_by_email(email)
    if not pending:
        # Re-issue from user record if prior row was consumed/expired
        user = get_user_by_email(email)
        if not user or user.get('status') == 'inactive':
            flash('Unable to resend. Start recovery again.', 'error')
            return redirect(url_for('auth.forgot_password'))
        otp = _generate_reset_otp()
        expires_at = _utc_now() + timedelta(minutes=cfg['expires_minutes'])
        create_or_replace_password_reset_otp(
            user_id=user['id'], email=email, otp_hash=hash_otp(otp),
            expires_at=expires_at, resend_count=0,
        )
        sent = email_service.send_password_reset_otp(
            email, user.get('full_name') or user.get('username') or 'there', otp
        )
        if not sent:
            flash('Could not send email. Try again shortly.', 'error')
        else:
            flash('A new recovery code was sent to your Gmail.', 'success')
        return redirect(url_for('auth.verify_reset_otp'))

    last = _parse_utc(pending.get('last_sent_at'))
    if last:
        elapsed = (_utc_now() - last).total_seconds()
        if elapsed < cfg['resend_cooldown']:
            wait = int(cfg['resend_cooldown'] - elapsed)
            flash(f'Please wait {wait}s before requesting another code.', 'error')
            return redirect(url_for('auth.verify_reset_otp'))

    resend_count = int(pending.get('resend_count') or 0)
    if resend_count >= cfg['max_resends']:
        flash('Maximum resends reached. Start recovery again later.', 'error')
        return redirect(url_for('auth.forgot_password'))

    user = get_user_by_id(pending['user_id'])
    otp = _generate_reset_otp()
    expires_at = _utc_now() + timedelta(minutes=cfg['expires_minutes'])
    update_password_reset_resend(
        pending['id'], hash_otp(otp), expires_at, resend_count + 1
    )
    sent = email_service.send_password_reset_otp(
        email,
        (user or {}).get('full_name') or (user or {}).get('username') or 'there',
        otp,
    )
    if not sent:
        flash('Could not send email. Try again shortly.', 'error')
    else:
        flash('A new recovery code was sent to your Gmail.', 'success')
    return redirect(url_for('auth.verify_reset_otp'))


def _password_reset_session_ok():
    """Return user_id if the post-OTP reset session is still valid."""
    uid = session.get('pwd_reset_user_id')
    until = session.get('pwd_reset_authorized_until')
    if not uid or not until:
        return None
    try:
        exp = _parse_utc(until)
        if not exp:
            # Unparseable timestamp — do not strand a just-verified user
            logger.warning('pwd_reset_authorized_until unparseable: %r', until)
            return int(uid)
        if _utc_now() > exp:
            session.pop('pwd_reset_user_id', None)
            session.pop('pwd_reset_authorized_until', None)
            return None
        return int(uid)
    except (TypeError, ValueError):
        return None


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_options():
    """Step 3: set a new password or continue without changing it."""
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))

    user_id = _password_reset_session_ok()
    if not user_id:
        flash('Recovery session expired. Please verify a new code.', 'error')
        return redirect(url_for('auth.forgot_password'))

    user = get_user_by_id(user_id)
    if not user:
        flash('Account not found.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        action = request.form.get('action', 'change')
        if action == 'skip':
            session.pop('pwd_reset_user_id', None)
            session.pop('pwd_reset_authorized_until', None)
            flash('You can sign in with your existing password.', 'success')
            return redirect(url_for('auth.login'))

        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        ok, msg = validate_password(password)
        if not ok:
            flash(msg, 'error')
            return redirect(url_for('auth.reset_password_options'))
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.reset_password_options'))

        if update_user_password(user_id, password):
            session.pop('pwd_reset_user_id', None)
            session.pop('pwd_reset_authorized_until', None)
            logger.info('Password reset completed for user_id=%s', user_id)
            flash('Password updated. Please sign in with your new password.', 'success')
            return redirect(url_for('auth.login'))

        flash('Could not update password. Try again.', 'error')
        return redirect(url_for('auth.reset_password_options'))

    return render_template(
        'auth/reset_password.html',
        full_name=user.get('full_name') or user.get('username'),
        email=_mask_email(user.get('email') or ''),
    )



def role_required(required_role):
    """
    Decorator to check user role.
    Usage: @role_required('admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please login first', 'error')
                return redirect(url_for('auth.login', next=request.url))
            
            if current_user.role != required_role:
                flash('You do not have permission to access this page', 'error')
                logger.warning(f"Unauthorized access attempt by user {current_user.username} to {required_role} page")
                return redirect(url_for('views.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
