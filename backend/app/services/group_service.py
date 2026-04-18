"""Group service — CRUD + student enrolment logic."""

from app.extensions import db
from app.models.group import Group
from app.models.group_student import GroupStudent
from app.models.user import User


# ── CRUD ──────────────────────────────────────────────────────────


def create_group(name: str, trainer_id: int):
    if not name or not name.strip():
        return {"success": False, "message": "Group name is required."}, 400

    group = Group(name=name.strip(), trainer_id=trainer_id)
    db.session.add(group)
    db.session.commit()

    return {
        "success": True,
        "message": "Group created.",
        "group": group.to_dict(),
    }, 201


def get_trainer_groups(trainer_id: int):
    groups = Group.query.filter_by(trainer_id=trainer_id).order_by(Group.created_at.desc()).all()
    return {
        "success": True,
        "groups": [g.to_dict() for g in groups],
    }, 200


def get_student_groups(student_id: int):
    memberships = GroupStudent.query.filter_by(student_id=student_id).all()
    group_ids = [m.group_id for m in memberships]
    groups = Group.query.filter(Group.id.in_(group_ids)).order_by(Group.created_at.desc()).all()
    return {
        "success": True,
        "groups": [g.to_dict() for g in groups],
    }, 200


def update_group(group_id: int, trainer_id: int, name: str):
    group = Group.query.get(group_id)
    if not group:
        return {"success": False, "message": "Group not found."}, 404
    if group.trainer_id != trainer_id:
        return {"success": False, "message": "Not authorised."}, 403
    if not name or not name.strip():
        return {"success": False, "message": "Group name is required."}, 400

    group.name = name.strip()
    db.session.commit()

    return {"success": True, "message": "Group updated.", "group": group.to_dict()}, 200


def delete_group(group_id: int, trainer_id: int):
    group = Group.query.get(group_id)
    if not group:
        return {"success": False, "message": "Group not found."}, 404
    if group.trainer_id != trainer_id:
        return {"success": False, "message": "Not authorised."}, 403

    db.session.delete(group)
    db.session.commit()

    return {"success": True, "message": "Group deleted."}, 200


# ── Student enrolment ─────────────────────────────────────────────


def add_student_to_group(group_id: int, trainer_id: int, student_email: str):
    group = Group.query.get(group_id)
    if not group:
        return {"success": False, "message": "Group not found."}, 404
    if group.trainer_id != trainer_id:
        return {"success": False, "message": "Not authorised."}, 403

    student = User.query.filter_by(email=student_email, role="student").first()
    if not student:
        return {"success": False, "message": "Student not found with that email."}, 404

    existing = GroupStudent.query.filter_by(group_id=group_id, student_id=student.id).first()
    if existing:
        return {"success": False, "message": "Student already in this group."}, 409

    gs = GroupStudent(group_id=group_id, student_id=student.id)
    db.session.add(gs)
    db.session.commit()

    return {
        "success": True,
        "message": f"{student.name} added to group.",
        "student": gs.to_dict(),
    }, 201


def remove_student_from_group(group_id: int, trainer_id: int, student_id: int):
    group = Group.query.get(group_id)
    if not group:
        return {"success": False, "message": "Group not found."}, 404
    if group.trainer_id != trainer_id:
        return {"success": False, "message": "Not authorised."}, 403

    gs = GroupStudent.query.filter_by(group_id=group_id, student_id=student_id).first()
    if not gs:
        return {"success": False, "message": "Student not in this group."}, 404

    db.session.delete(gs)
    db.session.commit()

    return {"success": True, "message": "Student removed from group."}, 200


def get_group_students(group_id: int, user_id: int):
    """Get students in a group. Accessible by the group's trainer or any enrolled student."""
    group = Group.query.get(group_id)
    if not group:
        return {"success": False, "message": "Group not found."}, 404

    # Check authorization — trainer owner or enrolled student
    user = User.query.get(user_id)
    if not user:
        return {"success": False, "message": "User not found."}, 404

    if user.role == "trainer" and group.trainer_id != user_id:
        return {"success": False, "message": "Not authorised."}, 403

    if user.role == "student":
        enrolled = GroupStudent.query.filter_by(group_id=group_id, student_id=user_id).first()
        if not enrolled:
            return {"success": False, "message": "Not authorised."}, 403

    students = GroupStudent.query.filter_by(group_id=group_id).all()
    return {
        "success": True,
        "students": [s.to_dict() for s in students],
    }, 200
