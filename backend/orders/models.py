# backend/orders/models.py
"""
TeleBoost Order Models
Моделі для системи замовлень
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from backend.supabase_client import supabase
from backend.services.models import Service
from backend.utils.constants import OrderStatus, SERVICE_TYPE
from backend.utils.redis_client import redis_client
from backend.utils.formatters import format_order_id

logger = logging.getLogger(__name__)


class Order:
    """Модель замовлення"""

    def __init__(self, data: Dict[str, Any]):
        """Ініціалізація з даних БД"""
        self.id = data.get('id')  # UUID
        self.user_id = data.get('user_id')

        # Service info
        self.service_id = data.get('service_id')
        self.service_name = data.get('metadata', {}).get('service_name', '')
        self.service_type = data.get('metadata', {}).get('service_type', SERVICE_TYPE.DEFAULT)

        # Order details
        self.link = data.get('link', '')
        self.quantity = int(data.get('quantity', 0))
        self.comments = data.get('comments')

        # External order
        self.external_id = data.get('nakrutochka_order_id')

        # Status
        self.status = data.get('status', OrderStatus.PENDING)

        # Progress
        self.start_count = int(data.get('start_count', 0))
        self.remains = int(data.get('remains', 0))
        self.completed = self.quantity - self.remains if self.quantity else 0

        # Financial
        self.charge = float(data.get('charge', 0))
        self.currency = 'USD'

        # Timestamps
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')

        # Metadata
        self.metadata = data.get('metadata', {})

    @classmethod
    def create(cls, user_id: str, service_id: int, link: str,
               quantity: int = None, **params) -> Optional['Order']:
        """
        Створити нове замовлення

        Args:
            user_id: ID користувача
            service_id: ID сервісу
            link: Посилання
            quantity: Кількість
            **params: Додаткові параметри

        Returns:
            Order instance або None
        """
        try:
            # Отримуємо сервіс
            service = Service.get_by_id(service_id)
            if not service:
                logger.error(f"Service {service_id} not found")
                return None

            if not service.is_active:
                logger.error(f"Service {service_id} is not active")
                return None

            # Підготовка параметрів
            parameters = {
                'service_type': service.type,
                'dripfeed': params.get('dripfeed', False),
                'runs': params.get('runs'),
                'interval': params.get('interval'),
                'comments': params.get('comments'),
                'answer_number': params.get('answer_number'),
                'username': params.get('username'),
                'min': params.get('min'),
                'max': params.get('max'),
                'posts': params.get('posts'),
                'delay': params.get('delay'),
            }

            # Розрахунок кількості для різних типів
            if service.type == SERVICE_TYPE.CUSTOM_COMMENTS:
                # Для custom comments quantity = кількість коментарів
                if 'comments' in params:
                    comments_list = params['comments'].strip().split('\n')
                    quantity = len([c for c in comments_list if c.strip()])

            # Розрахунок ціни
            price = service.calculate_price(quantity or 1)

            # Створення замовлення в БД
            order_data = {
                'user_id': user_id,
                'service_id': service_id,
                'link': link,
                'quantity': quantity,
                'comments': params.get('comments'),
                'charge': price,
                'status': OrderStatus.PENDING,
                'metadata': {
                    'service_name': service.name,
                    'service_type': service.type,
                    'parameters': parameters,
                }
            }

            result = supabase.table('orders').insert(order_data).execute()

            if not result.data:
                logger.error("Failed to create order in database")
                return None

            order = cls(result.data[0])

            # Кешуємо замовлення
            cache_key = f"order:{order.id}"
            redis_client.set(cache_key, order.to_dict(), ttl=300)  # 5 хвилин

            logger.info(f"Created order {order.id} for user {user_id}")
            return order

        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    @classmethod
    def get_by_id(cls, order_id: str, use_cache: bool = True) -> Optional['Order']:
        """Отримати замовлення за ID"""
        try:
            # Спробуємо з кешу
            if use_cache:
                cache_key = f"order:{order_id}"
                cached = redis_client.get(cache_key, data_type='json')

                if cached:
                    return cls(cached)

            # З БД
            result = supabase.table('orders').select('*').eq('id', order_id).single().execute()

            if result.data:
                order = cls(result.data)

                # Кешуємо
                if use_cache:
                    redis_client.set(f"order:{order_id}", result.data, ttl=300)

                return order

            return None

        except Exception as e:
            logger.error(f"Error getting order {order_id}: {e}")
            return None

    @classmethod
    def get_by_external_id(cls, nakrutochka_order_id: str) -> Optional['Order']:
        """Отримати замовлення за Nakrutochka ID"""
        try:
            result = supabase.table('orders') \
                .select('*') \
                .eq('nakrutochka_order_id', nakrutochka_order_id) \
                .single() \
                .execute()

            if result.data:
                return cls(result.data)
            return None

        except Exception as e:
            logger.error(f"Error getting order by external ID {nakrutochka_order_id}: {e}")
            return None

    @classmethod
    def get_user_orders(cls, user_id: str, status: Optional[str] = None,
                        limit: int = 50, offset: int = 0) -> List['Order']:
        """Отримати замовлення користувача"""
        try:
            query = supabase.table('orders').select('*').eq('user_id', user_id)

            if status:
                query = query.eq('status', status)

            result = query.order('created_at', desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()

            if result.data:
                return [cls(data) for data in result.data]

            return []

        except Exception as e:
            logger.error(f"Error getting user orders: {e}")
            return []

    def update_status(self, new_status: str, external_status: Optional[str] = None,
                      start_count: Optional[int] = None, remains: Optional[int] = None) -> bool:
        """Оновити статус замовлення"""
        try:
            # Валідація нового статусу
            if new_status not in OrderStatus.all():
                logger.error(f"Invalid status '{new_status}' for order {self.id}")
                return False

            # Перевірка дозволених переходів статусів
            from backend.orders.validators import validate_order_status_transition
            if not validate_order_status_transition(self.status, new_status):
                logger.warning(
                    f"Invalid status transition from '{self.status}' to '{new_status}' "
                    f"for order {self.id}"
                )
                return False

            update_data = {
                'status': new_status,
                'updated_at': datetime.utcnow().isoformat()
            }

            if external_status:
                self.metadata = self.metadata or {}
                self.metadata['external_status'] = external_status
                update_data['metadata'] = self.metadata

            if start_count is not None:
                update_data['start_count'] = start_count

            if remains is not None:
                update_data['remains'] = remains

            # Якщо замовлення завершено
            if new_status == OrderStatus.COMPLETED:
                self.metadata = self.metadata or {}
                self.metadata['completed_at'] = datetime.utcnow().isoformat()
                update_data['metadata'] = self.metadata

            result = supabase.table('orders') \
                .update(update_data) \
                .eq('id', self.id) \
                .execute()

            if result.data:
                # Оновлюємо локальні дані
                self.status = new_status
                if start_count is not None:
                    self.start_count = start_count
                if remains is not None:
                    self.remains = remains
                    self.completed = self.quantity - remains if self.quantity else 0

                # Інвалідуємо кеш
                redis_client.delete(f"order:{self.id}")

                logger.info(f"Order {self.id} status updated from '{self.status}' to '{new_status}'")
                return True

            return False

        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return False

    def set_external_id(self, nakrutochka_order_id: str) -> bool:
        """Встановити зовнішній ID замовлення"""
        try:
            result = supabase.table('orders') \
                .update({
                'nakrutochka_order_id': nakrutochka_order_id,
                'updated_at': datetime.utcnow().isoformat()
            }) \
                .eq('id', self.id) \
                .execute()

            if result.data:
                self.external_id = nakrutochka_order_id
                redis_client.delete(f"order:{self.id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error setting external ID: {e}")
            return False

    def cancel(self) -> bool:
        """Скасувати замовлення"""
        if self.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
            logger.warning(f"Cannot cancel order {self.id} with status {self.status}")
            return False

        return self.update_status(OrderStatus.CANCELLED)

    def get_progress_percentage(self) -> float:
        """Отримати прогрес виконання у відсотках"""
        if not self.quantity or self.quantity == 0:
            return 0.0

        completed = self.quantity - self.remains
        return round((completed / self.quantity) * 100, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Конвертувати в словник"""
        return {
            'id': self.id,
            'order_number': format_order_id(self.id[:8]) if self.id else None,
            'user_id': self.user_id,
            'service_id': self.service_id,
            'service_name': self.service_name,
            'service_type': self.service_type,
            'link': self.link,
            'quantity': self.quantity,
            'external_id': self.external_id,
            'status': self.status,
            'start_count': self.start_count,
            'remains': self.remains,
            'completed': self.completed,
            'progress': self.get_progress_percentage(),
            'charge': self.charge,
            'currency': self.currency,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'metadata': self.metadata,
        }

    def to_public_dict(self) -> Dict[str, Any]:
        """Публічний словник (без чутливих даних)"""
        from backend.utils.formatters import format_price, format_datetime

        return {
            'id': self.id,
            'order_number': format_order_id(self.id[:8]) if self.id else None,
            'service_name': self.service_name,
            'link': self.link,
            'quantity': self.quantity,
            'status': self.status,
            'progress': self.get_progress_percentage(),
            'price': format_price(self.charge, self.currency),
            'created_at': format_datetime(self.created_at) if self.created_at else None,
        }