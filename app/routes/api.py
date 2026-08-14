from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import traceback
import logging
import json
from datetime import datetime, timezone, timedelta

api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger('app')

from app.models.db import (
    get_user_by_id, get_attendance_by_user, mark_attendance, get_all_users
)
from app.services.email_service import EmailService

email_service = EmailService()

# IST TIMEZONE
IST = timezone(timedelta(hours=5, minutes=30))

# ─────────────────────────────────────────────
# Safe cached lazy loader for face modules.
# Imports face_service only once, then caches it.
# This avoids circular imports at startup while
# still giving instant access on every API call.
# ─────────────────────────────────────────────
_face_cache = {}

def _face():
    """Return cached face recognition functions. Load once, reuse always."""
    if not _face_cache:
        try:
            from app.utils.helpers import base64_to_cv2 as _b64
            from app.services.face_service import (
                get_face_embedding as _emb,
                recognize_user as _rec,
                check_duplicate_face as _dup,
            )
            _face_cache['b64'] = _b64
            _face_cache['emb'] = _emb
            _face_cache['rec'] = _rec
            _face_cache['dup'] = _dup
            _face_cache['ready'] = True
        except Exception as e:
            logger.warning(f"Face module not ready yet: {e}")
            _face_cache['ready'] = False
    return _face_cache


@api_bp.route('/register-user', methods=['POST'])
@login_required
def register():
    try:
        logger.info(f"Face registration request for user_id={current_user.id}")

        fc = _face()
        if not fc.get('ready'):
            return jsonify({
                'success': False,
                'message': 'Face module still loading. Wait 10 seconds and try again.'
            }), 503

        data = request.get_json(silent=True)
        if not data:
            return jsonify({'success': False, 'message': 'Invalid data provided.'}), 400

        image_b64 = data.get('image', '')
        if not image_b64:
            return jsonify({'success': False, 'message': 'Image is required.'}), 400

        img = fc['b64'](image_b64)
        if img is None:
            return jsonify({'success': False, 'message': 'Invalid image format.'}), 400

        user_data = get_user_by_id(current_user.id)
        if not user_data:
            return jsonify({'success': False, 'message': 'User account not found.'}), 404

        full_name = user_data.get('full_name') or user_data.get('username')

        # ── If face is already saved (including from a previous timed-out request
        #    that completed in the background), treat it as success so the user
        #    is not left confused thinking registration failed.
        if user_data.get('embedding'):
            return jsonify({
                'success': True,
                'already_registered': True,
                'message': f'Face already registered for {full_name}. You can now mark attendance!'
            }), 200

        embedding, err = fc['emb'](img)
        if err:
            return jsonify({'success': False, 'message': err}), 400

        # Check if this face is already claimed by another account
        is_dup, dup_user_id, dup_name = fc['dup'](embedding)
        if is_dup:
            if dup_user_id == current_user.id:
                # Same person — treat as success (background save scenario)
                return jsonify({
                    'success': True,
                    'already_registered': True,
                    'message': f'Face already registered for {full_name}. You can now mark attendance!'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': f'This face is already registered to another account ({dup_name}).'
                }), 400

        # Save embedding
        try:
            from app.models.db import get_db_connection
            conn = get_db_connection()
            c = conn.cursor()
            embedding_json = json.dumps(embedding.tolist())
            c.execute('UPDATE users SET embedding = ? WHERE id = ?',
                      (embedding_json, current_user.id))
            conn.commit()
            conn.close()
        except Exception as db_err:
            logger.error(f"DB error saving embedding: {db_err}")
            return jsonify({'success': False, 'message': 'Failed to save face data. Please retry.'}), 500

        return jsonify({
            'success': True,
            'message': f'Face registered successfully for {full_name}!'
        })

    except Exception as e:
        logger.error(f"Error in register: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/recognize-face', methods=['POST'])
def recognize():
    try:
        recognition_time = datetime.now(IST)

        fc = _face()
        if not fc.get('ready'):
            return jsonify({
                'success': False,
                'message': 'Face module still loading. Please wait a moment and try again.'
            }), 503

        data = request.get_json(silent=True)
        if not data:
            return jsonify({'success': False, 'message': 'Invalid data provided.'}), 400

        image_b64 = data.get('image', '')
        if not image_b64:
            return jsonify({'success': False, 'message': 'Image is required.'}), 400

        img = fc['b64'](image_b64)
        if img is None:
            return jsonify({'success': False, 'message': 'Invalid image format.'}), 400

        embedding, err = fc['emb'](img)
        if err:
            return jsonify({'success': False, 'message': err}), 400

        if not any(user.get('embedding') for user in get_all_users()):
            return jsonify({
                'success': True,
                'found': False,
                'code': 'no_registered_faces',
                'message': 'No faces registered yet. Please register first.'
            })

        user_id, name = fc['rec'](embedding)

        if user_id:
            user_data = get_user_by_id(user_id)
            if not user_data:
                return jsonify({'success': True, 'found': False,
                                'message': 'User account not found.'}), 200

            display_name = user_data.get('full_name') or user_data.get('username')
            marked, status = mark_attendance(user_id, recognition_time)

            if marked:
                logger.info(f"Attendance marked: {display_name}")
                attendance_time = recognition_time.strftime('%Y-%m-%d %H:%M:%S')
                return jsonify({
                    'success': True,
                    'found': True,
                    'user_id': user_id,
                    'user_name': display_name,
                    'user_email': user_data['email'],
                    'status': status,
                    'marked_at': attendance_time,
                    'message': f"Welcome {display_name}! Attendance marked at {attendance_time} IST"
                })
            elif status in ('office_closed', 'office_closed_early'):
                return jsonify({
                    'success': True,
                    'found': True,
                    'user_id': user_id,
                    'user_name': display_name,
                    'status': 'office_closed',
                    'message': 'Office hours are 06:00 AM - 08:00 PM IST. Attendance cannot be marked outside this window.'
                })
            else:
                return jsonify({
                    'success': True,
                    'found': True,
                    'user_id': user_id,
                    'user_name': display_name,
                    'status': 'duplicate',
                    'message': f"Attendance already marked for {display_name} today."
                })

        return jsonify({
            'success': True,
            'found': False,
            'code': 'face_not_recognized',
            'message': 'Face not recognized. Look directly at the camera in good lighting.'
        })

    except Exception as e:
        logger.error(f"Error in recognize: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/attendance', methods=['GET'])
@login_required
def attendance():
    try:
        records = get_attendance_by_user(current_user.id, limit=50)
        user_data = get_user_by_id(current_user.id)
        display_name = user_data.get('full_name') if user_data else current_user.username

        res = []
        for r in records:
            time_val = r.get('time_in') or r.get('time')
            raw_status = r.get('status')

            # Resolve status using same corporate time windows for old records
            if raw_status in (None, '', 'present') and time_val:
                if time_val > '20:00:00' or time_val < '06:00:00':
                    resolved_status = raw_status or 'present'  # keep as-is for edge cases
                elif time_val > '13:00:00':
                    resolved_status = 'half_day'
                elif time_val > '09:15:00':
                    resolved_status = 'late'
                else:
                    resolved_status = 'present'
            else:
                resolved_status = raw_status or 'present'

            res.append({
                'date': r['date'],
                'name': r.get('full_name') or display_name,
                'time': time_val,
                'time_in': time_val,
                'time_out': r.get('time_out'),
                'marked_at': f"{r['date']}T{time_val}",
                'status': resolved_status
            })

        return jsonify({'success': True, 'data': res})

    except Exception as e:
        logger.error(f"Error retrieving attendance: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/users', methods=['GET'])
def get_users():
    try:
        users = get_all_users()
        res = [{'id': u['id'], 'name': u.get('full_name') or u.get('username')} for u in users]
        return jsonify({'success': True, 'data': res})
    except Exception as e:
        logger.error(f"Error retrieving users: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
