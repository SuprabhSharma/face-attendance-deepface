from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
import os
import logging

def create_app():
    # Load environment variables
    load_dotenv()

    app = Flask(__name__)

    @app.get('/health')
    def health_check():
        return {'status': 'ok'}, 200

    # ==============================
    # 🔐 SECURITY & SESSION CONFIG
    # ==============================
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')

    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV', 'development') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = int(os.getenv('SESSION_TIMEOUT_MINUTES', 30)) * 60

    # ==============================
    # 🔑 LOGIN MANAGER
    # ==============================
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'error'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.db import get_user_by_id
        from app.routes.auth import User

        user_data = get_user_by_id(int(user_id))
        if user_data:
            return User(
                user_id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                role=user_data.get('role', 'user')
            )
        return None

    # ==============================
    # 📝 LOGGING SETUP
    # ==============================
    from app.utils.logging_config import setup_logging
    setup_logging()

    # ==============================
    # 🗄️ DATABASE INIT
    # ==============================
    from app.models.db import init_db, ensure_default_admin

    with app.app_context():
        try:
            init_db()
            ensure_default_admin()
        except Exception as e:
            logging.error(f"Database initialization failed: {e}")

    # ==============================
    # 📦 REGISTER BLUEPRINTS
    # ==============================
    from app.routes.views import views_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)

    # ==============================
    # 🤖 PRELOAD FACE MODEL (BACKGROUND THREAD)
    # Runs in a daemon thread so it never blocks Gunicorn startup.
    # By the time a real user logs in and reaches the register page,
    # SFace will already be warm in memory.
    # ==============================
    import threading
    def _preload_sface():
        try:
            from app.services.face_service import get_face_embedding  # triggers DeepFace.build_model
            logging.info("SFace model preloaded successfully in background thread.")
        except Exception as _e:
            logging.warning(f"SFace background preload warning: {_e}")

    _t = threading.Thread(target=_preload_sface, daemon=True)
    _t.start()

    # ==============================
    # ⏰ SCHEDULER (FIXED)
    # ==============================
    if os.getenv('SCHEDULER_ENABLED', 'true').lower() == 'true':
        try:
            from app.services.scheduler import start_scheduler, scheduler

            # ✅ Prevent multiple scheduler starts
            if not scheduler.running:
                start_scheduler()
            logging.info("[OK] Attendance scheduler started")

        except Exception as e:
            logging.error(f"Failed to start scheduler: {e}")

    return app
