# backend/payments/utils/security.py
"""
TeleBoost Payment Security Utils
Функції безпеки для платіжної системи
"""
import hashlib
import hmac
import json
import time
import secrets
import logging
from typing import Dict, Any, Optional, Union
from urllib.parse import parse_qs

from backend.config import config

logger = logging.getLogger(__name__)


class PaymentSecurityError(Exception):
    """Помилка безпеки платежів"""
    pass


def verify_cryptobot_signature(body: Union[str, bytes], signature: str) -> bool:
    """
    Перевірка підпису CryptoBot

    Args:
        body: Тіло запиту
        signature: Підпис з заголовка X-Crypto-Bot-Api-Signature

    Returns:
        True якщо підпис валідний
    """
    try:
        if isinstance(body, str):
            body = body.encode('utf-8')

        # Обчислюємо очікуваний підпис
        expected_signature = hmac.new(
            key=config.CRYPTOBOT_TOKEN.encode('utf-8'),
            msg=body,
            digestmod=hashlib.sha256
        ).hexdigest()

        # Безпечне порівняння
        return hmac.compare_digest(signature, expected_signature)

    except Exception as e:
        logger.error(f"Error verifying CryptoBot signature: {e}")
        return False


def verify_nowpayments_signature(body: Union[str, bytes], signature: str) -> bool:
    """
    Перевірка підпису NOWPayments IPN

    Args:
        body: Тіло запиту (JSON)
        signature: Підпис з заголовка X-Nowpayments-Sig

    Returns:
        True якщо підпис валідний
    """
    try:
        # Парсимо JSON і сортуємо ключі
        if isinstance(body, bytes):
            body = body.decode('utf-8')

        data = json.loads(body)
        sorted_json = json.dumps(data, sort_keys=True, separators=(',', ':'))

        # Обчислюємо очікуваний підпис
        expected_signature = hmac.new(
            key=config.NOWPAYMENTS_IPN_SECRET.encode('utf-8'),
            msg=sorted_json.encode('utf-8'),
            digestmod=hashlib.sha512
        ).hexdigest()

        # Безпечне порівняння (case-insensitive для NOWPayments)
        return hmac.compare_digest(signature.lower(), expected_signature.lower())

    except Exception as e:
        logger.error(f"Error verifying NOWPayments signature: {e}")
        return False


def generate_payment_token(payment_id: str, expires_in: int = 3600) -> str:
    """
    Генерація токена для безпечного доступу до платежу

    Args:
        payment_id: ID платежу
        expires_in: Час життя токена в секундах

    Returns:
        Токен
    """
    # Створюємо токен з payment_id та timestamp
    timestamp = int(time.time() + expires_in)
    data = f"{payment_id}:{timestamp}"

    # Підписуємо дані
    signature = hmac.new(
        key=config.JWT_SECRET.encode('utf-8'),
        msg=data.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

    return f"{data}:{signature}"


def verify_payment_token(token: str) -> Optional[str]:
    """
    Перевірка токена платежу

    Args:
        token: Токен

    Returns:
        payment_id якщо токен валідний, None якщо ні
    """
    try:
        # Розбираємо токен
        parts = token.split(':')
        if len(parts) != 3:
            return None

        payment_id, timestamp_str, signature = parts
        timestamp = int(timestamp_str)

        # Перевіряємо термін дії
        if timestamp < int(time.time()):
            logger.warning(f"Payment token expired: {payment_id}")
            return None

        # Перевіряємо підпис
        data = f"{payment_id}:{timestamp_str}"
        expected_signature = hmac.new(
            key=config.JWT_SECRET.encode('utf-8'),
            msg=data.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            logger.warning(f"Invalid payment token signature: {payment_id}")
            return None

        return payment_id

    except Exception as e:
        logger.error(f"Error verifying payment token: {e}")
        return None


def generate_idempotency_key() -> str:
    """
    Генерація унікального ключа для ідемпотентних запитів

    Returns:
        Ключ ідемпотентності
    """
    return secrets.token_urlsafe(32)


def hash_sensitive_data(data: str) -> str:
    """
    Хешування чутливих даних для логування

    Args:
        data: Чутливі дані

    Returns:
        Хеш даних
    """
    return hashlib.sha256(data.encode('utf-8')).hexdigest()[:16]


def sanitize_payment_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Очищення платіжних даних від чутливої інформації

    Args:
        data: Дані платежу

    Returns:
        Очищені дані
    """
    sensitive_fields = [
        'card_number', 'cvv', 'pin', 'password',
        'private_key', 'secret', 'token', 'api_key'
    ]

    sanitized = data.copy()

    for field in sensitive_fields:
        if field in sanitized:
            # Маскуємо чутливі дані
            value = str(sanitized[field])
            if len(value) > 8:
                sanitized[field] = f"{value[:4]}...{value[-4:]}"
            else:
                sanitized[field] = "***"

    return sanitized


def validate_webhook_ip(ip_address: str, provider: str) -> bool:
    """
    Перевірка IP адреси webhook

    Args:
        ip_address: IP адреса запиту
        provider: Провайдер платежів

    Returns:
        True якщо IP дозволений
    """
    # IP адреси провайдерів (приклад)
    allowed_ips = {
        'cryptobot': [
            # CryptoBot IPs (потрібно уточнити в документації)
            '91.108.4.0/22',
            '91.108.8.0/22',
            '91.108.12.0/22',
            '91.108.16.0/22',
            '91.108.20.0/22',
            '149.154.160.0/20',
            '149.154.164.0/22',
        ],
        'nowpayments': [
            # NOWPayments IPs (потрібно уточнити в документації)
            # Зазвичай вони не публікують фіксований список
        ]
    }

    provider_ips = allowed_ips.get(provider, [])

    # Якщо немає списку IP - дозволяємо всі (небезпечно для production!)
    if not provider_ips:
        logger.warning(f"No IP whitelist for provider {provider}")
        return True

    # Перевіряємо чи IP в дозволених діапазонах
    from ipaddress import ip_address as parse_ip, ip_network

    try:
        request_ip = parse_ip(ip_address)

        for ip_range in provider_ips:
            if request_ip in ip_network(ip_range):
                return True

        logger.warning(f"Webhook from unauthorized IP: {ip_address} for {provider}")
        return False

    except Exception as e:
        logger.error(f"Error validating webhook IP: {e}")
        return False


def encrypt_payment_data(data: Dict[str, Any]) -> str:
    """
    Шифрування платіжних даних для зберігання

    Args:
        data: Дані для шифрування

    Returns:
        Зашифровані дані (base64)
    """
    # TODO: Implement actual encryption using cryptography library
    # Наразі просто конвертуємо в JSON
    return json.dumps(data)


def decrypt_payment_data(encrypted_data: str) -> Dict[str, Any]:
    """
    Розшифрування платіжних даних

    Args:
        encrypted_data: Зашифровані дані

    Returns:
        Розшифровані дані
    """
    # TODO: Implement actual decryption
    # Наразі просто парсимо JSON
    return json.loads(encrypted_data)


def generate_webhook_secret(provider: str) -> str:
    """
    Генерація секрету для webhook

    Args:
        provider: Провайдер платежів

    Returns:
        Секрет для webhook
    """
    # Генеруємо унікальний секрет для кожного провайдера
    return secrets.token_urlsafe(64)


def validate_payment_request(request_data: Dict[str, Any],
                             expected_fields: list) -> tuple[bool, Optional[str]]:
    """
    Валідація запиту на створення платежу

    Args:
        request_data: Дані запиту
        expected_fields: Очікувані поля

    Returns:
        (is_valid, error_message)
    """
    # Перевіряємо наявність обов'язкових полів
    for field in expected_fields:
        if field not in request_data:
            return False, f"Missing required field: {field}"

    # Перевіряємо на підозрілі поля
    suspicious_fields = ['__proto__', 'constructor', 'prototype']
    for field in suspicious_fields:
        if field in request_data:
            logger.warning(f"Suspicious field in payment request: {field}")
            return False, "Invalid request data"

    return True, None


def rate_limit_payment_requests(user_id: str, limit: int = 10,
                                window: int = 3600) -> bool:
    """
    Обмеження кількості платіжних запитів

    Args:
        user_id: ID користувача
        limit: Максимальна кількість запитів
        window: Часове вікно в секундах

    Returns:
        True якщо дозволено, False якщо перевищено ліміт
    """
    from backend.utils.redis_client import redis_client

    key = f"payment_rate_limit:{user_id}"

    try:
        # Отримуємо поточний лічильник
        current = redis_client.get(key, data_type='int') or 0

        if current >= limit:
            return False

        # Інкрементуємо лічильник
        redis_client.incr(key)

        # Встановлюємо TTL якщо це перший запит
        if current == 0:
            redis_client.expire(key, window)

        return True

    except Exception as e:
        logger.error(f"Error checking payment rate limit: {e}")
        # У разі помилки - дозволяємо запит
        return True


def log_security_event(event_type: str, details: Dict[str, Any]) -> None:
    """
    Логування подій безпеки

    Args:
        event_type: Тип події
        details: Деталі події
    """
    # Очищаємо чутливі дані
    safe_details = sanitize_payment_data(details)

    logger.warning(f"SECURITY EVENT: {event_type}", extra={
        'event_type': event_type,
        'details': safe_details,
        'timestamp': time.time()
    })