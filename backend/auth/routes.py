# backend/auth/routes.py
"""
TeleBoost Auth Routes
API endpoints для авторизації
ВИПРАВЛЕНА ВЕРСІЯ З ДЕТАЛЬНИМ ЛОГУВАННЯМ
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
    logger.info("🔴 AUTH: ========== TELEGRAM LOGIN START ==========")
    logger.info(f"🔴 AUTH: Request method: {request.method}")
    logger.info(f"🔴 AUTH: Request headers count: {len(request.headers)}")
    logger.info(f"🔴 AUTH: Content-Type: {request.headers.get('Content-Type')}")
    logger.info(f"🔴 AUTH: Content-Length: {request.headers.get('Content-Length')}")
    logger.info(f"🔴 AUTH: Request remote_addr: {request.remote_addr}")

    try:
        # Отримуємо дані різними способами
        data = None

        # Спосіб 1: JSON body
        try:
            data = request.get_json(force=True)
            logger.info(f"🔴 AUTH: Got JSON data: {bool(data)}")
        except Exception as e:
            logger.warning(f"🔴 AUTH: Failed to parse JSON: {e}")

        # Спосіб 2: Form data
        if not data:
            try:
                data = request.form.to_dict()
                logger.info(f"🔴 AUTH: Got form data: {bool(data)}")
            except Exception as e:
                logger.warning(f"🔴 AUTH: Failed to parse form: {e}")

        # Спосіб 3: Raw data
        if not data:
            try:
                raw_data = request.get_data(as_text=True)
                logger.info(f"🔴 AUTH: Raw data length: {len(raw_data)}")
                logger.info(f"🔴 AUTH: Raw data preview: {raw_data[:200]}...")

                # Спробуємо розпарсити як JSON
                import json
                data = json.loads(raw_data)
            except Exception as e:
                logger.warning(f"🔴 AUTH: Failed to parse raw data: {e}")

        if data:
            logger.info(f"🔴 AUTH: Data keys: {list(data.keys())}")
            logger.info(f"🔴 AUTH: Has initData: {'initData' in data}")
            logger.info(f"🔴 AUTH: Has referralCode: {'referralCode' in data}")

            if 'initData' in data:
                init_data = data['initData']
                logger.info(f"🔴 AUTH: initData type: {type(init_data)}")
                logger.info(
                    f"🔴 AUTH: initData length: {len(init_data) if isinstance(init_data, str) else 'not string'}")

                if isinstance(init_data, str):
                    logger.info(f"🔴 AUTH: initData preview: {init_data[:200]}...")

                    # Перевіряємо чи містить основні параметри
                    if 'auth_date=' in init_data:
                        logger.info("🔴 AUTH: initData contains auth_date")
                    if 'hash=' in init_data:
                        logger.info("🔴 AUTH: initData contains hash")
                    if 'user=' in init_data:
                        logger.info("🔴 AUTH: initData contains user")

        if not data or 'initData' not in data:
            logger.warning("🔴 AUTH: Missing initData in request")
            logger.warning(f"🔴 AUTH: Available data: {data}")
            return jsonify({
                'success': False,
                'error': 'initData is required',
                'code': 'MISSING_INIT_DATA',
                'debug': {
                    'received_keys': list(data.keys()) if data else [],
                    'content_type': request.headers.get('Content-Type')
                }
            }), 400

        init_data = data['initData']
        logger.info(f"🔴 AUTH: Extracted initData, length: {len(init_data)}")

        # Верифікуємо дані від Telegram
        logger.info("🔴 AUTH: Starting Telegram data verification...")
        is_valid, telegram_data = verify_telegram_data(init_data)

        logger.info(f"🔴 AUTH: Verification result: is_valid={is_valid}, has_data={bool(telegram_data)}")
        if telegram_data:
            logger.info(f"🔴 AUTH: Telegram data keys: {list(telegram_data.keys())}")
            logger.info(f"🔴 AUTH: User ID: {telegram_data.get('id')}")
            logger.info(f"🔴 AUTH: Username: {telegram_data.get('username')}")
            logger.info(f"🔴 AUTH: First name: {telegram_data.get('first_name')}")
            logger.info(f"🔴 AUTH: Is Premium: {telegram_data.get('is_premium')}")

        if not is_valid or not telegram_data:
            logger.warning(f"🔴 AUTH: Invalid Telegram auth attempt")
            logger.warning(f"🔴 AUTH: Verification failed - is_valid: {is_valid}, telegram_data: {telegram_data}")

            # Детальна інформація про помилку
            return jsonify({
                'success': False,
                'error': 'Invalid Telegram data',
                'code': 'INVALID_TELEGRAM_DATA',
                'debug': {
                    'is_valid': is_valid,
                    'has_telegram_data': bool(telegram_data),
                    'init_data_length': len(init_data),
                    'init_data_preview': init_data[:100] + '...' if len(init_data) > 100 else init_data
                }
            }), 401

        # Витягуємо реферальний код
        referral_code = data.get('referralCode') or extract_referral_code(init_data)
        logger.info(f"🔴 AUTH: Referral code: {referral_code}")

        # Шукаємо або створюємо користувача
        telegram_id = str(telegram_data['id'])
        logger.info(f"🔴 AUTH: Looking for user with telegram_id: {telegram_id}")

        user = User.get_by_telegram_id(telegram_id)
        logger.info(f"🔴 AUTH: User found: {bool(user)}")

        if user:
            logger.info(f"🔴 AUTH: Existing user - ID: {user.id}, username: {user.username}")

            # Оновлюємо дані існуючого користувача
            update_data = {
                'username': telegram_data.get('username', ''),
                'first_name': telegram_data.get('first_name', ''),
                'last_name': telegram_data.get('last_name', ''),
                'photo_url': telegram_data.get('photo_url', ''),
                'is_premium': telegram_data.get('is_premium', False),
                'last_login': datetime.now(timezone.utc).isoformat(),
            }
            logger.info(f"🔴 AUTH: Updating user data: {list(update_data.keys())}")

            update_result = user.update(update_data)
            logger.info(f"🔴 AUTH: User update result: {update_result}")

            logger.info(f"🔴 AUTH: User {user.telegram_id} logged in successfully")
        else:
            # Створюємо нового користувача
            logger.info(f"🔴 AUTH: Creating new user for telegram_id: {telegram_id}")
            logger.info(f"🔴 AUTH: User data for creation: {telegram_data}")

            user = User.create(telegram_data, referral_code)

            if not user:
                logger.error("🔴 AUTH: Failed to create user")
                logger.error(f"🔴 AUTH: Creation data: {telegram_data}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to create user',
                    'code': 'USER_CREATION_FAILED',
                    'debug': {
                        'telegram_id': telegram_id,
                        'telegram_data_keys': list(telegram_data.keys())
                    }
                }), 500

            logger.info(f"🔴 AUTH: New user created - ID: {user.id}, telegram_id: {user.telegram_id}")

        # Генеруємо токени
        logger.info("🔴 AUTH: Generating tokens...")
        user_dict = user.to_dict()
        logger.info(f"🔴 AUTH: User dict keys: {list(user_dict.keys())}")
        logger.info(f"🔴 AUTH: User dict id: {user_dict.get('id')}")
        logger.info(f"🔴 AUTH: User dict telegram_id: {user_dict.get('telegram_id')}")

        try:
            tokens = create_tokens_pair(user_dict)
            logger.info(f"🔴 AUTH: Tokens generated successfully")
            logger.info(f"🔴 AUTH: Token keys: {list(tokens.keys())}")
            logger.info(f"🔴 AUTH: Access token length: {len(tokens['access_token'])}")
            logger.info(f"🔴 AUTH: Refresh token length: {len(tokens['refresh_token'])}")
            logger.info(f"🔴 AUTH: Token expires in: {tokens['expires_in']} seconds")
        except Exception as e:
            logger.error(f"🔴 AUTH: Token generation failed: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': 'Failed to generate tokens',
                'code': 'TOKEN_GENERATION_FAILED'
            }), 500

        # Створюємо сесію
        logger.info("🔴 AUTH: Creating user session...")
        try:
            # Для отримання JTI декодуємо токени
            access_payload = decode_token(tokens['access_token'], verify_exp=False)[1]
            refresh_payload = decode_token(tokens['refresh_token'], verify_exp=False)[1]

            if not access_payload or not refresh_payload:
                logger.error("🔴 AUTH: Failed to decode tokens for session")
                raise Exception("Token decode failed")

            logger.info(f"🔴 AUTH: Access token JTI: {access_payload.get('jti')}")
            logger.info(f"🔴 AUTH: Refresh token JTI: {refresh_payload.get('jti')}")

            session = UserSession.create(
                user_id=user.id,
                access_jti=access_payload['jti'],
                refresh_jti=refresh_payload['jti'],
                ip_address=request.remote_addr or '0.0.0.0',
                user_agent=request.headers.get('User-Agent', ''),
                expires_at=datetime.fromtimestamp(refresh_payload['exp'], tz=timezone.utc)
            )

            logger.info(f"🔴 AUTH: Session created: {bool(session)}")
            if session:
                logger.info(f"🔴 AUTH: Session ID: {session.id}")
        except Exception as e:
            logger.error(f"🔴 AUTH: Session creation failed: {e}", exc_info=True)
            # Продовжуємо без сесії

        # Формуємо відповідь
        response_data = {
            'success': True,
            'message': SUCCESS_MESSAGES.get('LOGIN_SUCCESS', 'Login successful'),
            'data': {
                'user': user.to_public_dict(),
                'tokens': tokens
            }
        }

        logger.info("🔴 AUTH: Response prepared successfully")
        logger.info(f"🔴 AUTH: Response user keys: {list(response_data['data']['user'].keys())}")
        logger.info(f"🔴 AUTH: Response token keys: {list(response_data['data']['tokens'].keys())}")
        logger.info(f"🔴 AUTH: User display name: {user.get_display_name()}")
        logger.info("🔴 AUTH: ========== TELEGRAM LOGIN SUCCESS ==========")

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"🔴 AUTH: ========== TELEGRAM LOGIN ERROR ==========")
        logger.error(f"🔴 AUTH: Error type: {type(e).__name__}")
        logger.error(f"🔴 AUTH: Error message: {str(e)}")
        logger.error(f"🔴 AUTH: Error args: {e.args}")
        logger.error("🔴 AUTH: Full traceback:", exc_info=True)

        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES.get('INTERNAL_ERROR', 'Internal server error'),
            'code': 'LOGIN_ERROR',
            'debug': {
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
@rate_limit(calls=5, period=60)  # 5 оновлень токена за хвилину
def refresh_token():
    """
    Оновити access token використовуючи refresh token
    """
    logger.info("🔴 AUTH: /refresh endpoint called")

    try:
        data = request.get_json()
        logger.info(f"🔴 AUTH: Request data received: {bool(data)}")

        if not data or 'refresh_token' not in data:
            logger.warning("🔴 AUTH: Missing refresh_token in request")
            return jsonify({
                'success': False,
                'error': 'refresh_token is required',
                'code': 'MISSING_REFRESH_TOKEN'
            }), 400

        refresh_token = data['refresh_token']
        logger.info(f"🔴 AUTH: Refresh token length: {len(refresh_token)}")

        # Оновлюємо токен
        logger.info("🔴 AUTH: Attempting to refresh access token...")
        result = refresh_access_token(refresh_token)

        if not result:
            logger.warning("🔴 AUTH: Failed to refresh token")
            return jsonify({
                'success': False,
                'error': 'Invalid or expired refresh token',
                'code': 'INVALID_REFRESH_TOKEN'
            }), 401

        logger.info("🔴 AUTH: Token refreshed successfully")
        logger.info(f"🔴 AUTH: New token expires in: {result.get('expires_in')} seconds")

        return jsonify({
            'success': True,
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"🔴 AUTH: Token refresh error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES.get('INTERNAL_ERROR', 'Internal server error'),
            'code': 'REFRESH_ERROR'
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required
def logout():
    """
    Вийти з системи (відкликати токени)
    """
    logger.info("🔴 AUTH: /logout endpoint called")
    logger.info(f"🔴 AUTH: Current user: {g.current_user.telegram_id if hasattr(g, 'current_user') else 'Unknown'}")

    try:
        # Отримуємо токен з заголовка
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        logger.info(f"🔴 AUTH: Token to revoke length: {len(token)}")

        # Відкликаємо access token
        revoke_result = revoke_token(token)
        logger.info(f"🔴 AUTH: Token revoke result: {revoke_result}")

        # Деактивуємо сесію якщо є JTI
        if hasattr(g, 'jwt_payload') and g.jwt_payload:
            jti = g.jwt_payload.get('jti')
            logger.info(f"🔴 AUTH: Session JTI to deactivate: {jti}")

            if jti:
                # Знаходимо та деактивуємо сесію
                sessions = UserSession.get_active_sessions(g.current_user.id)
                logger.info(f"🔴 AUTH: Found {len(sessions)} active sessions")

                for session in sessions:
                    if session.access_token_jti == jti:
                        deactivate_result = session.deactivate()
                        logger.info(f"🔴 AUTH: Session deactivated: {deactivate_result}")
                        break

        logger.info(f"🔴 AUTH: User {g.current_user.telegram_id} logged out successfully")

        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200

    except Exception as e:
        logger.error(f"🔴 AUTH: Logout error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES.get('INTERNAL_ERROR', 'Internal server error'),
            'code': 'LOGOUT_ERROR'
        }), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required
def get_current_user():
    """
    Отримати дані поточного користувача
    """
    logger.info("🔴 AUTH: /me endpoint called")
    logger.info(f"🔴 AUTH: Current user ID: {g.current_user.id}")
    logger.info(f"🔴 AUTH: Current user telegram_id: {g.current_user.telegram_id}")

    try:
        user_data = g.current_user.to_public_dict()
        logger.info(f"🔴 AUTH: User data keys: {list(user_data.keys())}")

        return jsonify({
            'success': True,
            'data': {
                'user': user_data
            }
        }), 200

    except Exception as e:
        logger.error(f"🔴 AUTH: Get current user error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES.get('INTERNAL_ERROR', 'Internal server error'),
            'code': 'USER_ERROR'
        }), 500


@auth_bp.route('/me', methods=['PUT'])
@jwt_required
def update_current_user():
    """
    Оновити дані поточного користувача
    """
    logger.info("🔴 AUTH: /me PUT endpoint called")

    try:
        data = request.get_json()
        logger.info(f"🔴 AUTH: Update data received: {bool(data)}")

        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required',
                'code': 'MISSING_BODY'
            }), 400

        logger.info(f"🔴 AUTH: Fields to update: {list(data.keys())}")

        # Санітизуємо дані
        if 'username' in data:
            data['username'] = sanitize_string(data['username'], max_length=32)
        if 'first_name' in data:
            data['first_name'] = sanitize_string(data['first_name'], max_length=64)
        if 'last_name' in data:
            data['last_name'] = sanitize_string(data['last_name'], max_length=64)

        # Оновлюємо користувача
        success = g.current_user.update(data)
        logger.info(f"🔴 AUTH: Update result: {success}")

        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to update user',
                'code': 'UPDATE_FAILED'
            }), 500

        logger.info(f"🔴 AUTH: User {g.current_user.telegram_id} updated profile successfully")

        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'data': {
                'user': g.current_user.to_public_dict()
            }
        }), 200

    except Exception as e:
        logger.error(f"🔴 AUTH: Update user error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES.get('INTERNAL_ERROR', 'Internal server error'),
            'code': 'UPDATE_ERROR'
        }), 500


@auth_bp.route('/verify', methods=['GET'])
@optional_jwt
def verify_token():
    """
    Перевірити валідність токена
    """
    logger.info("🔴 AUTH: /verify endpoint called")
    logger.info(f"🔴 AUTH: Has current_user: {hasattr(g, 'current_user') and g.current_user is not None}")

    try:
        if g.current_user:
            logger.info(f"🔴 AUTH: Valid token for user: {g.current_user.telegram_id}")
            return jsonify({
                'success': True,
                'data': {
                    'valid': True,
                    'user': g.current_user.to_public_dict()
                }
            }), 200
        else:
            logger.info("🔴 AUTH: No valid token")
            return jsonify({
                'success': True,
                'data': {
                    'valid': False
                }
            }), 200

    except Exception as e:
        logger.error(f"🔴 AUTH: Token verify error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES.get('INTERNAL_ERROR', 'Internal server error'),
            'code': 'VERIFY_ERROR'
        }), 500


@auth_bp.route('/sessions', methods=['GET'])
@jwt_required
def get_sessions():
    """
    Отримати активні сесії користувача
    """
    logger.info("🔴 AUTH: /sessions endpoint called")

    try:
        sessions = UserSession.get_active_sessions(g.current_user.id)
        logger.info(f"🔴 AUTH: Found {len(sessions)} active sessions")

        # Визначаємо поточну сесію
        current_jti = g.jwt_payload.get('jti') if hasattr(g, 'jwt_payload') else None
        logger.info(f"🔴 AUTH: Current session JTI: {current_jti}")

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
        logger.error(f"🔴 AUTH: Get sessions error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES.get('INTERNAL_ERROR', 'Internal server error'),
            'code': 'SESSIONS_ERROR'
        }), 500


@auth_bp.route('/sessions/<session_id>', methods=['DELETE'])
@jwt_required
def revoke_session(session_id):
    """
    Відкликати конкретну сесію
    """
    logger.info(f"🔴 AUTH: /sessions/{session_id} DELETE endpoint called")

    try:
        # Знаходимо сесію
        sessions = UserSession.get_active_sessions(g.current_user.id)
        session_to_revoke = None

        for session in sessions:
            if session.id == session_id:
                session_to_revoke = session
                break

        if not session_to_revoke:
            logger.warning(f"🔴 AUTH: Session {session_id} not found")
            return jsonify({
                'success': False,
                'error': 'Session not found',
                'code': 'SESSION_NOT_FOUND'
            }), 404

        # Деактивуємо сесію
        deactivate_result = session_to_revoke.deactivate()
        logger.info(f"🔴 AUTH: Session deactivate result: {deactivate_result}")

        logger.info(f"🔴 AUTH: User {g.current_user.telegram_id} revoked session {session_id}")

        return jsonify({
            'success': True,
            'message': 'Session revoked successfully'
        }), 200

    except Exception as e:
        logger.error(f"🔴 AUTH: Revoke session error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES.get('INTERNAL_ERROR', 'Internal server error'),
            'code': 'REVOKE_ERROR'
        }), 500


# Тестовий endpoint для debug
@auth_bp.route('/test', methods=['GET', 'POST'])
def test_endpoint():
    """Тестовий endpoint для перевірки роботи"""
    logger.info("🔴 AUTH: Test endpoint called")

    return jsonify({
        'success': True,
        'message': 'Auth module is working',
        'data': {
            'method': request.method,
            'headers': dict(request.headers),
            'has_json': request.is_json,
            'content_type': request.content_type
        }
    }), 200


# Логування при імпорті модуля
logger.info("🔴 AUTH: routes.py module loaded, auth_bp created with prefix: /api/auth")