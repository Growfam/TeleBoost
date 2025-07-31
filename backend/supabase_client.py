# backend/supabase_client.py
"""
TeleBoost Supabase Client
Підключення до Supabase БД
"""
import logging
from typing import Dict, List, Optional, Any
from supabase import create_client, Client
from datetime import datetime

from backend.config import config

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Клієнт для роботи з Supabase"""

    def __init__(self):
        """Ініціалізація Supabase клієнта"""
        try:
            if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
                raise ValueError("Supabase credentials not configured")

            self.client: Client = create_client(
                supabase_url=config.SUPABASE_URL,
                supabase_key=config.SUPABASE_SERVICE_KEY
            )
            logger.info("✅ Supabase connected successfully")

        except Exception as e:
            logger.error(f"❌ Supabase connection failed: {e}")
            self.client = None

    def table(self, table_name: str):
        """Отримати референс на таблицю"""
        if not self.client:
            raise ConnectionError("Supabase client not initialized")
        return self.client.table(table_name)

    def rpc(self, function_name: str, params: Dict[str, Any] = None):
        """Виклик RPC функції"""
        if not self.client:
            raise ConnectionError("Supabase client not initialized")
        return self.client.rpc(function_name, params or {})

    # === User Methods ===

    def get_user_by_telegram_id(self, telegram_id: str) -> Optional[Dict]:
        """Отримати користувача за Telegram ID"""
        try:
            result = self.table('users').select('*').eq('telegram_id', telegram_id).single().execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting user by telegram_id {telegram_id}: {e}")
            return None

    def create_user(self, user_data: Dict) -> Optional[Dict]:
        """Створити нового користувача"""
        try:
            # Додаємо timestamp
            user_data['created_at'] = datetime.utcnow().isoformat()
            user_data['updated_at'] = user_data['created_at']

            result = self.table('users').insert(user_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    def update_user(self, user_id: str, update_data: Dict) -> Optional[Dict]:
        """Оновити дані користувача"""
        try:
            update_data['updated_at'] = datetime.utcnow().isoformat()

            result = self.table('users').update(update_data).eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return None

    # === Balance Methods ===

    def get_user_balance(self, user_id: str) -> float:
        """Отримати баланс користувача"""
        try:
            result = self.table('users').select('balance').eq('id', user_id).single().execute()
            return float(result.data.get('balance', 0)) if result.data else 0.0
        except Exception as e:
            logger.error(f"Error getting balance for user {user_id}: {e}")
            return 0.0

    def update_user_balance(self, user_id: str, amount: float, operation: str = 'add') -> bool:
        """Оновити баланс користувача"""
        try:
            # Використовуємо RPC для атомарного оновлення
            if operation == 'add':
                result = self.rpc('increment_balance', {
                    'user_id': user_id,
                    'amount': amount
                }).execute()
            else:  # subtract
                result = self.rpc('decrement_balance', {
                    'user_id': user_id,
                    'amount': amount
                }).execute()

            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating balance for user {user_id}: {e}")
            return False

    # === Transaction Methods ===

    def create_transaction(self, transaction_data: Dict) -> Optional[Dict]:
        """Створити транзакцію"""
        try:
            transaction_data['created_at'] = datetime.utcnow().isoformat()

            result = self.table('transactions').insert(transaction_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return None

    def get_user_transactions(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Отримати транзакції користувача"""
        try:
            result = self.table('transactions') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
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
            order_data['created_at'] = datetime.utcnow().isoformat()
            order_data['updated_at'] = order_data['created_at']

            result = self.table('orders').insert(order_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    def get_order(self, order_id: str) -> Optional[Dict]:
        """Отримати замовлення за ID"""
        try:
            result = self.table('orders').select('*').eq('id', order_id).single().execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {e}")
            return None

    def update_order(self, order_id: str, update_data: Dict) -> Optional[Dict]:
        """Оновити замовлення"""
        try:
            update_data['updated_at'] = datetime.utcnow().isoformat()

            result = self.table('orders').update(update_data).eq('id', order_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating order {order_id}: {e}")
            return None

    def get_user_orders(self, user_id: str, status: Optional[str] = None,
                        limit: int = 50, offset: int = 0) -> List[Dict]:
        """Отримати замовлення користувача"""
        try:
            query = self.table('orders').select('*').eq('user_id', user_id)

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
            payment_data['created_at'] = datetime.utcnow().isoformat()
            payment_data['updated_at'] = payment_data['created_at']

            result = self.table('payments').insert(payment_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            return None

    def get_payment(self, payment_id: str) -> Optional[Dict]:
        """Отримати платіж за ID"""
        try:
            result = self.table('payments').select('*').eq('id', payment_id).single().execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting payment {payment_id}: {e}")
            return None

    def update_payment(self, payment_id: str, update_data: Dict) -> Optional[Dict]:
        """Оновити платіж"""
        try:
            update_data['updated_at'] = datetime.utcnow().isoformat()

            result = self.table('payments').update(update_data).eq('id', payment_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating payment {payment_id}: {e}")
            return None

    # === Service Methods ===

    def get_all_services(self) -> List[Dict]:
        """Отримати всі сервіси"""
        try:
            result = self.table('services').select('*').eq('is_active', True).execute()
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
            logger.error(f"Error getting service {service_id}: {e}")
            return None

    def upsert_service(self, service_data: Dict) -> Optional[Dict]:
        """Створити або оновити сервіс"""
        try:
            service_data['updated_at'] = datetime.utcnow().isoformat()

            result = self.table('services').upsert(service_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error upserting service: {e}")
            return None

    # === NEW Referral Methods для дворівневої системи ===

    def create_referral(self, referrer_id: str, referred_id: str, level: int = 1) -> Optional[Dict]:
        """
        Створити реферальний зв'язок

        Args:
            referrer_id: ID реферера
            referred_id: ID реферала
            level: Рівень реферала (1 або 2)
        """
        try:
            referral_data = {
                'referrer_id': referrer_id,
                'referred_id': referred_id,
                'level': level,
                'bonus_paid': False,
                'bonus_amount': 0,
                'is_active': True,
                'created_at': datetime.utcnow().isoformat()
            }

            result = self.table('referrals').insert(referral_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating referral: {e}")
            return None

    def get_referrals_by_level(self, referrer_id: str, level: int) -> List[Dict]:
        """
        Отримати рефералів певного рівня

        Args:
            referrer_id: ID реферера
            level: Рівень (1 або 2)
        """
        try:
            result = self.table('referrals') \
                .select(
                '*, referred_user:users!referred_id(id, telegram_id, username, first_name, last_name, balance, created_at)') \
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
        """
        Оновити статистику реферала після депозиту

        Args:
            referral_id: ID запису в таблиці referrals
            deposit_amount: Сума депозиту
            bonus_amount: Сума нарахованого бонусу
        """
        try:
            # Оновлюємо статистику
            update_data = {
                'total_deposits': self.client.rpc('increment_value', {
                    'table_name': 'referrals',
                    'column_name': 'total_deposits',
                    'row_id': referral_id,
                    'increment_by': deposit_amount
                }),
                'total_bonuses_generated': self.client.rpc('increment_value', {
                    'table_name': 'referrals',
                    'column_name': 'total_bonuses_generated',
                    'row_id': referral_id,
                    'increment_by': bonus_amount
                }),
                'last_deposit_at': datetime.utcnow().isoformat(),
                'bonus_paid': True
            }

            result = self.table('referrals').update(update_data).eq('id', referral_id).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating referral stats: {e}")
            return False

    def get_user_referrals(self, user_id: str) -> List[Dict]:
        """Отримати рефералів користувача (старий метод для сумісності)"""
        try:
            result = self.table('users') \
                .select('id, telegram_id, username, first_name, created_at') \
                .eq('referred_by', user_id) \
                .execute()

            return result.data or []
        except Exception as e:
            logger.error(f"Error getting referrals for user {user_id}: {e}")
            return []

    def get_referral_stats(self, user_id: str) -> Dict:
        """Отримати статистику рефералів (старий метод для сумісності)"""
        try:
            # Кількість рефералів
            referrals = self.get_user_referrals(user_id)

            # Сума заробітку з рефералів
            result = self.table('transactions') \
                .select('amount') \
                .eq('user_id', user_id) \
                .eq('type', 'referral_bonus') \
                .execute()

            total_earned = sum(float(t.get('amount', 0)) for t in (result.data or []))

            return {
                'count': len(referrals),
                'total_earned': total_earned,
                'referrals': referrals
            }
        except Exception as e:
            logger.error(f"Error getting referral stats for user {user_id}: {e}")
            return {'count': 0, 'total_earned': 0, 'referrals': []}

    def get_referral_by_users(self, referrer_id: str, referred_id: str) -> Optional[Dict]:
        """
        Отримати реферальний зв'язок між двома користувачами

        Args:
            referrer_id: ID реферера
            referred_id: ID реферала
        """
        try:
            result = self.table('referrals') \
                .select('*') \
                .eq('referrer_id', referrer_id) \
                .eq('referred_id', referred_id) \
                .single() \
                .execute()

            return result.data
        except Exception as e:
            logger.error(f"Error getting referral by users: {e}")
            return None

    def get_referral_chain(self, user_id: str) -> Dict[str, List[Dict]]:
        """
        Отримати повний ланцюг рефералів (2 рівні)

        Args:
            user_id: ID користувача

        Returns:
            Словник з рефералами по рівнях
        """
        try:
            # Рефералі першого рівня
            level1 = self.get_referrals_by_level(user_id, 1)

            # Рефералі другого рівня (рефералі рефералів)
            level2 = []
            for ref in level1:
                sub_refs = self.get_referrals_by_level(ref['referred_id'], 1)
                # Додаємо як рефералів 2го рівня основного користувача
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

    # === Helper Methods ===

    def test_connection(self) -> bool:
        """Тестувати з'єднання"""
        try:
            # Спробуємо отримати один запис
            self.table('users').select('id').limit(1).execute()
            return True
        except:
            return False


# Створюємо глобальний екземпляр
supabase = SupabaseClient()