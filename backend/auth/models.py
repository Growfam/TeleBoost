# backend/auth/models.py
"""
TeleBoost Auth Models
Моделі користувачів та сесій
"""
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List, Any

from backend.supabase_client import supabase
from backend.utils.redis_client import cache_user_data, get_cached_user_data, invalidate_user_cache
from backend.utils.formatters import generate_referral_code
from backend.utils.validators import validate_telegram_id

logger = logging.getLogger(__name__)


class User:
    """Модель користувача"""

    def __init__(self, data: Dict[str, Any]):
        """Ініціалізація з даних БД"""
        self.id = data.get('id')  # UUID
        self.telegram_id = data.get('telegram_id')  # String
        self.username = data.get('username', '')
        self.first_name = data.get('first_name', '')
        self.last_name = data.get('last_name', '')
        self.language_code = data.get('language_code', 'en')
        self.is_premium = data.get('is_premium', False)
        self.is_admin = data.get('is_admin', False)
        self.is_active = data.get('is_active', True)

        # Баланс та статистика
        self.balance = float(data.get('balance', 0))
        self.total_deposited = float(data.get('total_deposited', 0))
        self.total_withdrawn = float(data.get('total_withdrawn', 0))
        self.total_spent = float(data.get('total_spent', 0))

        # Реферальна система
        self.referral_code = data.get('referral_code')
        self.referred_by = data.get('referred_by')  # UUID реферера
        self.referral_earnings = float(data.get('referral_earnings', 0))

        # Дати
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
        self.last_login = data.get('last_login')

        # Додаткові дані
        self.photo_url = data.get('photo_url', '')
        self.settings = data.get('settings', {})

    @classmethod
    def create(cls, telegram_data: Dict[str, Any], referral_code: Optional[str] = None) -> Optional['User']:
        """
        Створити нового користувача

        Args:
            telegram_data: Дані від Telegram
            referral_code: Код реферала

        Returns:
            User об'єкт або None
        """
        try:
            # Валідація Telegram ID
            telegram_id = str(telegram_data.get('id', ''))
            if not validate_telegram_id(telegram_id):
                logger.error(f"Invalid telegram_id: {telegram_id}")
                return None

            # Перевіряємо чи немає вже такого користувача
            existing = cls.get_by_telegram_id(telegram_id)
            if existing:
                logger.warning(f"User with telegram_id {telegram_id} already exists")
                return existing

            # Знаходимо реферера якщо є код
            referred_by_id = None
            if referral_code:
                referrer = cls.get_by_referral_code(referral_code)
                if referrer:
                    referred_by_id = referrer.id
                    logger.info(f"User referred by {referrer.telegram_id}")

            # Генеруємо унікальний реферальний код
            new_referral_code = generate_referral_code(telegram_id)

            # Підготовка даних
            user_data = {
                'telegram_id': telegram_id,
                'username': telegram_data.get('username', ''),
                'first_name': telegram_data.get('first_name', ''),
                'last_name': telegram_data.get('last_name', ''),
                'language_code': telegram_data.get('language_code', 'en'),
                'is_premium': telegram_data.get('is_premium', False),
                'photo_url': telegram_data.get('photo_url', ''),
                'referral_code': new_referral_code,
                'referred_by': referred_by_id,
                'balance': 0,
                'settings': {
                    'notifications': True,
                    'language': telegram_data.get('language_code', 'en'),
                }
            }

            # Створюємо в БД
            created = supabase.create_user(user_data)
            if not created:
                logger.error("Failed to create user in database")
                return None

            user = cls(created)

            # Кешуємо
            cache_user_data(user.telegram_id, user.to_dict())

            logger.info(f"Created new user: {user.telegram_id}")

            # Нараховуємо реферальний бонус якщо є реферер
            if referrer:
                from backend.referrals.services import process_referral_bonus
                process_referral_bonus(referrer, user)

            return user

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    @classmethod
    def get_by_id(cls, user_id: str) -> Optional['User']:
        """Отримати користувача за ID (UUID)"""
        try:
            result = supabase.table('users').select('*').eq('id', user_id).single().execute()
            if result.data:
                return cls(result.data)
            return None
        except Exception as e:
            logger.error(f"Error getting user by id {user_id}: {e}")
            return None

    @classmethod
    def get_by_telegram_id(cls, telegram_id: str) -> Optional['User']:
        """Отримати користувача за Telegram ID"""
        try:
            # Спробуємо з кешу
            cached = get_cached_user_data(telegram_id)
            if cached:
                return cls(cached)

            # З БД
            user_data = supabase.get_user_by_telegram_id(telegram_id)
            if user_data:
                user = cls(user_data)
                # Кешуємо
                cache_user_data(telegram_id, user.to_dict())
                return user

            return None
        except Exception as e:
            logger.error(f"Error getting user by telegram_id {telegram_id}: {e}")
            return None

    @classmethod
    def get_by_referral_code(cls, referral_code: str) -> Optional['User']:
        """Отримати користувача за реферальним кодом"""
        try:
            result = supabase.table('users') \
                .select('*') \
                .eq('referral_code', referral_code) \
                .single() \
                .execute()

            if result.data:
                return cls(result.data)
            return None
        except Exception as e:
            logger.error(f"Error getting user by referral_code {referral_code}: {e}")
            return None

    def update(self, update_data: Dict[str, Any]) -> bool:
        """Оновити дані користувача"""
        try:
            # Фільтруємо дані які можна оновлювати
            allowed_fields = [
                'username', 'first_name', 'last_name', 'language_code',
                'photo_url', 'settings', 'last_login', 'is_active'
            ]

            filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}

            if not filtered_data:
                return True  # Нічого оновлювати

            # Оновлюємо в БД
            updated = supabase.update_user(self.id, filtered_data)
            if not updated:
                return False

            # Оновлюємо локальні дані
            for key, value in filtered_data.items():
                setattr(self, key, value)

            # Інвалідуємо кеш
            invalidate_user_cache(self.telegram_id)

            return True

        except Exception as e:
            logger.error(f"Error updating user {self.id}: {e}")
            return False

    def update_balance(self, amount: float, operation: str = 'add') -> bool:
        """Оновити баланс користувача"""
        try:
            success = supabase.update_user_balance(self.id, amount, operation)

            if success:
                if operation == 'add':
                    self.balance += amount
                else:
                    self.balance -= amount

                # Інвалідуємо кеш
                invalidate_user_cache(self.telegram_id)

            return success

        except Exception as e:
            logger.error(f"Error updating balance for user {self.id}: {e}")
            return False

    def get_display_name(self) -> str:
        """Отримати ім'я для відображення"""
        if self.username:
            return f"@{self.username}"
        elif self.first_name:
            full_name = self.first_name
            if self.last_name:
                full_name += f" {self.last_name}"
            return full_name
        else:
            return f"User {self.telegram_id}"

    def to_dict(self) -> Dict[str, Any]:
        """Конвертувати в словник"""
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'display_name': self.get_display_name(),
            'language_code': self.language_code,
            'is_premium': self.is_premium,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'balance': self.balance,
            'total_deposited': self.total_deposited,
            'total_withdrawn': self.total_withdrawn,
            'total_spent': self.total_spent,
            'referral_code': self.referral_code,
            'referred_by': self.referred_by,
            'referral_earnings': self.referral_earnings,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'last_login': self.last_login,
            'photo_url': self.photo_url,
            'settings': self.settings,
        }

    def to_public_dict(self) -> Dict[str, Any]:
        """Конвертувати в словник для публічного API (без чутливих даних)"""
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'display_name': self.get_display_name(),
            'language_code': self.language_code,
            'is_premium': self.is_premium,
            'balance': self.balance,
            'referral_code': self.referral_code,
            'photo_url': self.photo_url,
            'settings': self.settings,
        }


class UserSession:
    """Модель сесії користувача"""

    def __init__(self, data: Dict[str, Any]):
        """Ініціалізація з даних"""
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.access_token_jti = data.get('access_token_jti')
        self.refresh_token_jti = data.get('refresh_token_jti')
        self.ip_address = data.get('ip_address')
        self.user_agent = data.get('user_agent')
        self.created_at = data.get('created_at')
        self.expires_at = data.get('expires_at')
        self.is_active = data.get('is_active', True)

    @classmethod
    def create(cls, user_id: str, access_jti: str, refresh_jti: str,
               ip_address: str, user_agent: str, expires_at: datetime) -> Optional['UserSession']:
        """Створити нову сесію"""
        try:
            session_data = {
                'user_id': user_id,
                'access_token_jti': access_jti,
                'refresh_token_jti': refresh_jti,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'expires_at': expires_at.isoformat(),
                'is_active': True,
            }

            result = supabase.table('user_sessions').insert(session_data).execute()

            if result.data:
                return cls(result.data[0])
            return None

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None

    @classmethod
    def get_active_sessions(cls, user_id: str) -> List['UserSession']:
        """Отримати активні сесії користувача"""
        try:
            result = supabase.table('user_sessions') \
                .select('*') \
                .eq('user_id', user_id) \
                .eq('is_active', True) \
                .gt('expires_at', datetime.now(timezone.utc).isoformat()) \
                .execute()

            return [cls(data) for data in (result.data or [])]

        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []

    def deactivate(self) -> bool:
        """Деактивувати сесію"""
        try:
            result = supabase.table('user_sessions') \
                .update({'is_active': False}) \
                .eq('id', self.id) \
                .execute()

            if result.data:
                self.is_active = False
                return True
            return False

        except Exception as e:
            logger.error(f"Error deactivating session: {e}")
            return False