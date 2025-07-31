# backend/payments/models.py
"""
TeleBoost Payment Models
Моделі для роботи з платежами
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

from backend.supabase_client import supabase
from backend.utils.redis_client import redis_client, cache_get, cache_set
from backend.utils.constants import PAYMENT_STATUS, PAYMENT_PROVIDERS, CRYPTO_CURRENCIES

logger = logging.getLogger(__name__)


class PaymentMethod:
    """Метод оплати"""

    def __init__(self, provider: str, currency: str, network: Optional[str] = None):
        self.provider = provider
        self.currency = currency.upper()
        self.network = network
        self.is_active = True

        # Отримуємо деталі валюти
        self.currency_info = CRYPTO_CURRENCIES.get(self.currency, {})
        self.decimals = self.currency_info.get('decimals', 8)
        self.name = self.currency_info.get('name', currency)

    def get_display_name(self) -> str:
        """Отримати назву для відображення"""
        if self.network:
            return f"{self.currency} ({self.network})"
        return self.currency

    def to_dict(self) -> Dict[str, Any]:
        """Конвертувати в словник"""
        return {
            'provider': self.provider,
            'currency': self.currency,
            'network': self.network,
            'display_name': self.get_display_name(),
            'decimals': self.decimals,
            'is_active': self.is_active,
        }


class Payment:
    """Модель платежу"""

    def __init__(self, data: Dict[str, Any]):
        """Ініціалізація з даних БД"""
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.payment_id = data.get('payment_id')  # External payment ID
        self.provider = data.get('provider', '')
        self.type = data.get('type', 'deposit')
        self.amount = Decimal(str(data.get('amount', 0)))
        self.currency = data.get('currency', 'USDT')
        self.status = data.get('status', PAYMENT_STATUS.WAITING)

        # Payment details
        self.payment_url = data.get('payment_url')
        self.expires_at = data.get('expires_at')
        self.paid_at = data.get('paid_at')

        # Metadata
        self.metadata = data.get('metadata', {})
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')

    @classmethod
    def create(cls, payment_data: Dict[str, Any]) -> Optional['Payment']:
        """
        Створити новий платіж

        Args:
            payment_data: Дані платежу

        Returns:
            Payment об'єкт або None
        """
        try:
            # Валідація обов'язкових полів
            required = ['user_id', 'amount', 'currency', 'provider']
            for field in required:
                if field not in payment_data:
                    logger.error(f"Missing required field: {field}")
                    return None

            # Встановлюємо дефолтні значення
            payment_data['type'] = payment_data.get('type', 'deposit')
            payment_data['status'] = PAYMENT_STATUS.WAITING
            payment_data['created_at'] = datetime.utcnow().isoformat()
            payment_data['updated_at'] = payment_data['created_at']

            # Створюємо в БД
            result = supabase.table('payments').insert(payment_data).execute()

            if result.data:
                payment = cls(result.data[0])

                # Кешуємо
                cls._cache_payment(payment)

                logger.info(f"Created payment {payment.id} for user {payment.user_id}")
                return payment

            return None

        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            return None

    @classmethod
    def get_by_id(cls, payment_id: str, use_cache: bool = True) -> Optional['Payment']:
        """
        Отримати платіж за ID

        Args:
            payment_id: ID платежу (UUID)
            use_cache: Використовувати кеш

        Returns:
            Payment або None
        """
        try:
            # Спробуємо з кешу
            if use_cache:
                cache_key = f"payment:{payment_id}"
                cached = cache_get(cache_key, data_type='json')
                if cached:
                    return cls(cached)

            # З БД
            result = supabase.table('payments') \
                .select('*') \
                .eq('id', payment_id) \
                .single() \
                .execute()

            if result.data:
                payment = cls(result.data)

                # Кешуємо
                if use_cache:
                    cls._cache_payment(payment)

                return payment

            return None

        except Exception as e:
            logger.error(f"Error getting payment {payment_id}: {e}")
            return None

    @classmethod
    def get_by_payment_id(cls, payment_id: str, provider: Optional[str] = None) -> Optional['Payment']:
        """
        Отримати платіж за external payment ID

        Args:
            payment_id: External payment ID
            provider: Провайдер (для уточнення)

        Returns:
            Payment або None
        """
        try:
            query = supabase.table('payments') \
                .select('*') \
                .eq('payment_id', payment_id)

            if provider:
                query = query.eq('provider', provider)

            result = query.single().execute()

            if result.data:
                return cls(result.data)

            return None

        except Exception as e:
            logger.error(f"Error getting payment by payment_id {payment_id}: {e}")
            return None

    @classmethod
    def get_user_payments(cls, user_id: str, status: Optional[str] = None,
                          limit: int = 50, offset: int = 0) -> List['Payment']:
        """
        Отримати платежі користувача

        Args:
            user_id: ID користувача
            status: Фільтр по статусу
            limit: Ліміт
            offset: Зміщення

        Returns:
            Список платежів
        """
        try:
            query = supabase.table('payments') \
                .select('*') \
                .eq('user_id', user_id)

            if status:
                query = query.eq('status', status)

            result = query.order('created_at', desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()

            if result.data:
                return [cls(data) for data in result.data]

            return []

        except Exception as e:
            logger.error(f"Error getting user payments: {e}")
            return []

    def update(self, update_data: Dict[str, Any]) -> bool:
        """
        Оновити платіж

        Args:
            update_data: Дані для оновлення

        Returns:
            True якщо успішно
        """
        try:
            # Додаємо timestamp
            update_data['updated_at'] = datetime.utcnow().isoformat()

            # Оновлюємо в БД
            result = supabase.table('payments') \
                .update(update_data) \
                .eq('id', self.id) \
                .execute()

            if result.data:
                # Оновлюємо локальні дані
                for key, value in update_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)

                # Інвалідуємо кеш
                self._invalidate_cache()

                return True

            return False

        except Exception as e:
            logger.error(f"Error updating payment {self.id}: {e}")
            return False

    def update_status(self, new_status: str, metadata: Optional[Dict] = None) -> bool:
        """
        Оновити статус платежу

        Args:
            new_status: Новий статус
            metadata: Додаткові дані

        Returns:
            True якщо успішно
        """
        update_data = {
            'status': new_status,
        }

        # Додаємо дату оплати якщо статус успішний
        if new_status in [PAYMENT_STATUS.CONFIRMED, PAYMENT_STATUS.FINISHED]:
            update_data['paid_at'] = datetime.utcnow().isoformat()

        # Оновлюємо metadata
        if metadata:
            current_metadata = self.metadata or {}
            current_metadata.update(metadata)
            update_data['metadata'] = current_metadata

        return self.update(update_data)

    def is_expired(self) -> bool:
        """Перевірити чи платіж прострочений"""
        if not self.expires_at:
            return False

        try:
            expires_at = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            return datetime.utcnow() > expires_at.replace(tzinfo=None)
        except:
            return False

    def can_be_paid(self) -> bool:
        """Перевірити чи платіж може бути оплачений"""
        return (
                self.status == PAYMENT_STATUS.WAITING and
                not self.is_expired()
        )

    @classmethod
    def _cache_payment(cls, payment: 'Payment') -> None:
        """Кешувати платіж"""
        cache_key = f"payment:{payment.id}"
        cache_set(cache_key, payment.to_dict(), ttl=300)  # 5 хвилин

    def _invalidate_cache(self) -> None:
        """Інвалідувати кеш"""
        cache_key = f"payment:{self.id}"
        redis_client.delete(cache_key)

    def to_dict(self) -> Dict[str, Any]:
        """Конвертувати в словник"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'payment_id': self.payment_id,
            'provider': self.provider,
            'type': self.type,
            'amount': float(self.amount),
            'currency': self.currency,
            'status': self.status,
            'payment_url': self.payment_url,
            'expires_at': self.expires_at,
            'paid_at': self.paid_at,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_expired': self.is_expired(),
            'can_be_paid': self.can_be_paid(),
        }

    def to_public_dict(self) -> Dict[str, Any]:
        """Конвертувати в словник для публічного API"""
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'provider': self.provider,
            'amount': float(self.amount),
            'currency': self.currency,
            'status': self.status,
            'payment_url': self.payment_url,
            'expires_at': self.expires_at,
            'created_at': self.created_at,
            'is_expired': self.is_expired(),
        }