"""Attendance routes — sessions, marking, and history."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.middleware.auth import trainer_required
from app.services.attendance_service import (
    start_session,
    end_session,
    get_student_attendance,
    get_session_attendance,
    get_group_attendance,
)

attendance_bp = Blueprint("attendance", __name__, url_prefix="/api/attendance")


@attendance_bp.route("/start", methods=["POST"])
@trainer_required
def start():
    data = request.get_json(silent=True) or {}
    user_id = int(get_jwt_identity())
    body, status = start_session(
        group_id=data.get("group_id"),
        trainer_id=user_id,
    )
    return jsonify(body), status


@attendance_bp.route("/end", methods=["POST"])
@trainer_required
def end():
    data = request.get_json(silent=True) or {}
    user_id = int(get_jwt_identity())
    body, status = end_session(
        session_id=data.get("session_id"),
        trainer_id=user_id,
    )
    return jsonify(body), status


@attendance_bp.route("/session/<int:session_id>", methods=["GET"])
@jwt_required()
def session_records(session_id):
    body, status = get_session_attendance(session_id)
    return jsonify(body), status


@attendance_bp.route("/group/<int:group_id>", methods=["GET"])
@jwt_required()
def group_records(group_id):
    body, status = get_group_attendance(group_id)
    return jsonify(body), status


@attendance_bp.route("/student/<int:student_id>", methods=["GET"])
@jwt_required()
def student_records(student_id):
    body, status = get_student_attendance(student_id)
    return jsonify(body), status


@attendance_bp.route("/my", methods=["GET"])
@jwt_required()
def my_attendance():
    """Convenience endpoint — return current user's attendance."""
    user_id = int(get_jwt_identity())
    body, status = get_student_attendance(user_id)
    return jsonify(body), status
