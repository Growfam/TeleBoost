# backend/users/services.py
"""
TeleBoost User Services
Бізнес-логіка для роботи з користувачами
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal

from backend.users.models import UserProfile, UserSettings, UserActivity, UserNotification
from backend.supabase_client import supabase
from backend.utils.redis_client import redis_client, cache_get, cache_set
from backend.utils.constants import (
    TRANSACTION_TYPE, USER_ROLES, NOTIFICATION_TYPES,
    LIMITS, WITHDRAWAL_STATUS, CACHE_TTL
)
from backend.utils.formatters import format_price, format_datetime

logger = logging.getLogger(__name__)


class UserService:
    """Сервіс для управління користувачами"""

    @staticmethod
    def get_user_profile(user_id: str) -> Optional[UserProfile]:
        """Отримати повний профіль користувача"""
        return UserProfile.get_by_id(user_id)

    @staticmethod
    def get_user_balance_info(user_id: str) -> Dict[str, Any]:
        """Отримати детальну інформацію про баланс"""
        try:
            # Отримуємо користувача
            user = UserProfile.get_by_id(user_id)
            if not user:
                return None

            # Кешуємо баланс на 1 хвилину
            cache_key = f"balance_info:{user_id}"
            cached = cache_get(cache_key, data_type='json')
            if cached:
                return cached

            # Рахуємо активні замовлення
            active_orders = supabase.table('orders') \
                .select('charge') \
                .eq('user_id', user_id) \
                .in_('status', ['pending', 'processing', 'in_progress']) \
                .execute()

            frozen_amount = sum(float(o['charge']) for o in (active_orders.data or []))

            # Рахуємо pending виведення
            pending_withdrawals = supabase.table('payments') \
                .select('amount') \
                .eq('user_id', user_id) \
                .eq('type', 'withdrawal') \
                .in_('status', ['waiting', 'processing']) \
                .execute()

            pending_withdrawal_amount = sum(float(p['amount']) for p in (pending_withdrawals.data or []))

            balance_info = {
                'balance': user.balance,
                'available_balance': user.balance - frozen_amount - pending_withdrawal_amount,
                'frozen_amount': frozen_amount,
                'pending_withdrawals': pending_withdrawal_amount,
                'total_deposited': user.total_deposited,
                'total_withdrawn': user.total_withdrawn,
                'total_spent': user.total_spent,
                'referral_earnings': user.referral_earnings,
                'lifetime_value': user.lifetime_value,
                'currency': 'USD',
                'limits': user.get_limits(),
                'can_withdraw': user.balance - frozen_amount - pending_withdrawal_amount >= LIMITS['MIN_WITHDRAW'],
                'updated_at': datetime.utcnow().isoformat()
            }

            # Кешуємо
            cache_set(cache_key, balance_info, ttl=60)

            return balance_info

        except Exception as e:
            logger.error(f"Error getting balance info: {e}")
            return None

    @staticmethod
    def get_user_transactions(user_id: str, transaction_type: Optional[str] = None,
                              limit: int = 50, offset: int = 0) -> List[Dict]:
        """Отримати транзакції користувача з фільтрацією"""
        try:
            query = supabase.table('transactions') \
                .select('*') \
                .eq('user_id', user_id)

            if transaction_type:
                query = query.eq('type', transaction_type)

            result = query.order('created_at', desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()

            transactions = []
            for t in (result.data or []):
                # Додаємо форматування
                t['formatted_amount'] = format_price(abs(t['amount']), 'USD')
                t['formatted_date'] = format_datetime(t['created_at'])
                t['is_credit'] = t['amount'] > 0
                transactions.append(t)

            return transactions

        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []

    @staticmethod
    def create_withdrawal(user_id: str, amount: float, method: str,
                          address: str, network: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Створити запит на виведення"""
        try:
            # Отримуємо користувача
            user = UserProfile.get_by_id(user_id)
            if not user:
                return False, "Користувач не знайдений"

            # Перевіряємо можливість виведення
            can_withdraw, error = user.can_withdraw(amount)
            if not can_withdraw:
                return False, error

            # Створюємо запит на виведення
            withdrawal_data = {
                'user_id': user_id,
                'type': 'withdrawal',
                'amount': amount,
                'currency': 'USDT',
                'provider': method,
                'status': WITHDRAWAL_STATUS.PENDING,
                'metadata': {
                    'address': address,
                    'network': network,
                    'requested_at': datetime.utcnow().isoformat()
                }
            }

            # Створюємо в БД
            result = supabase.table('payments').insert(withdrawal_data).execute()

            if result.data:
                # Блокуємо кошти
                supabase.update_user_balance(user_id, amount, operation='subtract')

                # Створюємо транзакцію
                transaction_data = {
                    'user_id': user_id,
                    'type': TRANSACTION_TYPE.WITHDRAWAL,
                    'amount': -amount,
                    'balance_before': user.balance,
                    'balance_after': user.balance - amount,
                    'description': f'Виведення {amount} USDT',
                    'metadata': {
                        'payment_id': result.data[0]['id'],
                        'address': address,
                        'network': network
                    }
                }
                supabase.create_transaction(transaction_data)

                # Сповіщення
                UserNotification.create(
                    user_id=user_id,
                    notification_type=NOTIFICATION_TYPES['WITHDRAWAL_APPROVED'],
                    title='Запит на виведення',
                    message=f'Ваш запит на виведення ${amount} прийнято в обробку',
                    data={'amount': amount, 'payment_id': result.data[0]['id']}
                )

                # Інвалідуємо кеш
                redis_client.delete(f"balance_info:{user_id}")

                return True, None

            return False, "Помилка створення запиту"

        except Exception as e:
            logger.error(f"Error creating withdrawal: {e}")
            return False, "Внутрішня помилка"

    @staticmethod
    def upgrade_to_vip(user_id: str, days: int = 30) -> bool:
        """Оновити користувача до VIP"""
        try:
            expires_at = datetime.utcnow() + timedelta(days=days)

            result = supabase.table('users').update({
                'role': USER_ROLES['VIP'],
                'vip_expires_at': expires_at.isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', user_id).execute()

            if result.data:
                # Сповіщення
                UserNotification.create(
                    user_id=user_id,
                    notification_type='system_message',
                    title='VIP статус активовано!',
                    message=f'Вітаємо! Ваш VIP статус активний до {expires_at.strftime("%d.%m.%Y")}',
                    data={'expires_at': expires_at.isoformat()}
                )

                # Інвалідуємо кеш
                redis_client.delete(f"user_profile:{user_id}")

                return True

            return False

        except Exception as e:
            logger.error(f"Error upgrading to VIP: {e}")
            return False

    @staticmethod
    def get_user_statistics(user_id: str) -> Dict[str, Any]:
        """Отримати детальну статистику користувача"""
        try:
            # Кешуємо на 5 хвилин
            cache_key = f"user_stats:{user_id}"
            cached = cache_get(cache_key, data_type='json')
            if cached:
                return cached

            # Отримуємо користувача
            user = UserProfile.get_by_id(user_id)
            if not user:
                return None

            # Оновлюємо статистику через функцію БД
            supabase.client.rpc('update_user_stats', {
                'p_user_id': user_id
            }).execute()

            # Перезавантажуємо користувача з оновленими даними
            user = UserProfile.get_by_id(user_id)

            # Статистика за періоди
            now = datetime.utcnow()
            periods = {
                'today': now.date(),
                'week': (now - timedelta(days=7)).date(),
                'month': (now - timedelta(days=30)).date(),
                'all_time': None
            }

            stats = {
                'overview': {
                    'total_orders': user.total_orders,
                    'successful_orders': user.successful_orders,
                    'failed_orders': user.failed_orders,
                    'success_rate': round(
                        (user.successful_orders / user.total_orders * 100) if user.total_orders > 0 else 0, 2),
                    'average_order_value': float(user.average_order_value),
                    'lifetime_value': float(user.lifetime_value),
                    'trust_score': float(user.trust_score),
                    'account_age_days': (now - datetime.fromisoformat(
                        user.created_at.replace('Z', '+00:00').replace('+00:00', ''))).days,
                    'role': user.role,
                    'is_vip': user.is_vip()
                },
                'financial': {
                    'current_balance': float(user.balance),
                    'total_deposited': float(user.total_deposited),
                    'total_withdrawn': float(user.total_withdrawn),
                    'total_spent': float(user.total_spent),
                    'referral_earnings': float(user.referral_earnings),
                    'profit': float(user.total_deposited) - float(user.total_withdrawn) - float(user.total_spent)
                },
                'periods': {}
            }

            # Статистика по періодах
            for period_name, start_date in periods.items():
                if start_date:
                    # Замовлення
                    orders_query = supabase.table('orders') \
                        .select('status, charge') \
                        .eq('user_id', user_id) \
                        .gte('created_at', start_date.isoformat())
                else:
                    orders_query = supabase.table('orders') \
                        .select('status, charge') \
                        .eq('user_id', user_id)

                orders_result = orders_query.execute()
                orders = orders_result.data or []

                period_stats = {
                    'orders_count': len(orders),
                    'orders_sum': sum(float(o['charge']) for o in orders),
                    'completed_orders': len([o for o in orders if o['status'] == 'completed']),
                    'deposits': 0,
                    'withdrawals': 0
                }

                # Транзакції
                if start_date:
                    trans_query = supabase.table('transactions') \
                        .select('type, amount') \
                        .eq('user_id', user_id) \
                        .gte('created_at', start_date.isoformat())
                else:
                    trans_query = supabase.table('transactions') \
                        .select('type, amount') \
                        .eq('user_id', user_id)

                trans_result = trans_query.execute()

                for t in (trans_result.data or []):
                    if t['type'] == TRANSACTION_TYPE.DEPOSIT:
                        period_stats['deposits'] += float(t['amount'])
                    elif t['type'] == TRANSACTION_TYPE.WITHDRAWAL:
                        period_stats['withdrawals'] += abs(float(t['amount']))

                stats['periods'][period_name] = period_stats

            # Топ сервіси
            services_result = supabase.table('orders') \
                .select('service_id, metadata') \
                .eq('user_id', user_id) \
                .execute()

            service_counts = {}
            for order in (services_result.data or []):
                service_name = order.get('metadata', {}).get('service_name', 'Unknown')
                service_counts[service_name] = service_counts.get(service_name, 0) + 1

            stats['top_services'] = sorted(
                [{'name': k, 'count': v} for k, v in service_counts.items()],
                key=lambda x: x['count'],
                reverse=True
            )[:10]

            # Кешуємо
            cache_set(cache_key, stats, ttl=300)

            return stats

        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return None

    @staticmethod
    def search_users(query: str = None, filters: Dict = None,
                     limit: int = 50, offset: int = 0) -> Tuple[List[UserProfile], int]:
        """Пошук користувачів (для адмінів)"""
        try:
            # Базовий запит
            count_query = supabase.table('users').select('id', count='exact')
            data_query = supabase.table('users').select('*')

            # Пошук по тексту
            if query:
                # Пошук по username, telegram_id, email
                search_filter = f"username.ilike.%{query}%,telegram_id.ilike.%{query}%,first_name.ilike.%{query}%"
                count_query = count_query.or_(search_filter)
                data_query = data_query.or_(search_filter)

            # Фільтри
            if filters:
                if filters.get('is_active') is not None:
                    count_query = count_query.eq('is_active', filters['is_active'])
                    data_query = data_query.eq('is_active', filters['is_active'])

                if filters.get('role'):
                    count_query = count_query.eq('role', filters['role'])
                    data_query = data_query.eq('role', filters['role'])

                if filters.get('is_admin') is not None:
                    count_query = count_query.eq('is_admin', filters['is_admin'])
                    data_query = data_query.eq('is_admin', filters['is_admin'])

                if filters.get('min_balance'):
                    count_query = count_query.gte('balance', filters['min_balance'])
                    data_query = data_query.gte('balance', filters['min_balance'])

                if filters.get('created_after'):
                    count_query = count_query.gte('created_at', filters['created_after'])
                    data_query = data_query.gte('created_at', filters['created_after'])

            # Отримуємо кількість
            count_result = count_query.execute()
            total_count = count_result.count if hasattr(count_result, 'count') else 0

            # Отримуємо дані
            data_result = data_query \
                .order('created_at', desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()

            users = [UserProfile(u) for u in (data_result.data or [])]

            return users, total_count

        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return [], 0

    @staticmethod
    def ban_user(user_id: str, reason: str, admin_id: str) -> bool:
        """Заблокувати користувача"""
        try:
            result = supabase.table('users').update({
                'is_active': False,
                'banned_at': datetime.utcnow().isoformat(),
                'ban_reason': reason,
                'role': 'banned',  # Оновлюємо роль на banned
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', user_id).execute()

            if result.data:
                # Логуємо дію адміна
                supabase.table('admin_actions').insert({
                    'admin_id': admin_id,
                    'action': 'ban_user',
                    'target_user_id': user_id,
                    'details': {'reason': reason},
                    'created_at': datetime.utcnow().isoformat()
                }).execute()

                # Створюємо сповіщення для користувача
                UserNotification.create(
                    user_id=user_id,
                    notification_type='system_message',
                    title='Ваш акаунт заблоковано',
                    message=f'Причина: {reason}',
                    data={'banned_at': datetime.utcnow().isoformat()}
                )

                # Завершуємо всі активні сесії
                supabase.table('user_sessions').update({
                    'is_active': False
                }).eq('user_id', user_id).eq('is_active', True).execute()

                # Інвалідуємо кеш
                redis_client.delete(f"user_profile:{user_id}")
                redis_client.delete(f"user:{user_id}")
                redis_client.delete(f"balance_info:{user_id}")

                # Логуємо подію
                UserActivity(user_id).log_action('account_banned', {'reason': reason})

                return True

            return False

        except Exception as e:
            logger.error(f"Error banning user: {e}")
            return False

    @staticmethod
    def unban_user(user_id: str, admin_id: str) -> bool:
        """Розблокувати користувача"""
        try:
            # Отримуємо користувача для визначення попередньої ролі
            user = UserProfile.get_by_id(user_id)
            if not user:
                return False

            # Визначаємо яку роль встановити
            new_role = USER_ROLES['DEFAULT']
            if user.is_admin:
                new_role = 'admin'
            elif user.is_vip():
                new_role = USER_ROLES['VIP']
            elif user.is_premium:
                new_role = USER_ROLES['PREMIUM']

            result = supabase.table('users').update({
                'is_active': True,
                'banned_at': None,
                'ban_reason': None,
                'role': new_role,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', user_id).execute()

            if result.data:
                # Логуємо дію адміна
                supabase.table('admin_actions').insert({
                    'admin_id': admin_id,
                    'action': 'unban_user',
                    'target_user_id': user_id,
                    'details': {'restored_role': new_role},
                    'created_at': datetime.utcnow().isoformat()
                }).execute()

                # Створюємо сповіщення
                UserNotification.create(
                    user_id=user_id,
                    notification_type='system_message',
                    title='Ваш акаунт розблоковано',
                    message='Ви знову можете користуватися сервісом',
                    data={'unbanned_at': datetime.utcnow().isoformat()}
                )

                # Інвалідуємо кеш
                redis_client.delete(f"user_profile:{user_id}")
                redis_client.delete(f"user:{user_id}")

                return True

            return False

        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            return False


class UserTransactionService:
    """Сервіс для роботи з транзакціями"""

    @staticmethod
    def get_transaction_summary(user_id: str, period_days: int = 30) -> Dict[str, Any]:
        """Отримати зведення по транзакціях"""
        try:
            since = datetime.utcnow() - timedelta(days=period_days)

            result = supabase.table('transactions') \
                .select('type, amount') \
                .eq('user_id', user_id) \
                .gte('created_at', since.isoformat()) \
                .execute()

            summary = {
                'deposits': 0,
                'withdrawals': 0,
                'orders': 0,
                'referral_bonuses': 0,
                'refunds': 0,
                'total_in': 0,
                'total_out': 0,
                'transactions_count': len(result.data or [])
            }

            for t in (result.data or []):
                amount = float(t['amount'])

                if t['type'] == TRANSACTION_TYPE.DEPOSIT:
                    summary['deposits'] += amount
                    summary['total_in'] += amount
                elif t['type'] == TRANSACTION_TYPE.WITHDRAWAL:
                    summary['withdrawals'] += abs(amount)
                    summary['total_out'] += abs(amount)
                elif t['type'] == TRANSACTION_TYPE.ORDER:
                    summary['orders'] += abs(amount)
                    summary['total_out'] += abs(amount)
                elif t['type'] == TRANSACTION_TYPE.REFERRAL_BONUS:
                    summary['referral_bonuses'] += amount
                    summary['total_in'] += amount
                elif t['type'] == TRANSACTION_TYPE.REFUND:
                    summary['refunds'] += amount
                    summary['total_in'] += amount

            summary['net_change'] = summary['total_in'] - summary['total_out']

            return summary

        except Exception as e:
            logger.error(f"Error getting transaction summary: {e}")
            return {}

    @staticmethod
    def export_transactions(user_id: str, format: str = 'csv',
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> Optional[str]:
        """Експорт транзакцій в CSV/Excel"""
        try:
            query = supabase.table('transactions') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True)

            if start_date:
                query = query.gte('created_at', start_date.isoformat())
            if end_date:
                query = query.lte('created_at', end_date.isoformat())

            result = query.execute()

            if not result.data:
                return None

            # Підготовка даних для експорту
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Заголовки
            writer.writerow([
                'Date', 'Type', 'Amount', 'Balance Before',
                'Balance After', 'Description', 'Transaction ID'
            ])

            # Дані
            for t in result.data:
                writer.writerow([
                    format_datetime(t['created_at'], 'full'),
                    t['type'].replace('_', ' ').title(),
                    format_price(t['amount'], 'USD'),
                    format_price(t.get('balance_before', 0), 'USD'),
                    format_price(t.get('balance_after', 0), 'USD'),
                    t.get('description', ''),
                    t['id'][:8]
                ])

            return output.getvalue()

        except Exception as e:
            logger.error(f"Error exporting transactions: {e}")
            return None

    @staticmethod
    def create_transaction_with_balance_update(user_id: str, transaction_type: str,
                                               amount: float, description: str = None,
                                               metadata: Dict = None) -> Tuple[bool, Optional[str]]:
        """Створити транзакцію з атомарним оновленням балансу"""
        try:
            # Отримуємо користувача
            user = UserProfile.get_by_id(user_id)
            if not user:
                return False, "Користувач не знайдений"

            # Визначаємо операцію
            if amount > 0:
                operation = 'add'
                balance_before = user.balance
                balance_after = user.balance + amount
            else:
                operation = 'subtract'
                balance_before = user.balance
                balance_after = user.balance - abs(amount)

                # Перевірка достатності коштів
                if balance_after < 0:
                    return False, "Недостатньо коштів"

            # Оновлюємо баланс
            success = supabase.update_user_balance(user_id, abs(amount), operation)
            if not success:
                return False, "Помилка оновлення балансу"

            # Створюємо транзакцію
            transaction_data = {
                'user_id': user_id,
                'type': transaction_type,
                'amount': amount,
                'balance_before': balance_before,
                'balance_after': balance_after,
                'description': description or f'{transaction_type.replace("_", " ").title()}',
                'metadata': metadata or {}
            }

            result = supabase.create_transaction(transaction_data)
            if result:
                # Інвалідуємо кеш
                redis_client.delete(f"balance_info:{user_id}")
                redis_client.delete(f"user_profile:{user_id}")

                return True, None
            else:
                # Відкатуємо баланс якщо не вдалося створити транзакцію
                reverse_operation = 'subtract' if operation == 'add' else 'add'
                supabase.update_user_balance(user_id, abs(amount), reverse_operation)
                return False, "Помилка створення транзакції"

        except Exception as e:
            logger.error(f"Error creating transaction with balance update: {e}")
            return False, "Внутрішня помилка"