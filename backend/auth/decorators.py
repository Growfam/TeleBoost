# backend/auth/decorators.py
"""
TeleBoost Auth Decorators
Декоратори для авторизації
ВЕРСИЯ С ПОЛНЫМ ЛОГИРОВАНИЕМ ДЛЯ ДИАГНОСТИКИ
"""
import logging
from functools import wraps
from typing import Optional, Callable, Any
from flask import request, jsonify, g

from backend.auth.jwt_handler import decode_token
from backend.auth.models import User

logger = logging.getLogger(__name__)


def jwt_required(f: Callable) -> Callable:
    """
    Декоратор для перевірки JWT токена

    Використання:
        @app.route('/api/protected')
        @jwt_required
        def protected_route():
            user = g.current_user
            return {'user_id': user.id}
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.info(f"🔵 JWT_REQUIRED: Decorator called for {request.method} {request.path}")

        # Логуємо всі заголовки для діагностики
        logger.info("🔵 JWT_REQUIRED: Request headers:")
        for header_name, header_value in request.headers:
            if header_name.lower() == 'authorization':
                # Маскуємо токен для безпеки
                if header_value and len(header_value) > 20:
                    masked_value = f"{header_value[:20]}...{header_value[-10:]}"
                else:
                    masked_value = header_value
                logger.info(f"🔵 JWT_REQUIRED:   {header_name}: {masked_value}")
            else:
                logger.info(f"🔵 JWT_REQUIRED:   {header_name}: {header_value}")

        # Отримуємо токен з заголовка
        auth_header = request.headers.get('Authorization')
        logger.info(f"🔵 JWT_REQUIRED: Authorization header exists: {bool(auth_header)}")

        if not auth_header:
            logger.warning("🔵 JWT_REQUIRED: No Authorization header found")
            return jsonify({
                'success': False,
                'error': 'Authorization header missing',
                'code': 'AUTH_HEADER_MISSING'
            }), 401

        logger.info(f"🔵 JWT_REQUIRED: Auth header length: {len(auth_header)}")
        logger.info(f"🔵 JWT_REQUIRED: Auth header preview: {auth_header[:30]}...")

        # Перевіряємо формат Bearer <token>
        parts = auth_header.split()
        logger.info(f"🔵 JWT_REQUIRED: Auth header parts count: {len(parts)}")

        if len(parts) != 2:
            logger.warning(f"🔵 JWT_REQUIRED: Invalid header format - expected 2 parts, got {len(parts)}")
            return jsonify({
                'success': False,
                'error': 'Invalid authorization header format',
                'code': 'INVALID_AUTH_HEADER'
            }), 401

        if parts[0] != 'Bearer':
            logger.warning(f"🔵 JWT_REQUIRED: Invalid header format - expected 'Bearer', got '{parts[0]}'")
            return jsonify({
                'success': False,
                'error': 'Invalid authorization header format',
                'code': 'INVALID_AUTH_HEADER'
            }), 401

        token = parts[1]
        logger.info(f"🔵 JWT_REQUIRED: Token extracted, length: {len(token)}")
        logger.info(f"🔵 JWT_REQUIRED: Token preview: {token[:20]}...{token[-10:]}")

        # Декодуємо токен
        logger.info("🔵 JWT_REQUIRED: Decoding token...")
        is_valid, payload = decode_token(token)

        logger.info(f"🔵 JWT_REQUIRED: Token decode result: is_valid={is_valid}, has_payload={bool(payload)}")

        if payload:
            logger.info(f"🔵 JWT_REQUIRED: Token payload keys: {list(payload.keys())}")
            logger.info(f"🔵 JWT_REQUIRED: Token type: {payload.get('type')}")
            logger.info(f"🔵 JWT_REQUIRED: User ID in token: {payload.get('user_id')}")
            logger.info(f"🔵 JWT_REQUIRED: Telegram ID in token: {payload.get('telegram_id')}")

        if not is_valid or not payload:
            logger.warning("🔵 JWT_REQUIRED: Token is invalid or decode failed")
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token',
                'code': 'INVALID_TOKEN'
            }), 401

        # Перевіряємо тип токена
        token_type = payload.get('type')
        if token_type != 'access':
            logger.warning(f"🔵 JWT_REQUIRED: Invalid token type: expected 'access', got '{token_type}'")
            return jsonify({
                'success': False,
                'error': 'Invalid token type',
                'code': 'INVALID_TOKEN_TYPE'
            }), 401

        # Отримуємо користувача
        user_id = payload['user_id']
        logger.info(f"🔵 JWT_REQUIRED: Looking up user with ID: {user_id}")

        user = User.get_by_id(user_id)
        logger.info(f"🔵 JWT_REQUIRED: User found: {bool(user)}")

        if not user:
            logger.warning(f"🔵 JWT_REQUIRED: User {user_id} not found in database")
            return jsonify({
                'success': False,
                'error': 'User not found',
                'code': 'USER_NOT_FOUND'
            }), 404

        logger.info(f"🔵 JWT_REQUIRED: User details - telegram_id: {user.telegram_id}, is_active: {user.is_active}")

        # Перевіряємо чи активний користувач
        if not user.is_active:
            logger.warning(f"🔵 JWT_REQUIRED: User {user.telegram_id} is inactive")
            return jsonify({
                'success': False,
                'error': 'User account is inactive',
                'code': 'USER_INACTIVE'
            }), 403

        # Зберігаємо користувача в g для доступу в route
        g.current_user = user
        g.jwt_payload = payload

        logger.info(f"🔵 JWT_REQUIRED: Authentication successful for user {user.telegram_id}")
        logger.info(f"🔵 JWT_REQUIRED: Proceeding to route handler: {f.__name__}")

        return f(*args, **kwargs)

    return decorated_function


def admin_required(f: Callable) -> Callable:
    """
    Декоратор для перевірки прав адміністратора

    Використання:
        @app.route('/api/admin/users')
        @jwt_required
        @admin_required
        def admin_users():
            return {'users': []}
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.info(f"🔵 ADMIN_REQUIRED: Decorator called for {request.method} {request.path}")

        # Перевіряємо чи є current_user (має бути встановлено jwt_required)
        if not hasattr(g, 'current_user') or not g.current_user:
            logger.warning("🔵 ADMIN_REQUIRED: No current_user in g")
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401

        logger.info(f"🔵 ADMIN_REQUIRED: Checking admin rights for user {g.current_user.telegram_id}")
        logger.info(f"🔵 ADMIN_REQUIRED: User is_admin: {g.current_user.is_admin}")

        # Перевіряємо чи є адміном
        if not g.current_user.is_admin:
            logger.warning(f"🔵 ADMIN_REQUIRED: User {g.current_user.telegram_id} is not admin")
            return jsonify({
                'success': False,
                'error': 'Admin access required',
                'code': 'ADMIN_REQUIRED'
            }), 403

        logger.info(f"🔵 ADMIN_REQUIRED: Admin access granted for user {g.current_user.telegram_id}")
        return f(*args, **kwargs)

    return decorated_function


def optional_jwt(f: Callable) -> Callable:
    """
    Декоратор для опціональної JWT авторизації

    Якщо токен є - валідує його, якщо немає - дозволяє доступ

    Використання:
        @app.route('/api/public')
        @optional_jwt
        def public_route():
            if g.current_user:
                return {'message': f'Hello {g.current_user.username}'}
            return {'message': 'Hello anonymous'}
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.info(f"🔵 OPTIONAL_JWT: Decorator called for {request.method} {request.path}")

        # Ініціалізуємо як None
        g.current_user = None
        g.jwt_payload = None

        # Отримуємо токен з заголовка
        auth_header = request.headers.get('Authorization')
        logger.info(f"🔵 OPTIONAL_JWT: Authorization header exists: {bool(auth_header)}")

        if auth_header:
            logger.info("🔵 OPTIONAL_JWT: Auth header found, attempting to validate")

            # Якщо є заголовок - намагаємося валідувати
            parts = auth_header.split()

            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]
                logger.info(f"🔵 OPTIONAL_JWT: Valid Bearer token format, length: {len(token)}")

                # Декодуємо токен
                is_valid, payload = decode_token(token)
                logger.info(f"🔵 OPTIONAL_JWT: Token decode result: is_valid={is_valid}")

                if is_valid and payload and payload.get('type') == 'access':
                    # Отримуємо користувача
                    user = User.get_by_id(payload['user_id'])

                    if user and user.is_active:
                        g.current_user = user
                        g.jwt_payload = payload
                        logger.info(f"🔵 OPTIONAL_JWT: Authenticated user: {user.telegram_id}")
                    else:
                        logger.info("🔵 OPTIONAL_JWT: User not found or inactive")
                else:
                    logger.info("🔵 OPTIONAL_JWT: Invalid token or wrong type")
            else:
                logger.info("🔵 OPTIONAL_JWT: Invalid Authorization header format")
        else:
            logger.info("🔵 OPTIONAL_JWT: No Authorization header, proceeding as anonymous")

        return f(*args, **kwargs)

    return decorated_function


def rate_limit(calls: int = 10, period: int = 60):
    """
    Декоратор для rate limiting

    Args:
        calls: Кількість дозволених викликів
        period: Період в секундах

    Використання:
        @app.route('/api/orders', methods=['POST'])
        @jwt_required
        @rate_limit(calls=5, period=60)  # 5 замовлень за хвилину
        def create_order():
            return {'order_id': '123'}
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger.info(f"🔵 RATE_LIMIT: Decorator called for {request.method} {request.path}")
            logger.info(f"🔵 RATE_LIMIT: Limits - {calls} calls per {period} seconds")

            from backend.utils.redis_client import redis_client
            from backend.utils.constants import CACHE_KEYS

            # Визначаємо ідентифікатор користувача
            if hasattr(g, 'current_user') and g.current_user:
                identifier = g.current_user.telegram_id
                logger.info(f"🔵 RATE_LIMIT: Using authenticated user ID: {identifier}")
            else:
                # Для анонімних використовуємо IP
                identifier = request.remote_addr
                logger.info(f"🔵 RATE_LIMIT: Using IP address: {identifier}")

            # Формуємо ключ для rate limit
            endpoint = request.endpoint or 'unknown'
            rate_key = f"rate_limit:{identifier}:{endpoint}"
            logger.info(f"🔵 RATE_LIMIT: Rate limit key: {rate_key}")

            try:
                # Перевіряємо кількість викликів
                current_calls = redis_client.get(rate_key, data_type='int')
                logger.info(f"🔵 RATE_LIMIT: Current calls: {current_calls}")

                if current_calls is None:
                    # Перший виклик
                    redis_client.set(rate_key, 1, ttl=period)
                    current_calls = 1
                    logger.info(f"🔵 RATE_LIMIT: First call, setting counter to 1")
                else:
                    if current_calls >= calls:
                        # Перевищено ліміт
                        ttl = redis_client.ttl(rate_key)
                        logger.warning(f"🔵 RATE_LIMIT: Limit exceeded for {identifier}, retry after {ttl}s")

                        return jsonify({
                            'success': False,
                            'error': f'Rate limit exceeded. Max {calls} requests per {period} seconds',
                            'code': 'RATE_LIMIT_EXCEEDED',
                            'retry_after': ttl
                        }), 429

                    # Інкрементуємо лічильник
                    redis_client.incr(rate_key)
                    current_calls += 1
                    logger.info(f"🔵 RATE_LIMIT: Incremented counter to {current_calls}")

                logger.info(f"🔵 RATE_LIMIT: Request allowed, {calls - current_calls} calls remaining")

            except Exception as e:
                # Якщо Redis недоступний - дозволяємо запит
                logger.error(f"🔵 RATE_LIMIT: Redis error: {e}, allowing request")

            # Додаємо заголовки rate limit
            response = f(*args, **kwargs)

            # Якщо відповідь - це tuple (response, status_code)
            if isinstance(response, tuple):
                response_obj, status_code = response
            else:
                response_obj = response
                status_code = 200

            # Конвертуємо в Response об'єкт якщо потрібно
            from flask import make_response
            response = make_response(response_obj, status_code)

            # Додаємо заголовки
            response.headers['X-RateLimit-Limit'] = str(calls)
            response.headers['X-RateLimit-Remaining'] = str(max(0, calls - current_calls))
            response.headers['X-RateLimit-Reset'] = str(redis_client.ttl(rate_key) if redis_client else period)

            logger.info(f"🔵 RATE_LIMIT: Response headers added")
            return response

        return decorated_function

    return decorator


def validate_request(schema: dict):
    """
    Декоратор для валідації request body

    Args:
        schema: Схема валідації

    Використання:
        @app.route('/api/orders', methods=['POST'])
        @jwt_required
        @validate_request({
            'service_id': {'type': 'integer', 'required': True},
            'link': {'type': 'string', 'required': True},
            'quantity': {'type': 'integer', 'required': True, 'min': 1}
        })
        def create_order():
            data = request.get_json()
            return {'order_id': '123'}
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger.info(f"🔵 VALIDATE_REQUEST: Decorator called for {request.method} {request.path}")

            if request.method not in ['POST', 'PUT', 'PATCH']:
                logger.info(f"🔵 VALIDATE_REQUEST: Skipping validation for {request.method}")
                return f(*args, **kwargs)

            data = request.get_json()
            logger.info(f"🔵 VALIDATE_REQUEST: Request data exists: {bool(data)}")

            if not data:
                logger.warning("🔵 VALIDATE_REQUEST: No request body")
                return jsonify({
                    'success': False,
                    'error': 'Request body is required',
                    'code': 'MISSING_BODY'
                }), 400

            logger.info(f"🔵 VALIDATE_REQUEST: Validating against schema with {len(schema)} fields")

            # Валідація схеми
            errors = []

            for field, rules in schema.items():
                logger.info(f"🔵 VALIDATE_REQUEST: Validating field '{field}'")

                # Перевірка обов'язкових полів
                if rules.get('required', False) and field not in data:
                    errors.append(f"Field '{field}' is required")
                    logger.warning(f"🔵 VALIDATE_REQUEST: Required field '{field}' is missing")
                    continue

                if field in data:
                    value = data[field]
                    field_type = rules.get('type')
                    logger.info(
                        f"🔵 VALIDATE_REQUEST: Field '{field}' type check: expected={field_type}, actual={type(value).__name__}")

                    # Перевірка типу
                    if field_type == 'integer':
                        try:
                            value = int(value)
                            data[field] = value
                        except:
                            errors.append(f"Field '{field}' must be an integer")
                            continue
                    elif field_type == 'float':
                        try:
                            value = float(value)
                            data[field] = value
                        except:
                            errors.append(f"Field '{field}' must be a number")
                            continue
                    elif field_type == 'string':
                        if not isinstance(value, str):
                            errors.append(f"Field '{field}' must be a string")
                            continue
                    elif field_type == 'boolean':
                        if not isinstance(value, bool):
                            errors.append(f"Field '{field}' must be a boolean")
                            continue

                    # Перевірка мін/макс для чисел
                    if field_type in ['integer', 'float']:
                        if 'min' in rules and value < rules['min']:
                            errors.append(f"Field '{field}' must be >= {rules['min']}")
                        if 'max' in rules and value > rules['max']:
                            errors.append(f"Field '{field}' must be <= {rules['max']}")

                    # Перевірка довжини для строк
                    if field_type == 'string':
                        if 'min_length' in rules and len(value) < rules['min_length']:
                            errors.append(f"Field '{field}' must be at least {rules['min_length']} characters")
                        if 'max_length' in rules and len(value) > rules['max_length']:
                            errors.append(f"Field '{field}' must be at most {rules['max_length']} characters")

            if errors:
                logger.warning(f"🔵 VALIDATE_REQUEST: Validation failed with {len(errors)} errors")
                return jsonify({
                    'success': False,
                    'error': 'Validation failed',
                    'code': 'VALIDATION_ERROR',
                    'errors': errors
                }), 400

            logger.info("🔵 VALIDATE_REQUEST: Validation passed")
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Логування при імпорті модуля
logger.info(
    "🔵 DECORATORS: Module loaded, decorators available: jwt_required, admin_required, optional_jwt, rate_limit, validate_request")