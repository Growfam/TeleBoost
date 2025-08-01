# backend/supabase_client.py
"""
TeleBoost Supabase Client
Підключення до Supabase БД з оптимізованими запитами та покращеною обробкою помилок
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from supabase import create_client, Client
from datetime import datetime, timezone
from contextlib import contextmanager
import time

from backend.config import config

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Клієнт для роботи з Supabase з покращеною продуктивністю"""

    def __init__(self):
        """Ініціалізація Supabase клієнта"""
        self._client = None
        self._last_connection_check = 0
        self._connection_check_interval = 60  # секунд

        try:
            if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
                raise ValueError("Supabase credentials not configured")

            self._client = create_client(
                supabase_url=config.SUPABASE_URL,
                supabase_key=config.SUPABASE_SERVICE_KEY
            )

            # Тестуємо з'єднання
            self._test_initial_connection()
            logger.info("✅ Supabase connected successfully")

        except Exception as e:
            logger.error(f"❌ Supabase connection failed: {e}")
            self._client = None

    def _test_initial_connection(self):
        """Початкова перевірка з'єднання"""
        # Простий запит для перевірки
        self._client.table('users').select('id').limit(1).execute()

    @property
    def client(self) -> Optional[Client]:
        """Отримати клієнт з перевіркою з'єднання"""
        if not self._client:
            return None

        # Періодична перевірка з'єднання
        current_time = time.time()
        if current_time - self._last_connection_check > self._connection_check_interval:
            if not self.test_connection():
                logger.warning("Lost connection to Supabase")
                return None
            self._last_connection_check = current_time

        return self._client

    def table(self, table_name: str):
        """Отримати референс на таблицю з перевіркою"""
        if not self.client:
            raise ConnectionError("Supabase client not initialized")
        return self.client.table(table_name)

    def rpc(self, function_name: str, params: Dict[str, Any] = None):
        """Виклик RPC функції з логуванням"""
        if not self.client:
            raise ConnectionError("Supabase client not initialized")

        logger.debug(f"Calling RPC: {function_name} with params: {params}")

        try:
            result = self.client.rpc(function_name, params or {})
            return result
        except Exception as e:
            logger.error(f"RPC call failed: {function_name}, error: {e}")
            raise

    @contextmanager
    def transaction(self):
        """Контекстний менеджер для транзакцій (заглушка для майбутнього)"""
        # Supabase поки не підтримує транзакції через клієнт
        # Але ми готуємо інтерфейс для майбутнього
        yield self

    # === User Methods ===

    def get_user_by_telegram_id(self, telegram_id: str) -> Optional[Dict]:
        """Отримати користувача за Telegram ID"""
        try:
            result = self.table('users').select('*').eq('telegram_id', telegram_id).single().execute()
            return result.data
        except Exception as e:
            if "No rows found" not in str(e):
                logger.error(f"Error getting user by telegram_id {telegram_id}: {e}")
            return None

    def create_user(self, user_data: Dict) -> Optional[Dict]:
        """Створити нового користувача"""
        try:
            # Додаємо timestamp та дефолтні значення
            user_data['created_at'] = datetime.now(timezone.utc).isoformat()
            user_data['updated_at'] = user_data['created_at']

            # Дефолтні значення для нових полів
            user_data.setdefault('role', 'default')
            user_data.setdefault('trust_score', 100.0)
            user_data.setdefault('withdrawal_limit', 50000)
            user_data.setdefault('daily_order_limit', 100)
            user_data.setdefault('notes', {})
            user_data.setdefault('tags', [])

            result = self.table('users').insert(user_data).execute()

            if result.data:
                logger.info(f"Created user: {user_data.get('telegram_id')}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    def update_user(self, user_id: str, update_data: Dict) -> Optional[Dict]:
        """Оновити дані користувача"""
        try:
            update_data['updated_at'] = datetime.now(timezone.utc).isoformat()

            result = self.table('users').update(update_data).eq('id', user_id).execute()

            if result.data:
                logger.info(f"Updated user {user_id}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return None

    # === Balance Methods (ВИПРАВЛЕНО) ===

    def get_user_balance(self, user_id: str) -> float:
        """Отримати баланс користувача"""
        try:
            result = self.table('users').select('balance').eq('id', user_id).single().execute()
            return float(result.data.get('balance', 0)) if result.data else 0.0
        except Exception as e:
            logger.error(f"Error getting balance for user {user_id}: {e}")
            return 0.0

    def update_user_balance(self, user_id: str, amount: float, operation: str = 'add') -> bool:
        """Оновити баланс користувача (ВИПРАВЛЕНО)"""
        try:
            # Правильний формат параметрів для RPC
            if operation == 'add':
                result = self.rpc('increment_balance', {
                    'user_id': user_id,  # Правильна назва параметра
                    'amount': amount
                }).execute()
            else:  # subtract
                result = self.rpc('decrement_balance', {
                    'user_id': user_id,  # Правильна назва параметра
                    'amount': amount
                }).execute()

            # Логуємо результат
            success = result.data is True if result.data is not None else False

            if success:
                logger.info(f"Balance updated for user {user_id}: {operation} {amount}")
            else:
                logger.warning(f"Balance update failed for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error updating balance for user {user_id}: {e}")
            return False

    # === Transaction Methods ===

    def create_transaction(self, transaction_data: Dict) -> Optional[Dict]:
        """Створити транзакцію"""
        try:
            transaction_data['created_at'] = datetime.now(timezone.utc).isoformat()

            # Переконуємося що balance_before та balance_after є числами
            if 'balance_before' in transaction_data:
                transaction_data['balance_before'] = float(transaction_data['balance_before'])
            if 'balance_after' in transaction_data:
                transaction_data['balance_after'] = float(transaction_data['balance_after'])

            result = self.table('transactions').insert(transaction_data).execute()

            if result.data:
                logger.info(f"Created transaction for user {transaction_data.get('user_id')}: "
                            f"{transaction_data.get('type')} {transaction_data.get('amount')}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return None

    def get_user_transactions(self, user_id: str, limit: int = 50, offset: int = 0,
                              transaction_type: Optional[str] = None) -> List[Dict]:
        """Отримати транзакції користувача з фільтрацією"""
        try:
            query = self.table('transactions') \
                .select('*') \
                .eq('user_id', user_id)

            if transaction_type:
                query = query.eq('type', transaction_type)

            result = query.order('created_at', desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Error getting transactions for user {user_id}: {e}")
            return []

    # === Order Methods ===

    def create_order(self, order_data: Dict) -> Optional[Dict]:
        """Створити замовлення"""
        try:
            order_data['created_at'] = datetime.now(timezone.utc).isoformat()
            order_data['updated_at'] = order_data['created_at']

            # Переконуємося що charge є числом
            if 'charge' in order_data:
                order_data['charge'] = float(order_data['charge'])

            result = self.table('orders').insert(order_data).execute()

            if result.data:
                order = result.data[0]
                logger.info(f"Created order {order['id']} for user {order_data.get('user_id')}")

                # Оновлюємо статистику користувача
                self.rpc('update_user_stats', {'p_user_id': order_data['user_id']}).execute()

                return order
            return None

        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    def get_order(self, order_id: str) -> Optional[Dict]:
        """Отримати замовлення за ID"""
        try:
            result = self.table('orders').select('*').eq('id', order_id).single().execute()
            return result.data
        except Exception as e:
            if "No rows found" not in str(e):
                logger.error(f"Error getting order {order_id}: {e}")
            return None

    def update_order(self, order_id: str, update_data: Dict) -> Optional[Dict]:
        """Оновити замовлення"""
        try:
            update_data['updated_at'] = datetime.now(timezone.utc).isoformat()

            result = self.table('orders').update(update_data).eq('id', order_id).execute()

            if result.data:
                order = result.data[0]
                logger.info(f"Updated order {order_id}: status={update_data.get('status')}")

                # Оновлюємо статистику користувача якщо змінився статус
                if 'status' in update_data:
                    self.rpc('update_user_stats', {'p_user_id': order['user_id']}).execute()

                return order
            return None

        except Exception as e:
            logger.error(f"Error updating order {order_id}: {e}")
            return None

    def get_user_orders(self, user_id: str, status: Optional[str] = None,
                        limit: int = 50, offset: int = 0) -> List[Dict]:
        """Отримати замовлення користувача"""
        try:
            query = self.table('orders') \
                .select('*, services(name, type, category)') \
                .eq('user_id', user_id)

            if status:
                query = query.eq('status', status)

            result = query.order('created_at', desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Error getting orders for user {user_id}: {e}")
            return []

    # === Payment Methods ===

    def create_payment(self, payment_data: Dict) -> Optional[Dict]:
        """Створити платіж"""
        try:
            payment_data['created_at'] = datetime.now(timezone.utc).isoformat()
            payment_data['updated_at'] = payment_data['created_at']

            # Переконуємося що amount є числом
            if 'amount' in payment_data:
                payment_data['amount'] = float(payment_data['amount'])

            result = self.table('payments').insert(payment_data).execute()

            if result.data:
                logger.info(f"Created payment {result.data[0]['id']} for user {payment_data.get('user_id')}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            return None

    def get_payment(self, payment_id: str) -> Optional[Dict]:
        """Отримати платіж за ID"""
        try:
            result = self.table('payments').select('*').eq('id', payment_id).single().execute()
            return result.data
        except Exception as e:
            if "No rows found" not in str(e):
                logger.error(f"Error getting payment {payment_id}: {e}")
            return None

    def get_payment_by_provider_id(self, provider_id: str, provider: str) -> Optional[Dict]:
        """Отримати платіж за ID провайдера"""
        try:
            result = self.table('payments') \
                .select('*') \
                .eq('payment_id', provider_id) \
                .eq('provider', provider) \
                .single() \
                .execute()
            return result.data
        except Exception as e:
            if "No rows found" not in str(e):
                logger.error(f"Error getting payment by provider_id {provider_id}: {e}")
            return None

    def update_payment(self, payment_id: str, update_data: Dict) -> Optional[Dict]:
        """Оновити платіж"""
        try:
            update_data['updated_at'] = datetime.now(timezone.utc).isoformat()

            result = self.table('payments').update(update_data).eq('id', payment_id).execute()

            if result.data:
                logger.info(f"Updated payment {payment_id}: status={update_data.get('status')}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Error updating payment {payment_id}: {e}")
            return None

    # === Service Methods ===

    def get_all_services(self, only_active: bool = True) -> List[Dict]:
        """Отримати всі сервіси"""
        try:
            query = self.table('services').select('*')

            if only_active:
                query = query.eq('is_active', True)

            result = query.order('position', desc=False).execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Error getting services: {e}")
            return []

    def get_service(self, service_id: int) -> Optional[Dict]:
        """Отримати сервіс за ID"""
        try:
            result = self.table('services').select('*').eq('id', service_id).single().execute()
            return result.data
        except Exception as e:
            if "No rows found" not in str(e):
                logger.error(f"Error getting service {service_id}: {e}")
            return None

    def upsert_service(self, service_data: Dict) -> Optional[Dict]:
        """Створити або оновити сервіс"""
        try:
            service_data['updated_at'] = datetime.now(timezone.utc).isoformat()

            # Якщо немає created_at, додаємо
            if 'created_at' not in service_data and 'id' not in service_data:
                service_data['created_at'] = service_data['updated_at']

            result = self.table('services').upsert(service_data).execute()

            if result.data:
                logger.info(f"Upserted service {service_data.get('id')}")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Error upserting service: {e}")
            return None

    def deactivate_services(self, service_ids: List[int]) -> bool:
        """Деактивувати сервіси"""
        try:
            result = self.table('services') \
                .update({'is_active': False, 'updated_at': datetime.now(timezone.utc).isoformat()}) \
                .in_('id', service_ids) \
                .execute()

            logger.info(f"Deactivated {len(service_ids)} services")
            return True

        except Exception as e:
            logger.error(f"Error deactivating services: {e}")
            return False

    # === Referral Methods (ВИПРАВЛЕНО) ===

    def create_referral(self, referrer_id: str, referred_id: str, level: int = 1) -> Optional[Dict]:
        """Створити реферальний зв'язок"""
        try:
            referral_data = {
                'referrer_id': referrer_id,
                'referred_id': referred_id,
                'level': level,
                'bonus_paid': False,
                'bonus_amount': 0,
                'is_active': True,
                'created_at': datetime.now(timezone.utc).isoformat()
            }

            result = self.table('referrals').insert(referral_data).execute()

            if result.data:
                logger.info(f"Created referral: {referrer_id} -> {referred_id} (level {level})")
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Error creating referral: {e}")
            return None

    def get_referrals_by_level(self, referrer_id: str, level: int) -> List[Dict]:
        """Отримати рефералів певного рівня"""
        try:
            result = self.table('referrals') \
                .select(
                '*, referred_user:users!referred_id(id, telegram_id, username, first_name, last_name, balance, created_at, total_deposited)') \
                .eq('referrer_id', referrer_id) \
                .eq('level', level) \
                .eq('is_active', True) \
                .order('created_at', desc=True) \
                .execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Error getting referrals by level: {e}")
            return []

    def update_referral_stats(self, referral_id: str, deposit_amount: float, bonus_amount: float) -> bool:
        """Оновити статистику реферала після депозиту (ВИПРАВЛЕНО)"""
        try:
            # Оновлюємо total_deposits
            deposits_result = self.rpc('increment_value', {
                'table_name': 'referrals',
                'column_name': 'total_deposits',
                'row_id': referral_id,
                'increment_by': deposit_amount
            }).execute()

            # Оновлюємо total_bonuses_generated
            bonuses_result = self.rpc('increment_value', {
                'table_name': 'referrals',
                'column_name': 'total_bonuses_generated',
                'row_id': referral_id,
                'increment_by': bonus_amount
            }).execute()

            # Оновлюємо інші поля
            update_result = self.table('referrals').update({
                'last_deposit_at': datetime.now(timezone.utc).isoformat(),
                'bonus_paid': True,
                'bonus_amount': bonus_amount
            }).eq('id', referral_id).execute()

            success = bool(deposits_result.data and bonuses_result.data and update_result.data)

            if success:
                logger.info(f"Updated referral stats {referral_id}: deposit={deposit_amount}, bonus={bonus_amount}")

            return success

        except Exception as e:
            logger.error(f"Error updating referral stats: {e}")
            return False

    def get_user_referrals(self, user_id: str) -> List[Dict]:
        """Отримати рефералів користувача (для сумісності)"""
        try:
            # Отримуємо рефералів 1-го рівня
            level1 = self.get_referrals_by_level(user_id, 1)

            # Конвертуємо в старий формат
            referrals = []
            for ref in level1:
                if ref.get('referred_user'):
                    user = ref['referred_user']
                    referrals.append({
                        'id': user['id'],
                        'telegram_id': user['telegram_id'],
                        'username': user.get('username', ''),
                        'first_name': user.get('first_name', ''),
                        'created_at': user['created_at']
                    })

            return referrals

        except Exception as e:
            logger.error(f"Error getting referrals for user {user_id}: {e}")
            return []

    def get_referral_stats(self, user_id: str) -> Dict:
        """Отримати статистику рефералів"""
        try:
            # Кількість рефералів по рівнях
            level1 = self.get_referrals_by_level(user_id, 1)
            level2 = self.get_referrals_by_level(user_id, 2)

            # Загальний заробіток
            user = self.get_user_by_id(user_id)
            total_earned = float(user.get('referral_earnings', 0)) if user else 0

            return {
                'count': len(level1),  # Для сумісності показуємо тільки 1-й рівень
                'level1_count': len(level1),
                'level2_count': len(level2),
                'total_count': len(level1) + len(level2),
                'total_earned': total_earned,
                'referrals': self.get_user_referrals(user_id)  # Для сумісності
            }

        except Exception as e:
            logger.error(f"Error getting referral stats for user {user_id}: {e}")
            return {'count': 0, 'total_earned': 0, 'referrals': []}

    def get_referral_by_users(self, referrer_id: str, referred_id: str) -> Optional[Dict]:
        """Отримати реферальний зв'язок між двома користувачами"""
        try:
            result = self.table('referrals') \
                .select('*') \
                .eq('referrer_id', referrer_id) \
                .eq('referred_id', referred_id) \
                .single() \
                .execute()

            return result.data

        except Exception as e:
            if "No rows found" not in str(e):
                logger.error(f"Error getting referral by users: {e}")
            return None

    def get_referral_chain(self, user_id: str) -> Dict[str, List[Dict]]:
        """Отримати повний ланцюг рефералів (2 рівні)"""
        try:
            # Рефералі першого рівня
            level1 = self.get_referrals_by_level(user_id, 1)

            # Рефералі другого рівня
            level2 = []
            for ref in level1:
                if ref.get('referred_id'):
                    # Отримуємо рефералів кожного реферала 1-го рівня
                    sub_refs = self.get_referrals_by_level(ref['referred_id'], 1)

                    # Додаємо як рефералів 2-го рівня основного користувача
                    for sub_ref in sub_refs:
                        sub_ref['level'] = 2
                        sub_ref['referrer_id'] = user_id
                        level2.append(sub_ref)

            return {
                'level1': level1,
                'level2': level2
            }

        except Exception as e:
            logger.error(f"Error getting referral chain: {e}")
            return {'level1': [], 'level2': []}

    def process_referral_bonus_transaction(self, referrer_id: str, amount: float,
                                           referred_user_id: str, deposit_amount: float,
                                           level: int) -> bool:
        """Обробити реферальний бонус в одній транзакції (ВИПРАВЛЕНО)"""
        try:
            result = self.rpc('process_referral_bonus', {
                'p_referrer_id': referrer_id,
                'p_amount': amount,
                'p_referred_user_id': referred_user_id,
                'p_deposit_amount': deposit_amount,
                'p_level': level
            }).execute()

            success = bool(result.data)

            if success:
                logger.info(f"Processed referral bonus: {referrer_id} <- {amount} (level {level})")
            else:
                logger.error(f"Failed to process referral bonus: {result}")

            return success

        except Exception as e:
            logger.error(f"Error in referral bonus transaction: {e}")
            return False

    # === Helper Methods ===

    def test_connection(self) -> bool:
        """Тестувати з'єднання"""
        try:
            # Простий запит для перевірки
            self.table('users').select('id').limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Отримати користувача за ID"""
        try:
            result = self.table('users').select('*').eq('id', user_id).single().execute()
            return result.data
        except Exception as e:
            if "No rows found" not in str(e):
                logger.error(f"Error getting user by id {user_id}: {e}")
            return None

    # === Activity Methods ===

    def log_user_activity(self, user_id: str, action: str, details: Optional[Dict] = None) -> bool:
        """Записати активність користувача"""
        try:
            activity_data = {
                'user_id': user_id,
                'action': action,
                'details': details or {},
                'created_at': datetime.now(timezone.utc).isoformat()
            }

            result = self.table('user_activities').insert(activity_data).execute()
            return bool(result.data)

        except Exception as e:
            logger.error(f"Error logging user activity: {e}")
            return False

    # === Notification Methods ===

    def create_user_notification(self, user_id: str, notification_type: str,
                                 title: str, message: str, data: Optional[Dict] = None) -> bool:
        """Створити сповіщення для користувача"""
        try:
            notification_data = {
                'user_id': user_id,
                'type': notification_type,
                'title': title,
                'message': message,
                'data': data or {},
                'is_read': False,
                'created_at': datetime.now(timezone.utc).isoformat()
            }

            result = self.table('user_notifications').insert(notification_data).execute()

            if result.data:
                logger.info(f"Created notification for user {user_id}: {title}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return False

    # === Admin Methods ===

    def log_admin_action(self, admin_id: str, action: str, target_user_id: Optional[str] = None,
                         details: Optional[Dict] = None) -> bool:
        """Записати дію адміністратора"""
        try:
            action_data = {
                'admin_id': admin_id,
                'action': action,
                'target_user_id': target_user_id,
                'details': details or {},
                'created_at': datetime.now(timezone.utc).isoformat()
            }

            result = self.table('admin_actions').insert(action_data).execute()

            if result.data:
                logger.info(f"Admin action logged: {admin_id} -> {action}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error logging admin action: {e}")
            return False

    # === Batch Operations ===

    def batch_update_orders_status(self, order_ids: List[str], new_status: str) -> int:
        """Масове оновлення статусу замовлень"""
        try:
            result = self.table('orders') \
                .update({
                'status': new_status,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }) \
                .in_('id', order_ids) \
                .execute()

            updated_count = len(result.data or [])
            logger.info(f"Batch updated {updated_count} orders to status {new_status}")

            return updated_count

        except Exception as e:
            logger.error(f"Error in batch update orders: {e}")
            return 0

    # === Statistics Methods ===

    def get_system_stats(self) -> Dict[str, Any]:
        """Отримати системну статистику"""
        try:
            stats = {}

            # Кількість користувачів
            users_result = self.table('users').select('id', count='exact').execute()
            stats['total_users'] = users_result.count if hasattr(users_result, 'count') else 0

            # Кількість замовлень
            orders_result = self.table('orders').select('id', count='exact').execute()
            stats['total_orders'] = orders_result.count if hasattr(orders_result, 'count') else 0

            # Активні сервіси
            services_result = self.table('services').select('id', count='exact').eq('is_active', True).execute()
            stats['active_services'] = services_result.count if hasattr(services_result, 'count') else 0

            return stats

        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}


# Створюємо глобальний екземпляр
supabase = SupabaseClient()