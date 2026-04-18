"""Authentication service — registration and login logic."""

from app.extensions import db, bcrypt
from app.models.user import User
from app.utils.helpers import is_valid_email
from flask_jwt_extended import create_access_token


def register_user(name: str, email: str, password: str, role: str):
    """Create a new user account.

    Returns (dict, int) — (response body, HTTP status code).
    """
    # ── Validation ─────────────────────────────────────────────────
    if not all([name, email, password, role]):
        return {"success": False, "message": "All fields are required."}, 400

    if not is_valid_email(email):
        return {"success": False, "message": "Invalid email format."}, 400

    if len(password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters."}, 400

    if role not in ("trainer", "student"):
        return {"success": False, "message": "Role must be 'trainer' or 'student'."}, 400

    if User.query.filter_by(email=email).first():
        return {"success": False, "message": "Email already registered."}, 409

    # ── Create user ────────────────────────────────────────────────
    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(name=name, email=email, password=hashed_pw, role=role)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))

    return {
        "success": True,
        "message": "Registration successful.",
        "token": token,
        "user": user.to_dict(),
    }, 201


def login_user(email: str, password: str):
    """Authenticate an existing user.

    Returns (dict, int) — (response body, HTTP status code).
    """
    if not email or not password:
        return {"success": False, "message": "Email and password are required."}, 400

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return {"success": False, "message": "Invalid email or password."}, 401

    token = create_access_token(identity=str(user.id))

    return {
        "success": True,
        "message": "Login successful.",
        "token": token,
        "user": user.to_dict(),
    }, 200
