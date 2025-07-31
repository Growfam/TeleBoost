# backend/auth/decorators.py
"""
TeleBoost Auth Decorators
Декоратори для авторизації
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
        # Отримуємо токен з заголовка
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({
                'success': False,
                'error': 'Authorization header missing',
                'code': 'AUTH_HEADER_MISSING'
            }), 401

        # Перевіряємо формат Bearer <token>
        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != 'Bearer':
            return jsonify({
                'success': False,
                'error': 'Invalid authorization header format',
                'code': 'INVALID_AUTH_HEADER'
            }), 401

        token = parts[1]

        # Декодуємо токен
        is_valid, payload = decode_token(token)

        if not is_valid or not payload:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token',
                'code': 'INVALID_TOKEN'
            }), 401

        # Перевіряємо тип токена
        if payload.get('type') != 'access':
            return jsonify({
                'success': False,
                'error': 'Invalid token type',
                'code': 'INVALID_TOKEN_TYPE'
            }), 401

        # Отримуємо користувача
        user = User.get_by_id(payload['user_id'])

        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found',
                'code': 'USER_NOT_FOUND'
            }), 404

        # Перевіряємо чи активний користувач
        if not user.is_active:
            return jsonify({
                'success': False,
                'error': 'User account is inactive',
                'code': 'USER_INACTIVE'
            }), 403

        # Зберігаємо користувача в g для доступу в route
        g.current_user = user
        g.jwt_payload = payload

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
        # Перевіряємо чи є current_user (має бути встановлено jwt_required)
        if not hasattr(g, 'current_user') or not g.current_user:
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401

        # Перевіряємо чи є адміном
        if not g.current_user.is_admin:
            return jsonify({
                'success': False,
                'error': 'Admin access required',
                'code': 'ADMIN_REQUIRED'
            }), 403

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
        # Ініціалізуємо як None
        g.current_user = None
        g.jwt_payload = None

        # Отримуємо токен з заголовка
        auth_header = request.headers.get('Authorization')

        if auth_header:
            # Якщо є заголовок - намагаємося валідувати
            parts = auth_header.split()

            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]

                # Декодуємо токен
                is_valid, payload = decode_token(token)

                if is_valid and payload and payload.get('type') == 'access':
                    # Отримуємо користувача
                    user = User.get_by_id(payload['user_id'])

                    if user and user.is_active:
                        g.current_user = user
                        g.jwt_payload = payload

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
            from backend.utils.redis_client import redis_client
            from backend.utils.constants import CACHE_KEYS

            # Визначаємо ідентифікатор користувача
            if hasattr(g, 'current_user') and g.current_user:
                identifier = g.current_user.telegram_id
            else:
                # Для анонімних використовуємо IP
                identifier = request.remote_addr

            # Формуємо ключ для rate limit
            endpoint = request.endpoint or 'unknown'
            rate_key = CACHE_KEYS.format(
                CACHE_KEYS.RATE_LIMIT,
                user_id=identifier,
                endpoint=endpoint
            )

            # Перевіряємо кількість викликів
            current_calls = redis_client.get(rate_key, data_type='int')

            if current_calls is None:
                # Перший виклик
                redis_client.set(rate_key, 1, ttl=period)
                current_calls = 1
            else:
                if current_calls >= calls:
                    # Перевищено ліміт
                    ttl = redis_client.ttl(rate_key)

                    return jsonify({
                        'success': False,
                        'error': f'Rate limit exceeded. Max {calls} requests per {period} seconds',
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'retry_after': ttl
                    }), 429

                # Інкрементуємо лічильник
                redis_client.incr(rate_key)
                current_calls += 1

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
            response.headers['X-RateLimit-Reset'] = str(redis_client.ttl(rate_key))

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
            if request.method not in ['POST', 'PUT', 'PATCH']:
                return f(*args, **kwargs)

            data = request.get_json()

            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Request body is required',
                    'code': 'MISSING_BODY'
                }), 400

            # Валідація схеми
            errors = []

            for field, rules in schema.items():
                # Перевірка обов'язкових полів
                if rules.get('required', False) and field not in data:
                    errors.append(f"Field '{field}' is required")
                    continue

                if field in data:
                    value = data[field]
                    field_type = rules.get('type')

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
                return jsonify({
                    'success': False,
                    'error': 'Validation failed',
                    'code': 'VALIDATION_ERROR',
                    'errors': errors
                }), 400

            return f(*args, **kwargs)

        return decorated_function

    return decorator