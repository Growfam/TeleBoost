# backend/users/models.py
"""
TeleBoost User Models
Розширені моделі користувача з додатковою функціональністю
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

from backend.auth.models import User as BaseUser
from backend.supabase_client import supabase
from backend.utils.redis_client import redis_client, cache_get, cache_set
from backend.utils.constants import (
    TRANSACTION_TYPE, USER_ROLES, CACHE_KEYS, CACHE_TTL,
    NOTIFICATION_TYPES, LIMITS
)
from backend.utils.formatters import format_price, format_datetime

logger = logging.getLogger(__name__)


class UserProfile(BaseUser):
    """Розширена модель користувача з додатковими методами"""

    def __init__(self, data: Dict[str, Any]):
        """Ініціалізація з базового користувача"""
        super().__init__(data)

        # Додаткові поля
        self.role = data.get('role', USER_ROLES['DEFAULT'])
        self.vip_expires_at = data.get('vip_expires_at')
        self.total_orders = data.get('total_orders', 0)
        self.successful_orders = data.get('successful_orders', 0)
        self.failed_orders = data.get('failed_orders', 0)
        self.average_order_value = float(data.get('average_order_value', 0))
        self.last_order_at = data.get('last_order_at')
        self.lifetime_value = float(data.get('lifetime_value', 0))
        self.trust_score = float(data.get('trust_score', 100.0))
        self.withdrawal_limit = float(data.get('withdrawal_limit', LIMITS['MAX_WITHDRAW']))
        self.daily_order_limit = data.get('daily_order_limit', 100)
        self.notes = data.get('notes', {})
        self.tags = data.get('tags', [])
        self.banned_at = data.get('banned_at')
        self.ban_reason = data.get('ban_reason')

    @classmethod
    def get_by_id(cls, user_id: str) -> Optional['UserProfile']:
        """Отримати розширений профіль користувача"""
        try:
            # Спробуємо з кешу
            cache_key = f"user_profile:{user_id}"
            cached = cache_get(cache_key, data_type='json')
            if cached:
                return cls(cached)

            # З БД
            result = supabase.table('users').select('*').eq('id', user_id).single().execute()
            if result.data:
                user = cls(result.data)
                # Кешуємо
                cache_set(cache_key, result.data, ttl=CACHE_TTL['user'])
                return user

            return None
        except Exception as e:
            logger.error(f"Error getting user profile {user_id}: {e}")
            return None

    def is_vip(self) -> bool:
        """Перевірити чи користувач VIP"""
        if not self.vip_expires_at:
            return False

        try:
            expires = datetime.fromisoformat(self.vip_expires_at.replace('Z', '+00:00'))
            return datetime.utcnow() < expires.replace(tzinfo=None)
        except:
            return False

    def get_role_display(self) -> str:
        """Отримати назву ролі для відображення"""
        role_names = {
            USER_ROLES['DEFAULT']: '👤 Користувач',
            USER_ROLES['PREMIUM']: '⭐ Преміум',
            USER_ROLES['VIP']: '👑 VIP',
            USER_ROLES['PARTNER']: '🤝 Партнер',
        }
        return role_names.get(self.role, self.role)

    def calculate_trust_score(self) -> float:
        """Розрахувати довіру до користувача"""
        score = 100.0

        # Фактори що збільшують довіру
        if self.is_premium:
            score += 10
        if self.is_vip():
            score += 20
        if self.total_deposited > 100:
            score += min(self.total_deposited / 10, 50)
        if self.successful_orders > 10:
            score += min(self.successful_orders, 30)

        # Фактори що зменшують довіру
        if self.failed_orders > 5:
            score -= self.failed_orders * 2
        if self.total_withdrawn > self.total_deposited * 2:
            score -= 20

        # Обмежуємо від 0 до 100
        return max(0, min(100, score))

    def get_limits(self) -> Dict[str, Any]:
        """Отримати ліміти користувача"""
        limits = {
            'daily_orders': self.daily_order_limit,
            'min_order': LIMITS['MIN_ORDER'],
            'max_order': LIMITS['MAX_ORDER'],
            'min_deposit': LIMITS['MIN_DEPOSIT'],
            'max_deposit': LIMITS['MAX_DEPOSIT'],
            'min_withdraw': LIMITS['MIN_WITHDRAW'],
            'max_withdraw': min(self.withdrawal_limit, LIMITS['MAX_WITHDRAW']),
        }

        # VIP бонуси
        if self.is_vip():
            limits['daily_orders'] *= 2
            limits['max_order'] *= 2
            limits['max_deposit'] *= 2
            limits['max_withdraw'] = LIMITS['MAX_WITHDRAW']

        return limits

    def can_withdraw(self, amount: float) -> Tuple[bool, Optional[str]]:
        """Перевірити чи може користувач вивести кошти"""
        if not self.is_active:
            return False, "Акаунт деактивований"

        if self.balance < amount:
            return False, f"Недостатньо коштів. Доступно: ${self.balance:.2f}"

        limits = self.get_limits()
        if amount < limits['min_withdraw']:
            return False, f"Мінімальна сума виведення: ${limits['min_withdraw']}"

        if amount > limits['max_withdraw']:
            return False, f"Максимальна сума виведення: ${limits['max_withdraw']}"

        # Перевірка денного ліміту
        today_withdrawn = self._get_today_withdrawn()
        if today_withdrawn + amount > limits['max_withdraw']:
            return False, f"Перевищено денний ліміт. Вже виведено: ${today_withdrawn:.2f}"

        # Перевірка trust score
        if self.trust_score < 50 and amount > 100:
            return False, "Низький рівень довіри. Зверніться до підтримки"

        return True, None

    def _get_today_withdrawn(self) -> float:
        """Отримати суму виведень за сьогодні"""
        try:
            today = datetime.utcnow().date()
            result = supabase.table('transactions') \
                .select('amount') \
                .eq('user_id', self.id) \
                .eq('type', TRANSACTION_TYPE.WITHDRAWAL) \
                .gte('created_at', today.isoformat()) \
                .execute()

            if result.data:
                return abs(sum(float(t['amount']) for t in result.data))
            return 0.0
        except Exception as e:
            logger.error(f"Error getting today withdrawn: {e}")
            return 0.0

    def update_stats(self) -> bool:
        """Оновити статистику користувача"""
        try:
            # Використовуємо функцію update_user_stats
            result = supabase.client.rpc('update_user_stats', {
                'p_user_id': self.id
            }).execute()

            # Перезавантажуємо дані користувача
            updated_user = supabase.table('users').select('*').eq('id', self.id).single().execute()

            if updated_user.data:
                # Оновлюємо локальні дані
                self.total_orders = updated_user.data.get('total_orders', 0)
                self.successful_orders = updated_user.data.get('successful_orders', 0)
                self.failed_orders = updated_user.data.get('failed_orders', 0)
                self.average_order_value = float(updated_user.data.get('average_order_value', 0))
                self.lifetime_value = float(updated_user.data.get('lifetime_value', 0))
                self.last_order_at = updated_user.data.get('last_order_at')

                # Розраховуємо trust score
                self.trust_score = self.calculate_trust_score()

                # Оновлюємо trust_score в БД
                supabase.table('users').update({
                    'trust_score': self.trust_score
                }).eq('id', self.id).execute()

                # Інвалідуємо кеш
                redis_client.delete(f"user_profile:{self.id}")

                return True

            return False

        except Exception as e:
            logger.error(f"Error updating user stats: {e}")
            return False


class UserSettings:
    """Налаштування користувача"""

    def __init__(self, user_id: str, settings: Dict[str, Any]):
        self.user_id = user_id
        self.notifications = settings.get('notifications', {
            'order_created': True,
            'order_completed': True,
            'order_failed': True,
            'payment_received': True,
            'referral_bonus': True,
            'system_messages': True,
        })
        self.language = settings.get('language', 'uk')
        self.timezone = settings.get('timezone', 'Europe/Kyiv')
        self.two_factor_enabled = settings.get('two_factor_enabled', False)
        self.api_access_enabled = settings.get('api_access_enabled', False)
        self.email_verified = settings.get('email_verified', False)
        self.phone_verified = settings.get('phone_verified', False)
        self.privacy = settings.get('privacy', {
            'show_online_status': True,
            'show_statistics': False,
            'allow_referrals': True,
        })

    @classmethod
    def get_for_user(cls, user_id: str) -> 'UserSettings':
        """Отримати налаштування користувача"""
        try:
            result = supabase.table('users').select('settings').eq('id', user_id).single().execute()
            settings = result.data.get('settings', {}) if result.data else {}
            return cls(user_id, settings)
        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            return cls(user_id, {})

    def update(self, updates: Dict[str, Any]) -> bool:
        """Оновити налаштування"""
        try:
            # Об'єднуємо з існуючими
            current = self.to_dict()
            for key, value in updates.items():
                if key in current:
                    if isinstance(current[key], dict) and isinstance(value, dict):
                        current[key].update(value)
                    else:
                        current[key] = value

            # Зберігаємо в БД
            result = supabase.table('users').update({
                'settings': current
            }).eq('id', self.user_id).execute()

            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Конвертувати в словник"""
        return {
            'notifications': self.notifications,
            'language': self.language,
            'timezone': self.timezone,
            'two_factor_enabled': self.two_factor_enabled,
            'api_access_enabled': self.api_access_enabled,
            'email_verified': self.email_verified,
            'phone_verified': self.phone_verified,
            'privacy': self.privacy,
        }


class UserActivity:
    """Активність користувача"""

    def __init__(self, user_id: str):
        self.user_id = user_id

    def log_action(self, action: str, details: Optional[Dict] = None) -> bool:
        """Записати дію користувача"""
        try:
            activity_data = {
                'user_id': self.user_id,
                'action': action,
                'details': details or {},
                'ip_address': None,  # TODO: get from request
                'user_agent': None,  # TODO: get from request
                'created_at': datetime.utcnow().isoformat()
            }

            result = supabase.table('user_activities').insert(activity_data).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error logging user activity: {e}")
            return False

    def get_recent_activities(self, limit: int = 50) -> List[Dict]:
        """Отримати останні активності"""
        try:
            result = supabase.table('user_activities') \
                .select('*') \
                .eq('user_id', self.user_id) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()

            return result.data or []
        except Exception as e:
            logger.error(f"Error getting user activities: {e}")
            return []

    def get_login_history(self, days: int = 30) -> List[Dict]:
        """Отримати історію входів"""
        try:
            since = datetime.utcnow() - timedelta(days=days)

            result = supabase.table('user_sessions') \
                .select('created_at, ip_address, user_agent') \
                .eq('user_id', self.user_id) \
                .gte('created_at', since.isoformat()) \
                .order('created_at', desc=True) \
                .execute()

            return result.data or []
        except Exception as e:
            logger.error(f"Error getting login history: {e}")
            return []


class UserNotification:
    """Сповіщення користувача"""

    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.type = data.get('type')
        self.title = data.get('title')
        self.message = data.get('message')
        self.data = data.get('data', {})
        self.is_read = data.get('is_read', False)
        self.created_at = data.get('created_at')
        self.read_at = data.get('read_at')

    @classmethod
    def create(cls, user_id: str, notification_type: str,
               title: str, message: str, data: Optional[Dict] = None) -> Optional['UserNotification']:
        """Створити сповіщення"""
        try:
            notification_data = {
                'user_id': user_id,
                'type': notification_type,
                'title': title,
                'message': message,
                'data': data or {},
                'is_read': False,
                'created_at': datetime.utcnow().isoformat()
            }

            result = supabase.table('user_notifications').insert(notification_data).execute()

            if result.data:
                return cls(result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None

    @classmethod
    def get_unread_count(cls, user_id: str) -> int:
        """Отримати кількість непрочитаних"""
        try:
            # Спробуємо з кешу
            cache_key = f"unread_notifications:{user_id}"
            cached = cache_get(cache_key, data_type='int')
            if cached is not None:
                return cached

            result = supabase.table('user_notifications') \
                .select('id', count='exact') \
                .eq('user_id', user_id) \
                .eq('is_read', False) \
                .execute()

            count = result.count if hasattr(result, 'count') else 0

            # Кешуємо на 1 хвилину
            cache_set(cache_key, count, ttl=60)

            return count
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0

    def mark_as_read(self) -> bool:
        """Позначити як прочитане"""
        try:
            result = supabase.table('user_notifications').update({
                'is_read': True,
                'read_at': datetime.utcnow().isoformat()
            }).eq('id', self.id).execute()

            if result.data:
                self.is_read = True
                self.read_at = datetime.utcnow().isoformat()

                # Інвалідуємо кеш
                redis_client.delete(f"unread_notifications:{self.user_id}")

                return True
            return False
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False