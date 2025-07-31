# backend/referrals/models.py
"""
TeleBoost Referral Models
Моделі для реферальної системи
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from backend.supabase_client import supabase
from backend.utils.redis_client import redis_client, cache_get, cache_set
from backend.utils.constants import CACHE_KEYS, CACHE_TTL

logger = logging.getLogger(__name__)


@dataclass
class ReferralStats:
    """Статистика рефералів"""
    total_referrals: int = 0
    active_referrals: int = 0
    level1_referrals: int = 0
    level2_referrals: int = 0
    total_earned: float = 0.0
    level1_earned: float = 0.0
    level2_earned: float = 0.0
    pending_bonuses: float = 0.0
    this_month_earned: float = 0.0
    last_referral_date: Optional[datetime] = None


class Referral:
    """Модель реферала"""

    def __init__(self, data: Dict[str, Any]):
        """Ініціалізація з даних БД"""
        self.id = data.get('id')
        self.referrer_id = data.get('referrer_id')
        self.referred_id = data.get('referred_id')
        self.level = data.get('level', 1)
        self.bonus_paid = data.get('bonus_paid', False)
        self.bonus_amount = float(data.get('bonus_amount', 0))
        self.total_deposits = float(data.get('total_deposits', 0))
        self.total_bonuses_generated = float(data.get('total_bonuses_generated', 0))
        self.is_active = data.get('is_active', True)
        self.created_at = data.get('created_at')
        self.last_deposit_at = data.get('last_deposit_at')

        # Дані реферала (joined)
        self.referred_user = data.get('referred_user', {})

    @classmethod
    def create(cls, referrer_id: str, referred_id: str, level: int = 1) -> Optional['Referral']:
        """
        Створити зв'язок реферал-реферер

        Args:
            referrer_id: ID реферера
            referred_id: ID реферала
            level: Рівень реферала (1 або 2)

        Returns:
            Referral об'єкт або None
        """
        try:
            # Перевіряємо чи не існує вже такий зв'язок
            existing = supabase.table('referrals') \
                .select('*') \
                .eq('referrer_id', referrer_id) \
                .eq('referred_id', referred_id) \
                .single() \
                .execute()

            if existing.data:
                logger.warning(f"Referral link already exists: {referrer_id} -> {referred_id}")
                return cls(existing.data)

            # Створюємо новий зв'язок
            referral_data = {
                'referrer_id': referrer_id,
                'referred_id': referred_id,
                'level': level,
                'bonus_paid': False,
                'bonus_amount': 0,
                'is_active': True,
                'created_at': datetime.utcnow().isoformat()
            }

            result = supabase.table('referrals').insert(referral_data).execute()

            if result.data:
                # Інвалідуємо кеш
                cls._invalidate_cache(referrer_id)

                logger.info(f"Created referral link: {referrer_id} -> {referred_id} (level {level})")
                return cls(result.data[0])

            return None

        except Exception as e:
            logger.error(f"Error creating referral: {e}")
            return None

    @classmethod
    def get_user_referrals(cls, user_id: str, level: Optional[int] = None,
                           active_only: bool = True) -> List['Referral']:
        """
        Отримати рефералів користувача

        Args:
            user_id: ID користувача
            level: Фільтр по рівню (1 або 2)
            active_only: Тільки активні

        Returns:
            Список рефералів
        """
        try:
            # Спробуємо з кешу
            cache_key = f"referrals:{user_id}:list"
            if level:
                cache_key += f":level{level}"

            cached = cache_get(cache_key, data_type='json')
            if cached:
                return [cls(data) for data in cached]

            # Запит до БД з JOIN для отримання даних користувача
            query = supabase.table('referrals') \
                .select(
                '*, referred_user:users!referred_id(id, telegram_id, username, first_name, last_name, balance, created_at, last_login)') \
                .eq('referrer_id', user_id)

            if level:
                query = query.eq('level', level)

            if active_only:
                query = query.eq('is_active', True)

            query = query.order('created_at', desc=True)

            result = query.execute()

            if result.data:
                # Кешуємо
                cache_set(cache_key, result.data, ttl=CACHE_TTL['referrals'])

                return [cls(data) for data in result.data]

            return []

        except Exception as e:
            logger.error(f"Error getting user referrals: {e}")
            return []

    @classmethod
    def get_referral_tree(cls, user_id: str) -> Dict[str, List['Referral']]:
        """
        Отримати дерево рефералів (2 рівні)

        Args:
            user_id: ID користувача

        Returns:
            Словник з рефералами по рівнях
        """
        try:
            # Рефералі першого рівня
            level1_refs = cls.get_user_referrals(user_id, level=1)

            # Рефералі другого рівня
            level2_refs = []

            for ref in level1_refs:
                # Для кожного реферала першого рівня шукаємо його рефералів
                sub_refs = cls.get_user_referrals(ref.referred_id, level=1)

                # Створюємо записи другого рівня
                for sub_ref in sub_refs:
                    # Клонуємо дані та встановлюємо рівень 2
                    level2_data = sub_ref.__dict__.copy()
                    level2_data['level'] = 2
                    level2_data['referrer_id'] = user_id  # Основний реферер
                    level2_refs.append(cls(level2_data))

            return {
                'level1': level1_refs,
                'level2': level2_refs
            }

        except Exception as e:
            logger.error(f"Error getting referral tree: {e}")
            return {'level1': [], 'level2': []}

    @classmethod
    def get_stats(cls, user_id: str) -> ReferralStats:
        """
        Отримати статистику рефералів

        Args:
            user_id: ID користувача

        Returns:
            Статистика рефералів
        """
        try:
            # Спробуємо з кешу
            cache_key = f"referrals:{user_id}:stats"
            cached = cache_get(cache_key, data_type='json')
            if cached:
                return ReferralStats(**cached)

            stats = ReferralStats()

            # Отримуємо дерево рефералів
            tree = cls.get_referral_tree(user_id)

            # Рахуємо статистику
            stats.level1_referrals = len(tree['level1'])
            stats.level2_referrals = len(tree['level2'])
            stats.total_referrals = stats.level1_referrals + stats.level2_referrals

            # Рахуємо активних (ті що зробили хоч один депозит)
            stats.active_referrals = sum(
                1 for ref in tree['level1'] + tree['level2']
                if ref.total_deposits > 0
            )

            # Рахуємо заробіток
            for ref in tree['level1']:
                stats.level1_earned += ref.total_bonuses_generated
                stats.total_earned += ref.total_bonuses_generated

            for ref in tree['level2']:
                stats.level2_earned += ref.total_bonuses_generated
                stats.total_earned += ref.total_bonuses_generated

            # Остання дата реферала
            all_refs = tree['level1'] + tree['level2']
            if all_refs:
                dates = [ref.created_at for ref in all_refs if ref.created_at]
                if dates:
                    stats.last_referral_date = max(dates)

            # Заробіток за цей місяць
            current_month = datetime.utcnow().month
            current_year = datetime.utcnow().year

            # Отримуємо транзакції за цей місяць
            result = supabase.table('transactions') \
                .select('amount') \
                .eq('user_id', user_id) \
                .eq('type', 'referral_bonus') \
                .gte('created_at', f"{current_year}-{current_month:02d}-01") \
                .execute()

            if result.data:
                stats.this_month_earned = sum(float(t['amount']) for t in result.data)

            # Кешуємо статистику
            cache_set(cache_key, stats.__dict__, ttl=CACHE_TTL['referrals'])

            return stats

        except Exception as e:
            logger.error(f"Error getting referral stats: {e}")
            return ReferralStats()

    @classmethod
    def update_deposit_stats(cls, referral_id: str, deposit_amount: float,
                             bonus_amount: float) -> bool:
        """
        Оновити статистику депозитів реферала

        Args:
            referral_id: ID зв'язку
            deposit_amount: Сума депозиту
            bonus_amount: Сума бонусу

        Returns:
            True якщо успішно
        """
        try:
            # Оновлюємо статистику
            result = supabase.table('referrals') \
                .update({
                'total_deposits': supabase.client.rpc('increment_value', {
                    'table_name': 'referrals',
                    'column_name': 'total_deposits',
                    'row_id': referral_id,
                    'increment_by': deposit_amount
                }),
                'total_bonuses_generated': supabase.client.rpc('increment_value', {
                    'table_name': 'referrals',
                    'column_name': 'total_bonuses_generated',
                    'row_id': referral_id,
                    'increment_by': bonus_amount
                }),
                'last_deposit_at': datetime.utcnow().isoformat(),
                'bonus_paid': True
            }) \
                .eq('id', referral_id) \
                .execute()

            return bool(result.data)

        except Exception as e:
            logger.error(f"Error updating deposit stats: {e}")
            return False

    @classmethod
    def _invalidate_cache(cls, user_id: str) -> None:
        """Інвалідувати кеш рефералів"""
        patterns = [
            f"referrals:{user_id}:*",
            f"user:{user_id}:referrals",
        ]

        for pattern in patterns:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)

    def to_dict(self) -> Dict[str, Any]:
        """Конвертувати в словник"""
        return {
            'id': self.id,
            'referrer_id': self.referrer_id,
            'referred_id': self.referred_id,
            'level': self.level,
            'bonus_paid': self.bonus_paid,
            'bonus_amount': self.bonus_amount,
            'total_deposits': self.total_deposits,
            'total_bonuses_generated': self.total_bonuses_generated,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'last_deposit_at': self.last_deposit_at,
            'referred_user': self.referred_user
        }