"""Flask application factory."""

from flask import Flask
from config import Config
from app.extensions import db, jwt, bcrypt, cors


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Initialise extensions ──────────────────────────────────────
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app, origins=app.config["CORS_ORIGINS"], supports_credentials=True)

    # ── Import models so SQLAlchemy knows about them ───────────────
    from app.models import user, group, group_student, face_data  # noqa: F401
    from app.models import attendance_session, attendance          # noqa: F401

    # ── Register blueprints ────────────────────────────────────────
    from app.routes.auth import auth_bp
    from app.routes.groups import groups_bp
    from app.routes.face import face_bp
    from app.routes.attendance import attendance_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(face_bp)
    app.register_blueprint(attendance_bp)

    # ── Create tables on first request (dev convenience) ───────────
    with app.app_context():
        db.create_all()

    return app
