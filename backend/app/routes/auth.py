"""Auth routes — POST /register, POST /login, GET /me."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.auth_service import register_user, login_user
from app.models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    body, status = register_user(
        name=data.get("name", "").strip(),
        email=data.get("email", "").strip().lower(),
        password=data.get("password", ""),
        role=data.get("role", "").strip().lower(),
    )
    return jsonify(body), status


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    body, status = login_user(
        email=data.get("email", "").strip().lower(),
        password=data.get("password", ""),
    )
    return jsonify(body), status


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Return the currently authenticated user's profile."""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404
    return jsonify({"success": True, "user": user.to_dict()}), 200
