"""Face routes — upload and recognize faces."""

import traceback

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.utils.helpers import base64_to_cv2
from app.services.face_service import (
    get_face_embedding,
    store_face_encoding,
    check_duplicate_face,
    recognize_faces_in_group,
)

face_bp = Blueprint("face", __name__, url_prefix="/api")


@face_bp.route("/upload-face", methods=["POST"])
@jwt_required()
def upload_face():
    """Student uploads a face image → encoding stored in DB."""
    try:
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("image", "")

        if not image_b64:
            return jsonify({"success": False, "message": "Image is required."}), 400

        img = base64_to_cv2(image_b64)
        if img is None:
            return jsonify({"success": False, "message": "Invalid image format."}), 400

        embedding, err = get_face_embedding(img)
        if err:
            return jsonify({"success": False, "message": err}), 400

        # Duplicate check
        is_dup, dup_name = check_duplicate_face(embedding)
        if is_dup:
            return jsonify({
                "success": False,
                "message": f"Face already registered under: {dup_name}",
            }), 400

        user_id = int(get_jwt_identity())
        store_face_encoding(user_id, embedding)

        return jsonify({"success": True, "message": "Face registered successfully."}), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


@face_bp.route("/recognize-face", methods=["POST"])
@jwt_required()
def recognize_face():
    """Trainer sends a face image → matched against group students."""
    try:
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("image", "")
        group_id = data.get("group_id")
        session_id = data.get("session_id")

        if not image_b64:
            return jsonify({"success": False, "message": "Image is required."}), 400
        if not group_id:
            return jsonify({"success": False, "message": "group_id is required."}), 400

        img = base64_to_cv2(image_b64)
        if img is None:
            return jsonify({"success": False, "message": "Invalid image format."}), 400

        embedding, err = get_face_embedding(img)
        if err:
            return jsonify({"success": False, "message": err}), 400

        user_id, user_name = recognize_faces_in_group(embedding, group_id)

        if user_id:
            # Auto-mark present if session is provided
            if session_id:
                from app.services.attendance_service import mark_present

                mark_body, _ = mark_present(session_id, user_id, group_id)
                already = mark_body.get("already_marked", False)
                msg = (
                    f"{user_name} already marked present."
                    if already
                    else f"{user_name} marked present."
                )
            else:
                msg = f"Recognised: {user_name}"

            return jsonify({
                "success": True,
                "found": True,
                "student_id": user_id,
                "name": user_name,
                "message": msg,
            }), 200
        else:
            return jsonify({
                "success": True,
                "found": False,
                "message": "Face not recognised.",
            }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500
