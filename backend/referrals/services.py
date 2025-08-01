# backend/referrals/services.py
"""
TeleBoost Referral Services
Бізнес-логіка реферальної системи
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from decimal import Decimal

from backend.referrals.models import Referral, ReferralStats
from backend.supabase_client import supabase
from backend.utils.redis_client import invalidate_user_cache
from backend.utils.constants import TRANSACTION_TYPE

logger = logging.getLogger(__name__)

# Реферальні відсотки
REFERRAL_RATES = {
    1: 0.07,  # 7% для першого рівня
    2: 0.025  # 2.5% для другого рівня
}


def process_referral_bonus(referrer, new_user) -> bool:
    """
    Обробити реферальний бонус при реєстрації

    Args:
        referrer: User об'єкт реферера
        new_user: User об'єкт нового користувача

    Returns:
        True якщо успішно
    """
    try:
        # Створюємо зв'язок першого рівня
        referral = Referral.create(
            referrer_id=referrer.id,
            referred_id=new_user.id,
            level=1
        )

        if not referral:
            logger.error(f"Failed to create referral link: {referrer.id} -> {new_user.id}")
            return False

        # Перевіряємо чи є у реферера свій реферер (для створення зв'язку 2го рівня)
        if referrer.referred_by:
            # Створюємо зв'язок другого рівня
            second_level_referral = Referral.create(
                referrer_id=referrer.referred_by,
                referred_id=new_user.id,
                level=2
            )

            if second_level_referral:
                logger.info(f"Created second level referral: {referrer.referred_by} -> {new_user.id}")

        logger.info(f"Successfully processed referral registration: {referrer.telegram_id} -> {new_user.telegram_id}")
        return True

    except Exception as e:
        logger.error(f"Error processing referral bonus: {e}")
        return False


def process_deposit_referral_bonuses(user_id: str, deposit_amount: float) -> Dict[str, Any]:
    """
    Обробити реферальні бонуси при депозиті

    Args:
        user_id: ID користувача який зробив депозит
        deposit_amount: Сума депозиту

    Returns:
        Словник з інформацією про нараховані бонуси
    """
    try:
        bonuses = {
            'level1_bonus': 0,
            'level2_bonus': 0,
            'level1_referrer': None,
            'level2_referrer': None,
            'total_bonus': 0,
            'transactions': []
        }

        # Знаходимо рефереріів
        # Рівень 1 - прямий реферер
        level1_result = supabase.table('referrals') \
            .select('*, referrer:users!referrer_id(id, telegram_id, username, balance)') \
            .eq('referred_id', user_id) \
            .eq('level', 1) \
            .eq('is_active', True) \
            .single() \
            .execute()

        if level1_result.data:
            referral = level1_result.data
            referrer = referral['referrer']

            # Розраховуємо бонус
            bonus_amount = round(deposit_amount * REFERRAL_RATES[1], 2)

            if bonus_amount > 0:
                # Створюємо транзакцію для реферера
                transaction_result = _create_referral_transaction(
                    referrer_id=referrer['id'],
                    amount=bonus_amount,
                    level=1,
                    referred_user_id=user_id,
                    deposit_amount=deposit_amount
                )

                if transaction_result:
                    bonuses['level1_bonus'] = bonus_amount
                    bonuses['level1_referrer'] = referrer
                    bonuses['transactions'].append(transaction_result)

                    # Оновлюємо статистику реферала
                    Referral.update_deposit_stats(
                        referral_id=referral['id'],
                        deposit_amount=deposit_amount,
                        bonus_amount=bonus_amount
                    )

        # Рівень 2 - реферер реферера
        level2_result = supabase.table('referrals') \
            .select('*, referrer:users!referrer_id(id, telegram_id, username, balance)') \
            .eq('referred_id', user_id) \
            .eq('level', 2) \
            .eq('is_active', True) \
            .single() \
            .execute()

        if level2_result.data:
            referral = level2_result.data
            referrer = referral['referrer']

            # Розраховуємо бонус
            bonus_amount = round(deposit_amount * REFERRAL_RATES[2], 2)

            if bonus_amount > 0:
                # Створюємо транзакцію для реферера
                transaction_result = _create_referral_transaction(
                    referrer_id=referrer['id'],
                    amount=bonus_amount,
                    level=2,
                    referred_user_id=user_id,
                    deposit_amount=deposit_amount
                )

                if transaction_result:
                    bonuses['level2_bonus'] = bonus_amount
                    bonuses['level2_referrer'] = referrer
                    bonuses['transactions'].append(transaction_result)

                    # Оновлюємо статистику реферала
                    Referral.update_deposit_stats(
                        referral_id=referral['id'],
                        deposit_amount=deposit_amount,
                        bonus_amount=bonus_amount
                    )

        bonuses['total_bonus'] = bonuses['level1_bonus'] + bonuses['level2_bonus']

        logger.info(
            f"Processed deposit referral bonuses: user={user_id}, "
            f"deposit={deposit_amount}, total_bonus={bonuses['total_bonus']}"
        )

        return bonuses

    except Exception as e:
        logger.error(f"Error processing deposit referral bonuses: {e}")
        return {
            'level1_bonus': 0,
            'level2_bonus': 0,
            'total_bonus': 0,
            'transactions': []
        }


def _create_referral_transaction(referrer_id: str, amount: float, level: int,
                                 referred_user_id: str, deposit_amount: float) -> Optional[Dict]:
    """
    Створити транзакцію реферального бонусу (тільки % від депозиту)

    Args:
        referrer_id: ID реферера
        amount: Сума бонусу (вже розрахована як % від депозиту)
        level: Рівень реферала (1 або 2)
        referred_user_id: ID реферала який зробив депозит
        deposit_amount: Сума депозиту реферала

    Returns:
        Дані транзакції або None
    """
    try:
        # Отримуємо поточний баланс реферера
        current_balance_result = supabase.table('users') \
            .select('balance') \
            .eq('id', referrer_id) \
            .single() \
            .execute()

        if not current_balance_result.data:
            logger.error(f"User not found: {referrer_id}")
            return None

        current_balance = float(current_balance_result.data['balance'])
        new_balance = current_balance + amount

        # 1. Оновлюємо баланс реферера
        balance_updated = supabase.update_user_balance(referrer_id, amount, operation='add')

        if not balance_updated:
            logger.error(f"Failed to update balance for user {referrer_id}")
            return None

        # 2. Створюємо запис транзакції
        transaction_data = {
            'user_id': referrer_id,
            'type': TRANSACTION_TYPE.REFERRAL_BONUS,
            'amount': amount,
            'balance_before': current_balance,
            'balance_after': new_balance,
            'description': f'Реферальний бонус {level} рівня ({REFERRAL_RATES[level] * 100}%) від депозиту {deposit_amount} USD',
            'metadata': {
                'referral_level': level,
                'referred_user_id': referred_user_id,
                'deposit_amount': deposit_amount,
                'bonus_rate': REFERRAL_RATES[level]
            }
        }

        transaction = supabase.create_transaction(transaction_data)

        if not transaction:
            logger.error(f"Failed to create transaction for user {referrer_id}")
            # ВАЖЛИВО: Тут потрібно було б відкотити баланс, але без транзакцій це складно
            return None

        # 3. Оновлюємо referral_earnings користувача
        earnings_result = supabase.client.rpc('increment_value', {
            'table_name': 'users',
            'column_name': 'referral_earnings',
            'row_id': referrer_id,
            'increment_by': amount
        }).execute()

        # Перевіряємо результат RPC виклику
        if not earnings_result.data:
            logger.error(f"Failed to update referral_earnings for user {referrer_id}: {earnings_result}")
            # Продовжуємо, бо основні операції вже виконані
        else:
            logger.debug(f"Successfully updated referral_earnings for user {referrer_id}")

        # Інвалідуємо кеш
        invalidate_user_cache(referrer_id)

        logger.info(
            f"Created referral bonus transaction: referrer={referrer_id}, "
            f"amount={amount} ({REFERRAL_RATES[level] * 100}%), level={level}, "
            f"from deposit={deposit_amount}"
        )

        return transaction

    except Exception as e:
        logger.error(f"Error creating referral transaction: {e}", exc_info=True)
        return None

def get_user_referrals(user_id: str, level: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Отримати список рефералів користувача

    Args:
        user_id: ID користувача
        level: Фільтр по рівню

    Returns:
        Список рефералів
    """
    try:
        referrals = Referral.get_user_referrals(user_id, level=level)

        # Форматуємо для відображення
        formatted = []
        for ref in referrals:
            user = ref.referred_user
            formatted.append({
                'id': ref.id,
                'user_id': ref.referred_id,
                'telegram_id': user.get('telegram_id'),
                'username': user.get('username', ''),
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'level': ref.level,
                'total_deposits': ref.total_deposits,
                'total_bonuses': ref.total_bonuses_generated,
                'is_active': ref.total_deposits > 0,
                'joined_at': ref.created_at,
                'last_deposit_at': ref.last_deposit_at
            })

        return formatted

    except Exception as e:
        logger.error(f"Error getting user referrals: {e}")
        return []


def get_referral_stats(user_id: str) -> Dict[str, Any]:
    """
    Отримати статистику рефералів

    Args:
        user_id: ID користувача

    Returns:
        Статистика
    """
    try:
        stats = Referral.get_stats(user_id)

        return {
            'total_referrals': stats.total_referrals,
            'active_referrals': stats.active_referrals,
            'level1_referrals': stats.level1_referrals,
            'level2_referrals': stats.level2_referrals,
            'total_earned': stats.total_earned,
            'level1_earned': stats.level1_earned,
            'level2_earned': stats.level2_earned,
            'this_month_earned': stats.this_month_earned,
            'pending_bonuses': stats.pending_bonuses,
            'last_referral_date': stats.last_referral_date,
            'rates': {
                'level1': REFERRAL_RATES[1] * 100,
                'level2': REFERRAL_RATES[2] * 100
            }
        }

    except Exception as e:
        logger.error(f"Error getting referral stats: {e}")
        return {
            'total_referrals': 0,
            'active_referrals': 0,
            'total_earned': 0,
            'rates': {
                'level1': REFERRAL_RATES[1] * 100,
                'level2': REFERRAL_RATES[2] * 100
            }
        }


def get_referral_tree(user_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Отримати дерево рефералів

    Args:
        user_id: ID користувача

    Returns:
        Дерево рефералів по рівнях
    """
    try:
        tree = Referral.get_referral_tree(user_id)

        # Форматуємо для відображення
        formatted_tree = {
            'level1': [],
            'level2': []
        }

        for level, referrals in tree.items():
            for ref in referrals:
                user = ref.referred_user
                formatted_tree[level].append({
                    'user_id': ref.referred_id,
                    'telegram_id': user.get('telegram_id'),
                    'username': user.get('username', ''),
                    'display_name': f"@{user.get('username')}" if user.get('username') else user.get('first_name',
                                                                                                     'User'),
                    'deposits': ref.total_deposits,
                    'generated_bonus': ref.total_bonuses_generated,
                    'is_active': ref.total_deposits > 0,
                    'joined_at': ref.created_at
                })

        return formatted_tree

    except Exception as e:
        logger.error(f"Error getting referral tree: {e}")
        return {'level1': [], 'level2': []}


def calculate_referral_bonus(amount: float, level: int) -> float:
    """
    Розрахувати реферальний бонус

    Args:
        amount: Сума депозиту
        level: Рівень реферала

    Returns:
        Сума бонусу
    """
    if level not in REFERRAL_RATES:
        return 0.0

    return round(amount * REFERRAL_RATES[level], 2)


def get_referral_earnings(user_id: str, period: Optional[str] = None) -> Dict[str, float]:
    """
    Отримати заробіток з рефералів за період

    Args:
        user_id: ID користувача
        period: Період ('today', 'week', 'month', 'all')

    Returns:
        Заробіток по рівнях
    """
    try:
        # Базовий запит
        query = supabase.table('transactions') \
            .select('amount, metadata') \
            .eq('user_id', user_id) \
            .eq('type', TRANSACTION_TYPE.REFERRAL_BONUS)

        # Фільтр по періоду
        if period == 'today':
            start_date = datetime.utcnow().replace(hour=0, minute=0, second=0)
            query = query.gte('created_at', start_date.isoformat())
        elif period == 'week':
            start_date = datetime.utcnow() - timedelta(days=7)
            query = query.gte('created_at', start_date.isoformat())
        elif period == 'month':
            start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
            query = query.gte('created_at', start_date.isoformat())

        result = query.execute()

        earnings = {
            'total': 0,
            'level1': 0,
            'level2': 0
        }

        if result.data:
            for transaction in result.data:
                amount = float(transaction['amount'])
                level = transaction.get('metadata', {}).get('referral_level', 1)

                earnings['total'] += amount
                if level == 1:
                    earnings['level1'] += amount
                elif level == 2:
                    earnings['level2'] += amount

        return earnings

    except Exception as e:
        logger.error(f"Error getting referral earnings: {e}")
        return {'total': 0, 'level1': 0, 'level2': 0}