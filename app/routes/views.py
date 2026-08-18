from flask import Blueprint, render_template, redirect, url_for, send_from_directory, current_app
from flask_login import login_required, current_user, logout_user
from app.models.db import get_all_users_admin
from app.routes.auth import role_required
import os

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
def index():
    """Always start fresh - force logout"""
    logout_user()   # 🔥 force logout every time
    return redirect(url_for('auth.login'))

@views_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')

@views_bp.route('/register')
@login_required
def register():
    if current_user.role == 'admin':
        from flask import flash
        flash('System Administrators are exempt from attendance and face registration.', 'info')
        return redirect(url_for('views.admin_dashboard'))
    return render_template('register.html')

@views_bp.route('/camera')
@login_required
def camera():
    if current_user.role == 'admin':
        from flask import flash
        flash('System Administrators are exempt from attendance tracking.', 'info')
        return redirect(url_for('views.admin_dashboard'))
    return render_template('camera.html')

@views_bp.route('/report')
@login_required
def report():
    return render_template('report.html')

@views_bp.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    # The dashboard loads live attendance asynchronously. This keeps the
    # initial HTML small and prevents historical records from being rendered
    # into the page on every admin visit.
    return render_template('admin/dashboard.html')

@views_bp.route('/admin/users')
@login_required
@role_required('admin')
def admin_users():
    users = get_all_users_admin()
    return render_template('admin/users.html', users=users)

@views_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_user_route(user_id):
    from flask import request, jsonify, flash
    from app.models.db import get_user_by_id, verify_password, delete_user_completely

    # 1. Extract admin password from JSON or Form body
    if request.is_json:
        data = request.get_json() or {}
        admin_password = data.get('admin_password', '').strip()
    else:
        admin_password = request.form.get('admin_password', '').strip()

    if not admin_password:
        msg = "Admin password is required to authorize deletion."
        if request.is_json:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('views.admin_users'))

    # 2. Re-authenticate the active admin
    admin_record = get_user_by_id(current_user.id)
    if not admin_record or not verify_password(admin_record['password_hash'], admin_password):
        msg = "Incorrect admin password. Authorization failed."
        if request.is_json:
            return jsonify({'success': False, 'message': msg}), 403
        flash(msg, 'error')
        return redirect(url_for('views.admin_users'))

    # 3. Perform complete atomic purge
    success, msg = delete_user_completely(user_id, admin_id=current_user.id)
    if not success:
        if request.is_json:
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('views.admin_users'))

    if request.is_json:
        return jsonify({'success': True, 'message': msg})
    flash(msg, 'success')
    return redirect(url_for('views.admin_users'))

@views_bp.route('/admin/attendance')
@login_required
@role_required('admin')
def admin_attendance():
    # Keep the existing URL/bookmark, but use the same live admin dashboard.
    return render_template('admin/dashboard.html')

# ── PWA: Serve sw.js from root scope (browsers require this exact path) ──
@views_bp.route('/sw.js')
def service_worker():
    """Service Worker must be served from root scope for full PWA coverage."""
    static_dir = os.path.join(current_app.root_path, 'static')
    response = send_from_directory(static_dir, 'sw.js')
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@views_bp.route('/manifest.json')
def pwa_manifest():
    """Serve PWA manifest from root path for broad browser compatibility."""
    static_dir = os.path.join(current_app.root_path, 'static')
    response = send_from_directory(static_dir, 'manifest.json')
    response.headers['Content-Type'] = 'application/manifest+json'
    return response

# Error handlers
@views_bp.app_errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@views_bp.app_errorhandler(500)
def internal_server_error(error):
    return render_template('500.html'), 500
