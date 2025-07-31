# backend/auth/jwt_handler.py
"""
TeleBoost JWT Handler
Створення та валідація JWT токенів
"""
import jwt
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, Any

from backend.config import config
from backend.utils.redis_client import redis_client

logger = logging.getLogger(__name__)


def create_access_token(user_data: Dict[str, Any]) -> str:
    """
    Створити access token

    Args:
        user_data: Дані користувача (id, telegram_id, etc.)

    Returns:
        JWT access token
    """
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())  # JWT ID для можливості revoke

    payload = {
        # Стандартні claims
        'iat': now,
        'exp': now + config.JWT_ACCESS_TOKEN_EXPIRES,
        'jti': jti,
        'type': 'access',

        # Кастомні claims
        'user_id': user_data['id'],  # UUID з БД
        'telegram_id': user_data['telegram_id'],  # Telegram ID
        'username': user_data.get('username', ''),
        'is_admin': user_data.get('is_admin', False),
        'is_active': user_data.get('is_active', True),
    }

    token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

    # Зберігаємо JTI в Redis для можливості revoke
    redis_client.set(
        f"jwt:{jti}",
        'valid',
        ttl=int(config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds())
    )

    logger.info(f"Created access token for user {user_data['telegram_id']}")

    return token


def create_refresh_token(user_data: Dict[str, Any]) -> str:
    """
    Створити refresh token

    Args:
        user_data: Дані користувача

    Returns:
        JWT refresh token
    """
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())

    payload = {
        # Стандартні claims
        'iat': now,
        'exp': now + config.JWT_REFRESH_TOKEN_EXPIRES,
        'jti': jti,
        'type': 'refresh',

        # Мінімальні дані для refresh
        'user_id': user_data['id'],
        'telegram_id': user_data['telegram_id'],
    }

    token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

    # Зберігаємо JTI в Redis
    redis_client.set(
        f"jwt:refresh:{jti}",
        'valid',
        ttl=int(config.JWT_REFRESH_TOKEN_EXPIRES.total_seconds())
    )

    logger.info(f"Created refresh token for user {user_data['telegram_id']}")

    return token


def create_tokens_pair(user_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Створити пару токенів (access + refresh)

    Args:
        user_data: Дані користувача

    Returns:
        Словник з токенами
    """
    return {
        'access_token': create_access_token(user_data),
        'refresh_token': create_refresh_token(user_data),
        'token_type': 'Bearer',
        'expires_in': int(config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds()),
    }


def decode_token(token: str, verify_exp: bool = True) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Декодувати та валідувати JWT токен

    Args:
        token: JWT токен
        verify_exp: Чи перевіряти термін дії

    Returns:
        (is_valid, payload) - результат валідації та дані
    """
    try:
        # Декодуємо токен
        payload = jwt.decode(
            token,
            config.JWT_SECRET,
            algorithms=[config.JWT_ALGORITHM],
            options={"verify_exp": verify_exp}
        )

        # Перевіряємо JTI (чи не revoked)
        jti = payload.get('jti')
        if jti:
            token_type = payload.get('type', 'access')
            redis_key = f"jwt:{jti}" if token_type == 'access' else f"jwt:refresh:{jti}"

            if not redis_client.exists(redis_key):
                logger.warning(f"Token {jti} has been revoked")
                return False, None

        # Перевіряємо обов'язкові поля
        required_fields = ['user_id', 'telegram_id', 'type']
        for field in required_fields:
            if field not in payload:
                logger.error(f"Missing required field in token: {field}")
                return False, None

        return True, payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return False, None
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        return False, None


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """
    Оновити access token використовуючи refresh token

    Args:
        refresh_token: Refresh token

    Returns:
        Новий access token або None
    """
    # Декодуємо refresh token
    is_valid, payload = decode_token(refresh_token)

    if not is_valid or not payload:
        return None

    # Перевіряємо тип токена
    if payload.get('type') != 'refresh':
        logger.error("Not a refresh token")
        return None

    # Отримуємо користувача з БД для актуальних даних
    from backend.auth.models import User
    user = User.get_by_id(payload['user_id'])

    if not user:
        logger.error(f"User {payload['user_id']} not found")
        return None

    if not user.is_active:
        logger.warning(f"User {user.telegram_id} is not active")
        return None

    # Створюємо новий access token
    user_data = user.to_dict()
    new_access_token = create_access_token(user_data)

    return {
        'access_token': new_access_token,
        'token_type': 'Bearer',
        'expires_in': int(config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds()),
    }


def revoke_token(token: str) -> bool:
    """
    Відкликати токен (зробити недійсним)

    Args:
        token: JWT токен

    Returns:
        True якщо успішно
    """
    try:
        # Декодуємо без перевірки терміну дії
        is_valid, payload = decode_token(token, verify_exp=False)

        if not payload:
            return False

        jti = payload.get('jti')
        if not jti:
            return False

        # Видаляємо з Redis
        token_type = payload.get('type', 'access')
        redis_key = f"jwt:{jti}" if token_type == 'access' else f"jwt:refresh:{jti}"

        redis_client.delete(redis_key)

        logger.info(f"Revoked token {jti}")
        return True

    except Exception as e:
        logger.error(f"Error revoking token: {e}")
        return False


def get_current_user_id(token: str) -> Optional[str]:
    """
    Швидко отримати user_id з токена

    Args:
        token: JWT токен

    Returns:
        user_id або None
    """
    is_valid, payload = decode_token(token)

    if is_valid and payload:
        return payload.get('user_id')

    return None


def is_token_expired(token: str) -> bool:
    """
    Перевірити чи токен прострочений

    Args:
        token: JWT токен

    Returns:
        True якщо прострочений
    """
    try:
        jwt.decode(
            token,
            config.JWT_SECRET,
            algorithms=[config.JWT_ALGORITHM],
            options={"verify_exp": True}
        )
        return False
    except jwt.ExpiredSignatureError:
        return True
    except:
        return True


def get_token_remaining_time(token: str) -> Optional[int]:
    """
    Отримати час що залишився до закінчення токена

    Args:
        token: JWT токен

    Returns:
        Секунди до закінчення або None
    """
    is_valid, payload = decode_token(token, verify_exp=False)

    if not payload:
        return None

    exp = payload.get('exp')
    if not exp:
        return None

    remaining = exp - datetime.now(timezone.utc).timestamp()

    return int(remaining) if remaining > 0 else 0