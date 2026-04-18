"""Authentication middleware — role-checking decorators."""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from app.models.user import User


def trainer_required(fn):
    """Allow access only to authenticated trainers."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != "trainer":
            return jsonify({"success": False, "message": "Trainer access required."}), 403
        return fn(*args, **kwargs)

    return wrapper


def student_required(fn):
    """Allow access only to authenticated students."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != "student":
            return jsonify({"success": False, "message": "Student access required."}), 403
        return fn(*args, **kwargs)

    return wrapper
