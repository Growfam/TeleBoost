# backend/auth/telegram_auth.py
"""
TeleBoost Telegram Auth
Перевірка та валідація Telegram Web App даних
ВИПРАВЛЕНА ВЕРСІЯ
"""
import hashlib
import hmac
import json
import time
import logging
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qsl, unquote

from backend.config import config

logger = logging.getLogger(__name__)


def verify_telegram_data(init_data: str) -> Tuple[bool, Optional[Dict]]:
    """
    Перевірка підпису Telegram Web App InitData

    Args:
        init_data: URL-encoded init data від Telegram

    Returns:
        (is_valid, user_data) - результат перевірки та дані користувача
    """
    try:
        logger.info(f"🔐 Received initData length: {len(init_data)}")
        logger.info(f"🔐 InitData preview: {init_data[:100]}...")

        # Парсимо init data
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
        logger.info(f"🔐 Parsed data keys: {list(parsed_data.keys())}")

        # Отримуємо та видаляємо hash
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            logger.error("🔐 No hash in init data")
            # Спробуємо без перевірки hash для тестування
            if config.DEBUG and 'user' in parsed_data:
                logger.warning("🔐 DEBUG MODE: Skipping hash verification")
                user_data = parse_user_data(parsed_data.get('user', '{}'))
                if user_data:
                    user_data['auth_date'] = parsed_data.get('auth_date', str(int(time.time())))
                    user_data['start_param'] = parsed_data.get('start_param', '')
                    return True, user_data
            return False, None

        logger.info(f"🔐 Received hash: {received_hash[:20]}...")

        # Створюємо data-check-string
        data_check_array = []
        for key in sorted(parsed_data.keys()):
            value = parsed_data[key]
            data_check_array.append(f"{key}={value}")

        data_check_string = '\n'.join(data_check_array)
        logger.info(f"🔐 Data check string length: {len(data_check_string)}")
        logger.info(f"🔐 Data check string preview: {data_check_string[:100]}...")

        # Створюємо secret key
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=config.TELEGRAM_BOT_TOKEN.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()

        # Обчислюємо hash
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        logger.info(f"🔐 Calculated hash: {calculated_hash[:20]}...")

        # Порівнюємо хеші
        if not hmac.compare_digest(received_hash, calculated_hash):
            logger.error(f"🔐 Hash mismatch!")
            logger.error(f"🔐 Expected: {calculated_hash}")
            logger.error(f"🔐 Received: {received_hash}")

            # В DEBUG режимі дозволяємо без валідного хешу
            if config.DEBUG and 'user' in parsed_data:
                logger.warning("🔐 DEBUG MODE: Ignoring hash mismatch")
                user_data = parse_user_data(parsed_data.get('user', '{}'))
                if user_data:
                    user_data['auth_date'] = parsed_data.get('auth_date', str(int(time.time())))
                    user_data['start_param'] = parsed_data.get('start_param', '')
                    return True, user_data
            return False, None

        # Перевіряємо auth_date (не старше 24 годин)
        auth_date = parsed_data.get('auth_date')
        if auth_date:
            try:
                auth_timestamp = int(auth_date)
                current_timestamp = int(time.time())
                age_seconds = current_timestamp - auth_timestamp

                logger.info(f"🔐 Auth date age: {age_seconds} seconds")

                if age_seconds > 86400:  # 24 години
                    logger.error(f"🔐 Init data is too old: {age_seconds} seconds")
                    # В DEBUG режимі ігноруємо старі дані
                    if not config.DEBUG:
                        return False, None
                    logger.warning("🔐 DEBUG MODE: Ignoring old auth_date")
            except ValueError:
                logger.error(f"🔐 Invalid auth_date format: {auth_date}")

        # Парсимо user data
        user_data = parse_user_data(parsed_data.get('user', '{}'))
        if not user_data:
            logger.error("🔐 Invalid user data")
            return False, None

        # Додаємо додаткові дані
        user_data['auth_date'] = auth_date
        user_data['start_param'] = parsed_data.get('start_param', '')
        user_data['chat_instance'] = parsed_data.get('chat_instance', '')
        user_data['chat_type'] = parsed_data.get('chat_type', '')

        logger.info(f"🔐 Telegram auth successful for user {user_data.get('id')}")
        return True, user_data

    except Exception as e:
        logger.error(f"🔐 Telegram auth error: {type(e).__name__}: {str(e)}", exc_info=True)
        return False, None


def parse_user_data(user_json: str) -> Optional[Dict]:
    """
    Парсинг JSON даних користувача

    Args:
        user_json: JSON строка з даними користувача

    Returns:
        Словник з даними або None
    """
    try:
        logger.info(f"🔐 Parsing user data: {user_json[:100]}...")

        # Декодуємо URL encoding якщо є
        user_json = unquote(user_json)

        # Парсимо JSON
        user_data = json.loads(user_json)
        logger.info(f"🔐 Parsed user data keys: {list(user_data.keys())}")

        # Перевіряємо обов'язкові поля
        if 'id' not in user_data:
            logger.error("🔐 No 'id' field in user data")
            return None

        # Нормалізуємо дані
        normalized = {
            'id': str(user_data['id']),  # Завжди string
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', ''),
            'username': user_data.get('username', ''),
            'language_code': user_data.get('language_code', 'en'),
            'is_bot': user_data.get('is_bot', False),
            'is_premium': user_data.get('is_premium', False),
            'added_to_attachment_menu': user_data.get('added_to_attachment_menu', False),
            'allows_write_to_pm': user_data.get('allows_write_to_pm', True),
            'photo_url': user_data.get('photo_url', ''),
        }

        logger.info(f"🔐 Normalized user: id={normalized['id']}, username={normalized['username']}")

        return normalized

    except json.JSONDecodeError as e:
        logger.error(f"🔐 JSON decode error: {e}")
        logger.error(f"🔐 Invalid JSON: {user_json}")
        return None
    except Exception as e:
        logger.error(f"🔐 Error parsing user data: {type(e).__name__}: {str(e)}")
        return None


def extract_referral_code(init_data: str) -> Optional[str]:
    """
    Витягти реферальний код з start_param

    Args:
        init_data: URL-encoded init data

    Returns:
        Реферальний код або None
    """
    try:
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
        start_param = parsed_data.get('start_param', '')

        logger.info(f"🔐 Start param: {start_param}")

        # start_param може містити реферальний код
        # Наприклад: start_param=ref_ABC12345
        if start_param.startswith('ref_'):
            return start_param[4:]  # Видаляємо префікс 'ref_'

        # Або просто код
        if len(start_param) >= 6:
            return start_param

        return None

    except Exception as e:
        logger.error(f"🔐 Error extracting referral code: {e}")
        return None


def create_webapp_link(ref_code: Optional[str] = None) -> str:
    """
    Створити посилання на Web App

    Args:
        ref_code: Реферальний код (опціонально)

    Returns:
        Посилання на бота з Web App
    """
    base_url = f"https://t.me/{config.BOT_USERNAME}"

    if ref_code:
        return f"{base_url}?start=ref_{ref_code}"

    return base_url


def validate_webapp_request(request_data: Dict) -> bool:
    """
    Валідація запиту від Web App

    Args:
        request_data: Дані запиту

    Returns:
        True якщо валідний
    """
    # Перевіряємо обов'язкові поля
    required_fields = ['initData']

    for field in required_fields:
        if field not in request_data:
            logger.error(f"🔐 Missing required field: {field}")
            return False

    # Перевіряємо підпис
    is_valid, _ = verify_telegram_data(request_data['initData'])

    return is_valid


def get_user_display_name(user_data: Dict) -> str:
    """
    Отримати ім'я користувача для відображення

    Args:
        user_data: Дані користувача

    Returns:
        Ім'я для відображення
    """
    # Пріоритет: username > first_name + last_name > first_name > id
    if user_data.get('username'):
        return f"@{user_data['username']}"

    first_name = user_data.get('first_name', '')
    last_name = user_data.get('last_name', '')

    if first_name and last_name:
        return f"{first_name} {last_name}"
    elif first_name:
        return first_name
    else:
        return f"User {user_data.get('id', 'Unknown')}"


def is_premium_user(user_data: Dict) -> bool:
    """
    Перевірка чи є користувач Premium

    Args:
        user_data: Дані користувача

    Returns:
        True якщо Premium
    """
    return user_data.get('is_premium', False)


# Функція для тестування
def test_verify_telegram_data():
    """Тестова функція для перевірки роботи"""
    # Приклад тестових даних
    test_data = 'auth_date=1234567890&hash=test_hash&user={"id":123456789,"first_name":"Test","username":"testuser"}'

    logger.info("🔐 Running test verification...")
    is_valid, user_data = verify_telegram_data(test_data)

    logger.info(f"🔐 Test result: valid={is_valid}, user_data={user_data}")
    return is_valid, user_data