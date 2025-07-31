# backend/auth/routes.py
"""
TeleBoost Auth Routes
API endpoints для авторизації
"""
import logging
from flask import Blueprint, request, jsonify, g
from datetime import datetime, timezone

from backend.auth.telegram_auth import (
    verify_telegram_data,
    extract_referral_code,
    get_user_display_name
)
from backend.auth.jwt_handler import (
    create_tokens_pair,
    refresh_access_token,
    revoke_token,
    decode_token
)
from backend.auth.models import User, UserSession
from backend.auth.decorators import jwt_required, optional_jwt, rate_limit
from backend.utils.validators import sanitize_string
from backend.utils.constants import SUCCESS_MESSAGES, ERROR_MESSAGES

logger = logging.getLogger(__name__)

# Створюємо Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/telegram', methods=['POST'])
@rate_limit(calls=10, period=60)  # 10 спроб авторизації за хвилину
def telegram_login():
    """
    Авторизація через Telegram Web App

    Request body:
    {
        "initData": "query_id=...",  // URL-encoded init data від Telegram
        "referralCode": "TB12345678"  // Опціонально
    }

    Response:
    {
        "success": true,
        "message": "Login successful",
        "data": {
            "user": {...},
            "tokens": {
                "access_token": "...",
                "refresh_token": "...",
                "token_type": "Bearer",
                "expires_in": 86400
            }
        }
    }
    """
    try:
        data = request.get_json()

        if not data or 'initData' not in data:
            return jsonify({
                'success': False,
                'error': 'initData is required',
                'code': 'MISSING_INIT_DATA'
            }), 400

        init_data = data['initData']

        # Верифікуємо дані від Telegram
        is_valid, telegram_data = verify_telegram_data(init_data)

        if not is_valid or not telegram_data:
            logger.warning(f"Invalid Telegram auth attempt")
            return jsonify({
                'success': False,
                'error': 'Invalid Telegram data',
                'code': 'INVALID_TELEGRAM_DATA'
            }), 401

        # Витягуємо реферальний код
        referral_code = data.get('referralCode') or extract_referral_code(init_data)

        # Шукаємо або створюємо користувача
        user = User.get_by_telegram_id(telegram_data['id'])

        if user:
            # Оновлюємо дані існуючого користувача
            update_data = {
                'username': telegram_data.get('username', ''),
                'first_name': telegram_data.get('first_name', ''),
                'last_name': telegram_data.get('last_name', ''),
                'photo_url': telegram_data.get('photo_url', ''),
                'is_premium': telegram_data.get('is_premium', False),
                'last_login': datetime.now(timezone.utc).isoformat(),
            }
            user.update(update_data)

            logger.info(f"User {user.telegram_id} logged in")
        else:
            # Створюємо нового користувача
            user = User.create(telegram_data, referral_code)

            if not user:
                return jsonify({
                    'success': False,
                    'error': 'Failed to create user',
                    'code': 'USER_CREATION_FAILED'
                }), 500

            logger.info(f"New user created: {user.telegram_id}")

        # Генеруємо токени
        tokens = create_tokens_pair(user.to_dict())

        # Створюємо сесію
        # Для отримання JTI декодуємо токени
        access_payload = decode_token(tokens['access_token'], verify_exp=False)[1]
        refresh_payload = decode_token(tokens['refresh_token'], verify_exp=False)[1]

        session = UserSession.create(
            user_id=user.id,
            access_jti=access_payload['jti'],
            refresh_jti=refresh_payload['jti'],
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            expires_at=datetime.fromtimestamp(refresh_payload['exp'], tz=timezone.utc)
        )

        return jsonify({
            'success': True,
            'message': SUCCESS_MESSAGES['LOGIN_SUCCESS'],
            'data': {
                'user': user.to_public_dict(),
                'tokens': tokens
            }
        }), 200

    except Exception as e:
        logger.error(f"Telegram login error: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'LOGIN_ERROR'
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
@rate_limit(calls=5, period=60)  # 5 оновлень токена за хвилину
def refresh_token():
    """
    Оновити access token використовуючи refresh token

    Request body:
    {
        "refresh_token": "..."
    }

    Response:
    {
        "success": true,
        "data": {
            "access_token": "...",
            "token_type": "Bearer",
            "expires_in": 86400
        }
    }
    """
    try:
        data = request.get_json()

        if not data or 'refresh_token' not in data:
            return jsonify({
                'success': False,
                'error': 'refresh_token is required',
                'code': 'MISSING_REFRESH_TOKEN'
            }), 400

        refresh_token = data['refresh_token']

        # Оновлюємо токен
        result = refresh_access_token(refresh_token)

        if not result:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired refresh token',
                'code': 'INVALID_REFRESH_TOKEN'
            }), 401

        return jsonify({
            'success': True,
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'REFRESH_ERROR'
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required
def logout():
    """
    Вийти з системи (відкликати токени)

    Headers:
    Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Logged out successfully"
    }
    """
    try:
        # Отримуємо токен з заголовка
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')

        # Відкликаємо access token
        revoke_token(token)

        # Деактивуємо сесію якщо є JTI
        if hasattr(g, 'jwt_payload') and g.jwt_payload:
            jti = g.jwt_payload.get('jti')
            if jti:
                # Знаходимо та деактивуємо сесію
                sessions = UserSession.get_active_sessions(g.current_user.id)
                for session in sessions:
                    if session.access_token_jti == jti:
                        session.deactivate()
                        break

        logger.info(f"User {g.current_user.telegram_id} logged out")

        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'LOGOUT_ERROR'
        }), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required
def get_current_user():
    """
    Отримати дані поточного користувача

    Headers:
    Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "data": {
            "user": {...}
        }
    }
    """
    try:
        return jsonify({
            'success': True,
            'data': {
                'user': g.current_user.to_public_dict()
            }
        }), 200

    except Exception as e:
        logger.error(f"Get current user error: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'USER_ERROR'
        }), 500


@auth_bp.route('/me', methods=['PUT'])
@jwt_required
def update_current_user():
    """
    Оновити дані поточного користувача

    Headers:
    Authorization: Bearer <access_token>

    Request body:
    {
        "username": "new_username",
        "first_name": "John",
        "last_name": "Doe",
        "language_code": "uk",
        "settings": {
            "notifications": true,
            "language": "uk"
        }
    }

    Response:
    {
        "success": true,
        "message": "User updated successfully",
        "data": {
            "user": {...}
        }
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required',
                'code': 'MISSING_BODY'
            }), 400

        # Санітизуємо дані
        if 'username' in data:
            data['username'] = sanitize_string(data['username'], max_length=32)
        if 'first_name' in data:
            data['first_name'] = sanitize_string(data['first_name'], max_length=64)
        if 'last_name' in data:
            data['last_name'] = sanitize_string(data['last_name'], max_length=64)

        # Оновлюємо користувача
        success = g.current_user.update(data)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to update user',
                'code': 'UPDATE_FAILED'
            }), 500

        logger.info(f"User {g.current_user.telegram_id} updated profile")

        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'data': {
                'user': g.current_user.to_public_dict()
            }
        }), 200

    except Exception as e:
        logger.error(f"Update user error: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'UPDATE_ERROR'
        }), 500


@auth_bp.route('/verify', methods=['GET'])
@optional_jwt
def verify_token():
    """
    Перевірити валідність токена

    Headers:
    Authorization: Bearer <access_token> (опціонально)

    Response:
    {
        "success": true,
        "data": {
            "valid": true,
            "user": {...}  // якщо токен валідний
        }
    }
    """
    try:
        if g.current_user:
            return jsonify({
                'success': True,
                'data': {
                    'valid': True,
                    'user': g.current_user.to_public_dict()
                }
            }), 200
        else:
            return jsonify({
                'success': True,
                'data': {
                    'valid': False
                }
            }), 200

    except Exception as e:
        logger.error(f"Token verify error: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'VERIFY_ERROR'
        }), 500


@auth_bp.route('/sessions', methods=['GET'])
@jwt_required
def get_sessions():
    """
    Отримати активні сесії користувача

    Headers:
    Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "data": {
            "sessions": [
                {
                    "id": "...",
                    "ip_address": "...",
                    "user_agent": "...",
                    "created_at": "...",
                    "expires_at": "...",
                    "is_current": true
                }
            ]
        }
    }
    """
    try:
        sessions = UserSession.get_active_sessions(g.current_user.id)

        # Визначаємо поточну сесію
        current_jti = g.jwt_payload.get('jti') if hasattr(g, 'jwt_payload') else None

        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': session.id,
                'ip_address': session.ip_address,
                'user_agent': session.user_agent,
                'created_at': session.created_at,
                'expires_at': session.expires_at,
                'is_current': session.access_token_jti == current_jti
            })

        return jsonify({
            'success': True,
            'data': {
                'sessions': sessions_data
            }
        }), 200

    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'SESSIONS_ERROR'
        }), 500


@auth_bp.route('/sessions/<session_id>', methods=['DELETE'])
@jwt_required
def revoke_session(session_id):
    """
    Відкликати конкретну сесію

    Headers:
    Authorization: Bearer <access_token>

    Response:
    {
        "success": true,
        "message": "Session revoked successfully"
    }
    """
    try:
        # Знаходимо сесію
        sessions = UserSession.get_active_sessions(g.current_user.id)
        session_to_revoke = None

        for session in sessions:
            if session.id == session_id:
                session_to_revoke = session
                break

        if not session_to_revoke:
            return jsonify({
                'success': False,
                'error': 'Session not found',
                'code': 'SESSION_NOT_FOUND'
            }), 404

        # Деактивуємо сесію
        session_to_revoke.deactivate()

        logger.info(f"User {g.current_user.telegram_id} revoked session {session_id}")

        return jsonify({
            'success': True,
            'message': 'Session revoked successfully'
        }), 200

    except Exception as e:
        logger.error(f"Revoke session error: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'REVOKE_ERROR'
        }), 500