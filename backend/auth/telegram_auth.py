# backend/auth/telegram_auth.py
"""
TeleBoost Telegram Auth
Перевірка та валідація Telegram Web App даних
FIXED: Додано конвертацію telegram_id в string та детальне логування
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
        logger.info(f"📋 Verifying init_data length: {len(init_data)}")
        logger.debug(f"📋 Init data preview: {init_data[:100]}...")

        # Парсимо init data
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
        logger.debug(f"📋 Parsed data keys: {list(parsed_data.keys())}")

        # Отримуємо та видаляємо hash
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            logger.error("❌ No hash in init data")
            return False, None

        logger.debug(f"📋 Received hash: {received_hash}")

        # Створюємо data-check-string
        data_check_array = []
        for key in sorted(parsed_data.keys()):
            data_check_array.append(f"{key}={parsed_data[key]}")
        data_check_string = '\n'.join(data_check_array)

        logger.debug(f"📋 Data check string length: {len(data_check_string)}")

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

        logger.debug(f"📋 Calculated hash: {calculated_hash}")

        # Порівнюємо хеші
        if not hmac.compare_digest(received_hash, calculated_hash):
            logger.error(f"❌ Hash mismatch: expected {calculated_hash}, got {received_hash}")
            return False, None

        logger.info("✅ Hash verified successfully")

        # Перевіряємо auth_date (не старше 24 годин)
        auth_date = parsed_data.get('auth_date')
        if auth_date:
            try:
                auth_timestamp = int(auth_date)
                current_timestamp = int(time.time())

                if current_timestamp - auth_timestamp > 86400:  # 24 години
                    logger.error(f"❌ Init data is too old: {current_timestamp - auth_timestamp} seconds")
                    return False, None

                logger.info(f"✅ Auth date is valid: {current_timestamp - auth_timestamp} seconds old")
            except ValueError:
                logger.error(f"❌ Invalid auth_date format: {auth_date}")
                return False, None

        # Парсимо user data
        user_json_str = parsed_data.get('user', '{}')
        logger.debug(f"📋 Raw user JSON: {user_json_str}")

        user_data = parse_user_data(user_json_str)
        if not user_data:
            logger.error("❌ Invalid user data")
            return False, None

        # Додаємо додаткові дані
        user_data['auth_date'] = auth_date
        user_data['start_param'] = parsed_data.get('start_param', '')
        user_data['chat_instance'] = parsed_data.get('chat_instance', '')
        user_data['chat_type'] = parsed_data.get('chat_type', '')

        logger.info(f"✅ Telegram auth successful for user {user_data.get('id')} ({user_data.get('first_name')})")
        return True, user_data

    except Exception as e:
        logger.error(f"❌ Telegram auth error: {e}", exc_info=True)
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
        # Декодуємо URL encoding якщо є
        user_json = unquote(user_json)
        logger.debug(f"📋 Decoded user JSON: {user_json}")

        # Парсимо JSON
        user_data = json.loads(user_json)
        logger.debug(f"📋 Parsed user data: {json.dumps(user_data, indent=2)}")

        # Перевіряємо обов'язкові поля
        if 'id' not in user_data:
            logger.error("❌ No 'id' in user data")
            return None

        # КРИТИЧНО: Логуємо тип ID який приходить від Telegram
        original_id = user_data['id']
        original_type = type(original_id)
        logger.info(f"📊 Original Telegram ID type: {original_type}, value: {original_id}")

        # ВАЖЛИВО: Конвертуємо ID в string
        user_data['id'] = str(user_data['id'])
        logger.info(f"✅ Converted Telegram ID to string: {user_data['id']}")

        # Нормалізуємо дані
        normalized = {
            'id': user_data['id'],  # Вже string
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

        # Логуємо всі типи для діагностики
        logger.debug("📊 Normalized data types:")
        for key, value in normalized.items():
            logger.debug(f"   {key}: {type(value).__name__} = {value}")

        return normalized

    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error in user data: {e}")
        logger.error(f"   Raw JSON: {user_json}")
        return None
    except Exception as e:
        logger.error(f"❌ Error parsing user data: {e}", exc_info=True)
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

        logger.debug(f"📋 Start param: {start_param}")

        # start_param може містити реферальний код
        # Наприклад: start_param=ref_ABC12345
        if start_param.startswith('ref_'):
            referral_code = start_param[4:]  # Видаляємо префікс 'ref_'
            logger.info(f"✅ Found referral code: {referral_code}")
            return referral_code

        # Або просто код
        if len(start_param) >= 6:
            logger.info(f"✅ Found referral code: {start_param}")
            return start_param

        return None

    except Exception as e:
        logger.error(f"❌ Error extracting referral code: {e}")
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
            logger.error(f"❌ Missing required field: {field}")
            return False

    # Додатково перевіряємо initDataUnsafe якщо немає initData
    if not request_data.get('initData') and request_data.get('initDataUnsafe'):
        logger.warning("⚠️ No initData but has initDataUnsafe - possible browser/debug mode")
        # В production це має бути заборонено, але для тестування можна дозволити
        if config.DEBUG:
            return True

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


# Додаткова функція для діагностики
def diagnose_init_data(init_data: str) -> Dict:
    """
    Діагностика init_data для debugging

    Args:
        init_data: URL-encoded init data

    Returns:
        Діагностична інформація
    """
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))

        diagnosis = {
            'length': len(init_data),
            'has_hash': 'hash' in parsed,
            'has_user': 'user' in parsed,
            'has_auth_date': 'auth_date' in parsed,
            'fields': list(parsed.keys()),
            'user_preview': None,
        }

        if 'user' in parsed:
            try:
                user_json = unquote(parsed['user'])
                user_data = json.loads(user_json)
                diagnosis['user_preview'] = {
                    'id': user_data.get('id'),
                    'id_type': type(user_data.get('id')).__name__,
                    'username': user_data.get('username'),
                    'first_name': user_data.get('first_name'),
                }
            except:
                diagnosis['user_preview'] = 'Failed to parse'

        return diagnosis

    except Exception as e:
        return {'error': str(e)}


# Експорт функцій
__all__ = [
    'verify_telegram_data',
    'parse_user_data',
    'extract_referral_code',
    'create_webapp_link',
    'validate_webapp_request',
    'get_user_display_name',
    'is_premium_user',
    'diagnose_init_data',
]