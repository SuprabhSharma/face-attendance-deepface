"""Groups routes — CRUD + student management."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.middleware.auth import trainer_required
from app.services.group_service import (
    create_group,
    get_trainer_groups,
    get_student_groups,
    update_group,
    delete_group,
    add_student_to_group,
    remove_student_from_group,
    get_group_students,
)
from app.models.user import User

groups_bp = Blueprint("groups", __name__, url_prefix="/api/groups")


@groups_bp.route("", methods=["POST"])
@trainer_required
def create():
    data = request.get_json(silent=True) or {}
    user_id = int(get_jwt_identity())
    body, status = create_group(name=data.get("name", ""), trainer_id=user_id)
    return jsonify(body), status


@groups_bp.route("", methods=["GET"])
@jwt_required()
def list_groups():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    if user.role == "trainer":
        body, status = get_trainer_groups(user_id)
    else:
        body, status = get_student_groups(user_id)
    return jsonify(body), status


@groups_bp.route("/<int:group_id>", methods=["PUT"])
@trainer_required
def update(group_id):
    data = request.get_json(silent=True) or {}
    user_id = int(get_jwt_identity())
    body, status = update_group(group_id, user_id, name=data.get("name", ""))
    return jsonify(body), status


@groups_bp.route("/<int:group_id>", methods=["DELETE"])
@trainer_required
def delete(group_id):
    user_id = int(get_jwt_identity())
    body, status = delete_group(group_id, user_id)
    return jsonify(body), status


@groups_bp.route("/<int:group_id>/students", methods=["GET"])
@jwt_required()
def students(group_id):
    user_id = int(get_jwt_identity())
    body, status = get_group_students(group_id, user_id)
    return jsonify(body), status


@groups_bp.route("/<int:group_id>/add-student", methods=["POST"])
@trainer_required
def add_student(group_id):
    data = request.get_json(silent=True) or {}
    user_id = int(get_jwt_identity())
    body, status = add_student_to_group(
        group_id, user_id, student_email=data.get("email", "").strip().lower()
    )
    return jsonify(body), status


@groups_bp.route("/<int:group_id>/remove-student", methods=["DELETE"])
@trainer_required
def remove_student(group_id):
    data = request.get_json(silent=True) or {}
    user_id = int(get_jwt_identity())
    body, status = remove_student_from_group(
        group_id, user_id, student_id=data.get("student_id")
    )
    return jsonify(body), status
