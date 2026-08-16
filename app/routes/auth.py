"""
Authentication routes for user login, registration, and session management.
Handles user authentication flow using Flask-Login for session management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
import logging
import re
from app.models.db import (
    authenticate_user, 
    create_user, 
    get_user_by_username,
    get_user_by_email,
    get_user_by_id,
    update_user_profile_picture
)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Get logger
logger = logging.getLogger('auth')


class User:
    """User object for Flask-Login with full attributes including profile photo"""
    def __init__(self, user_id, username, email, full_name=None, profile_picture=None, role='user', is_active=True):
        self.id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name or username
        self.profile_picture = profile_picture
        self.role = role
        self.is_active = is_active
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
                role=user_data.get('role', 'user')
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


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration. Accepts only: full_name, email, password, confirm_password.
    A URL-safe username is auto-derived from the name so the rest of the codebase
    that references 'username' for login continues to work without changes.
    """
    if current_user.is_authenticated:
        return redirect(url_for('views.dashboard'))

    if request.method == 'POST':
        full_name        = request.form.get('full_name', '').strip()
        email            = request.form.get('email', '').strip().lower()
        password         = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        errors = []

        # Name validation — this IS the username
        if not full_name:
            errors.append('Your name is required.')
        elif len(full_name) < 2 or len(full_name) > 50:
            errors.append('Name must be 2–50 characters.')

        # Email validation
        if not email:
            errors.append('Email address is required.')
        else:
            is_valid, msg = validate_email(email)
            if not is_valid:
                errors.append(msg)

        # Password validation
        if not password:
            errors.append('Password is required.')
        else:
            is_valid, msg = validate_password(password)
            if not is_valid:
                errors.append(msg)

        if password != confirm_password:
            errors.append('Passwords do not match.')

        # full_name IS the username — use it directly
        username = full_name

        if not errors:
            if get_user_by_username(username):
                errors.append(f'The name "{full_name}" is already registered. Please sign in or use a different name.')
            if get_user_by_email(email):
                errors.append('This email is already registered. Please sign in.')

        if errors:
            for error in errors:
                flash(error, 'error')
            logger.warning(f"Registration errors for email: {email}")
            return redirect(url_for('auth.register'))

        try:
            create_user(
                username=username,
                email=email,
                password=password,
                full_name=full_name,
                role='user'
            )
            logger.info(f"New user registered: {full_name} ({username}) email: {email}")
            flash('Account created successfully! Please sign in.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            logger.error(f"Error creating user {username}: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'error')
            return redirect(url_for('auth.register'))

    return render_template('auth/register.html')


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
        from app.models.db import get_all_users
        all_users = get_all_users()
        admin_stats = {
            'total_users': len(all_users),
            'enrolled_biometrics': sum(1 for u in all_users if u.get('embedding')),
            'active_employees': sum(1 for u in all_users if u.get('role') != 'admin' and u.get('status') == 'active')
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
