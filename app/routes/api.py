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
    """Return cached face recognition functions. Load once, retry if previously failed."""
    if not _face_cache.get('ready'):
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
            logger.warning(f"Face module loading: {e}")
            return {'ready': False}
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
                'message': 'Face AI engine is initializing on the server. Please wait 10 seconds and try again.'
            }), 503

        data = request.get_json(silent=True)
        if not data:
            return jsonify({'success': False, 'message': 'Invalid image data received.'}), 400

        image_b64 = data.get('image', '')
        if not image_b64:
            return jsonify({'success': False, 'message': 'No camera image captured. Please allow camera access and try again.'}), 400

        img = fc['b64'](image_b64)
        if img is None:
            return jsonify({'success': False, 'message': 'Invalid image format received from camera.'}), 400

        user_data = get_user_by_id(current_user.id)
        if not user_data:
            return jsonify({'success': False, 'message': 'User account not found.'}), 404

        full_name = user_data.get('full_name') or user_data.get('username')

        # ── If face is already saved, treat as success
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
                # Same person
                return jsonify({
                    'success': True,
                    'already_registered': True,
                    'message': f'Face already registered for {full_name}. You can now mark attendance!'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': f'This face is already registered to another employee account ({dup_name}).'
                }), 400

        # Save embedding via database model helper
        try:
            from app.models.db import update_user_embedding
            update_user_embedding(current_user.id, embedding)
        except Exception as db_err:
            logger.error(f"DB error saving embedding: {db_err}")
            return jsonify({'success': False, 'message': 'Database error saving face biometrics. Please retry.'}), 500

        return jsonify({
            'success': True,
            'message': f'Face biometrics registered successfully for {full_name}!'
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
            elif status == 'already_absent':
                return jsonify({
                    'success': True,
                    'found': True,
                    'user_id': user_id,
                    'user_name': display_name,
                    'status': 'already_absent',
                    'message': f"You have already been marked ABSENT for today. Contact your administrator to override."
                })
            elif status == 'office_closed_sunday':
                return jsonify({
                    'success': True,
                    'found': True,
                    'user_id': user_id,
                    'user_name': display_name,
                    'status': 'office_closed_sunday',
                    'message': 'Office is closed on Sundays. Attendance is active Monday to Saturday (9:00 AM - 5:00 PM IST).'
                })
            elif status in ('office_closed', 'office_closed_early'):
                return jsonify({
                    'success': True,
                    'found': True,
                    'user_id': user_id,
                    'user_name': display_name,
                    'status': 'office_closed',
                    'message': 'Office hours are 9:00 AM - 5:00 PM IST. Attendance device is locked outside this window.'
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

            # Accurate 9-to-5 Corporate Time Window Categorization:
            if raw_status == 'absent' or not time_val:
                resolved_status = 'absent'
            elif time_val < '06:00:00' or time_val > '17:00:00':
                # Outside office hours (e.g. 11:14 PM) -> ABSENT
                resolved_status = 'absent'
            elif raw_status in ('half_day', 'late'):
                resolved_status = raw_status
            elif time_val <= '09:15:00':
                # 06:00 AM - 09:15 AM -> PRESENT (On-Time + 15m Grace)
                resolved_status = 'present'
            elif time_val <= '13:00:00':
                # 09:16 AM - 01:00 PM -> LATE
                resolved_status = 'late'
            elif time_val <= '17:00:00':
                # 01:01 PM - 05:00 PM -> HALF DAY
                resolved_status = 'half_day'
            else:
                resolved_status = 'absent'

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
