# app/views_UserInfo.py
# coding=utf-8

import json
import logging

from flask import Blueprint, current_app, jsonify, request

from .model.models import User

UserInfo_bp = Blueprint('UserInfo_bp', __name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@UserInfo_bp.route('/get_user', methods=['GET'])
def get_user():
    id = request.args.get('id', type=int)
    role = request.args.get('role', type=int)

    if id is None or role is None:
        return jsonify({
            "status_code": 10001,
            "error": "Missing required parameters"
        }), 400

    user_data = {
        "id": id,
        "role": role,
        "username": f"user_{id}",
        "role_name": f"role_{role}"
    }

    return jsonify(user_data), 200


@UserInfo_bp.route('/UserInfo', methods=['POST'])
def GetUserInfo():
    if not request.is_json:
        return jsonify({
            "status_code": 10002,
            "error": "Request body must be JSON"
        }), 400

    data = request.get_json()
    if not data or 'role' not in data:
        return jsonify({
            "status_code": 10003,
            "error": "Missing required field: role"
        }), 400

    try:
        role = int(data.get('role'))
    except (ValueError, TypeError):
        return jsonify({
            "status_code": 10004,
            "error": "Invalid role value"
        }), 400

    cache_key = f'users_with_role:{role}'

    if current_app.redis is not None:
        try:
            cached_data = current_app.redis.get(cache_key)
            if cached_data:
                return jsonify(json.loads(cached_data.decode('utf-8'))), 200
        except Exception as exc:
            logger.warning("Redis read failed for key %s: %s", cache_key, exc)

    users = User.query.filter_by(role=role).all()

    if not users:
        return jsonify({
            "status_code": 10005,
            "error": "No users found for the specified role"
        }), 404

    user_dicts = [user.action_to_dict() for user in users]

    if current_app.redis is not None:
        try:
            current_app.redis.set(cache_key, jsonify(user_dicts).data, ex=600)
        except Exception as exc:
            logger.warning("Redis write failed for key %s: %s", cache_key, exc)

    return jsonify(user_dicts), 200
