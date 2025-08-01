# backend/orders/services.py
"""
TeleBoost Order Services
Бізнес-логіка для роботи з замовленнями
"""
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from backend.orders.models import Order
from backend.services.models import Service
from backend.auth.models import User
from backend.api.nakrutochka_api import nakrutochka
from backend.supabase_client import supabase
from backend.utils.constants import OrderStatus, SERVICE_TYPE, TRANSACTION_TYPE
from backend.services.validators import validate_service_order

logger = logging.getLogger(__name__)

# Мапінг статусів Nakrutochka на внутрішні
NAKRUTOCHKA_STATUS_MAP = {
    'Pending': OrderStatus.PENDING,
    'In progress': OrderStatus.IN_PROGRESS,
    'Processing': OrderStatus.PROCESSING,
    'Completed': OrderStatus.COMPLETED,
    'Partial': OrderStatus.PARTIAL,
    'Canceled': OrderStatus.CANCELLED,
    'Cancelled': OrderStatus.CANCELLED,  # Різні варіанти написання
    'Failed': OrderStatus.FAILED,
    # Додаткові статуси, які може повертати Nakrutochka
    'Refunded': OrderStatus.CANCELLED,
    'Error': OrderStatus.FAILED,
    'Canceled by user': OrderStatus.CANCELLED,
}


class OrderService:
    """Сервіс для управління замовленнями"""

    @staticmethod
    def create_order(user: User, service_id: int, link: str,
                     quantity: int = None, **params) -> Tuple[bool, Optional[Order], Optional[str]]:
        """
        Створити нове замовлення

        Args:
            user: Користувач
            service_id: ID сервісу
            link: Посилання
            quantity: Кількість
            **params: Додаткові параметри

        Returns:
            (success, order, error_message)
        """
        try:
            # Валідація замовлення
            is_valid, error = validate_service_order(service_id, {
                'link': link,
                'quantity': quantity,
                **params
            })

            if not is_valid:
                return False, None, error

            # Отримуємо сервіс
            service = Service.get_by_id(service_id)
            if not service:
                return False, None, "Сервіс не знайдено"

            # Розрахунок кількості для різних типів
            if service.type == SERVICE_TYPE.CUSTOM_COMMENTS:
                if 'comments' in params:
                    comments_list = params['comments'].strip().split('\n')
                    quantity = len([c for c in comments_list if c.strip()])

            # Перевірка кількості
            is_valid, error = service.validate_quantity(quantity)
            if not is_valid:
                return False, None, error

            # Розрахунок ціни
            price = service.calculate_price(quantity)

            # Перевірка балансу
            if user.balance < price:
                return False, None, f"Недостатньо коштів. Потрібно: ${price:.2f}, доступно: ${user.balance:.2f}"

            # Створюємо замовлення в БД
            order = Order.create(
                user_id=user.id,
                service_id=service_id,
                link=link,
                quantity=quantity,
                **params
            )

            if not order:
                return False, None, "Помилка створення замовлення"

            # Відправляємо на Nakrutochka
            success, error = OrderProcessor.send_to_nakrutochka(order, service)

            if not success:
                # Скасовуємо замовлення
                order.cancel()
                return False, None, f"Помилка API: {error}"

            # Списуємо кошти з балансу
            balance_updated = supabase.client.rpc('decrement_balance', {
                'user_id': user.id,
                'amount': price
            }).execute()

            if balance_updated.data is not True:
                # Щось пішло не так, скасовуємо
                order.cancel()
                OrderProcessor.cancel_in_nakrutochka(order)
                return False, None, "Помилка списання коштів"

            # Створюємо транзакцію
            transaction_data = {
                'user_id': user.id,
                'type': TRANSACTION_TYPE.ORDER,
                'amount': -price,  # Від'ємна сума для списання
                'balance_before': user.balance,
                'balance_after': user.balance - price,
                'description': f'Замовлення #{order.id[:8]}',
                'metadata': {
                    'order_id': order.id,
                    'service_name': service.name,
                    'quantity': quantity
                }
            }
            supabase.create_transaction(transaction_data)

            # Оновлюємо баланс користувача локально
            user.balance -= price

            logger.info(f"Order {order.id} created successfully for user {user.telegram_id}")

            return True, order, None

        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return False, None, "Внутрішня помилка сервера"

    @staticmethod
    def get_order_details(order_id: str, user_id: str) -> Optional[Order]:
        """Отримати деталі замовлення"""
        order = Order.get_by_id(order_id)

        if not order:
            return None

        # Перевіряємо що замовлення належить користувачу
        if order.user_id != user_id:
            logger.warning(f"User {user_id} tried to access order {order_id}")
            return None

        return order

    @staticmethod
    def update_order_status(order: Order) -> bool:
        """Оновити статус замовлення з Nakrutochka"""
        try:
            if not order.external_id:
                return False

            # Отримуємо статус з API
            result = nakrutochka.get_order_status(order.external_id)

            if not result.get('success'):
                logger.error(
                    f"Failed to get status for order {order.id}: "
                    f"{result.get('error', 'Unknown error')}"
                )
                return False

            # Мапінг статусу з Nakrutochka
            external_status = result.get('status', 'Processing')
            new_status = NAKRUTOCHKA_STATUS_MAP.get(
                external_status,
                OrderStatus.PROCESSING  # Дефолтний статус
            )

            # Логування невідомих статусів
            if external_status not in NAKRUTOCHKA_STATUS_MAP:
                logger.warning(
                    f"Unknown Nakrutochka status '{external_status}' for order {order.id}, "
                    f"using default status '{new_status}'"
                )

            # Отримуємо додаткові дані
            start_count = result.get('start_count', 0)
            remains = result.get('remains', 0)

            # Валідація даних
            try:
                start_count = int(start_count)
                remains = int(remains)
            except (ValueError, TypeError):
                logger.error(f"Invalid numeric data from Nakrutochka for order {order.id}")
                start_count = 0
                remains = 0

            # Оновлюємо в БД
            return order.update_status(
                new_status=new_status,
                external_status=external_status,
                start_count=start_count,
                remains=remains
            )

        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return False

    @staticmethod
    def cancel_order(order: Order, user: User) -> Tuple[bool, Optional[str]]:
        """
        Скасувати замовлення

        Returns:
            (success, error_message)
        """
        try:
            # Перевіряємо чи можна скасувати
            if order.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
                return False, "Замовлення не можна скасувати"

            # Скасовуємо в Nakrutochka якщо є external_id
            if order.external_id:
                result = nakrutochka.cancel_orders([order.external_id])
                if not result.get('success'):
                    return False, "Не вдалося скасувати замовлення"

            # Скасовуємо в БД
            if not order.cancel():
                return False, "Помилка скасування"

            # Повертаємо кошти
            refund_amount = order.charge
            if refund_amount > 0:
                # Повертаємо на баланс
                balance_updated = supabase.client.rpc('increment_balance', {
                    'user_id': user.id,
                    'amount': refund_amount
                }).execute()

                if balance_updated.data is True:
                    # Створюємо транзакцію повернення
                    transaction_data = {
                        'user_id': user.id,
                        'type': TRANSACTION_TYPE.REFUND,
                        'amount': refund_amount,
                        'balance_before': user.balance,
                        'balance_after': user.balance + refund_amount,
                        'description': f'Повернення за замовлення #{order.id[:8]}',
                        'metadata': {
                            'order_id': order.id,
                            'refund_reason': 'order_cancelled'
                        }
                    }
                    supabase.create_transaction(transaction_data)

            return True, None

        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False, "Помилка скасування"

    @staticmethod
    def request_refill(order: Order) -> Tuple[bool, Optional[str]]:
        """Запросити поповнення для замовлення"""
        try:
            if order.status != OrderStatus.COMPLETED:
                return False, "Поповнення доступне тільки для завершених замовлень"

            if not order.external_id:
                return False, "Немає зовнішнього ID замовлення"

            # Запит на поповнення
            result = nakrutochka.refill_order(order.external_id)

            if result.get('success'):
                # Зберігаємо ID поповнення
                order.metadata = order.metadata or {}
                order.metadata['refill_id'] = result.get('refill_id')
                order.metadata['refill_requested_at'] = datetime.utcnow().isoformat()

                # Оновлюємо в БД
                supabase.table('orders').update({
                    'metadata': order.metadata,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', order.id).execute()

                return True, None
            else:
                return False, result.get('error', 'Помилка запиту поповнення')

        except Exception as e:
            logger.error(f"Error requesting refill: {e}")
            return False, "Помилка запиту поповнення"


class OrderProcessor:
    """Обробник замовлень через API"""

    @staticmethod
    def send_to_nakrutochka(order: Order, service: Service) -> Tuple[bool, Optional[str]]:
        """
        Відправити замовлення на Nakrutochka

        Returns:
            (success, error_message)
        """
        try:
            # Підготовка параметрів відповідно до типу сервісу
            api_params = {
                'service': service.id,  # Nakrutochka service ID
                'link': order.link,
            }

            # Додаємо параметри в залежності від типу
            if service.type == SERVICE_TYPE.DEFAULT:
                api_params['quantity'] = order.quantity

            elif service.type == SERVICE_TYPE.DRIP_FEED:
                api_params['quantity'] = order.quantity
                api_params['runs'] = order.metadata.get('parameters', {}).get('runs', 1)
                api_params['interval'] = order.metadata.get('parameters', {}).get('interval', 60)

            elif service.type == SERVICE_TYPE.CUSTOM_COMMENTS:
                api_params['comments'] = order.comments

            elif service.type == SERVICE_TYPE.POLL:
                api_params['quantity'] = order.quantity
                api_params['answer_number'] = order.metadata.get('parameters', {}).get('answer_number', '1')

            elif service.type == SERVICE_TYPE.SUBSCRIPTION:
                params = order.metadata.get('parameters', {})
                api_params['username'] = params.get('username')
                api_params['min'] = params.get('min', 100)
                api_params['max'] = params.get('max', 200)
                api_params['posts'] = params.get('posts', 0)
                api_params['delay'] = params.get('delay', 0)
                api_params['expiry'] = params.get('expiry')

            # Відправляємо запит
            result = nakrutochka.create_order(**api_params)

            if result.get('success'):
                # Зберігаємо external ID
                external_id = str(result.get('order_id'))
                order.set_external_id(external_id)

                # Оновлюємо статус
                order.update_status(OrderStatus.PROCESSING)

                logger.info(f"Order {order.id} sent to Nakrutochka with ID {external_id}")
                return True, None
            else:
                # Детальна обробка помилок
                error = result.get('error', 'Unknown API error')
                error_code = result.get('code', 'UNKNOWN')

                # Мапінг помилок Nakrutochka на зрозумілі повідомлення
                error_messages = {
                    'NOT_ENOUGH_BALANCE': 'Недостатньо коштів на балансі Nakrutochka',
                    'INVALID_LINK': 'Некоректне посилання для даного сервісу',
                    'SERVICE_NOT_FOUND': 'Сервіс не знайдено в Nakrutochka',
                    'QUANTITY_BELOW_MIN': f'Кількість менше мінімальної ({service.min})',
                    'QUANTITY_ABOVE_MAX': f'Кількість більше максимальної ({service.max})',
                    'INVALID_PARAMETERS': 'Некоректні параметри замовлення',
                    'SERVICE_UNAVAILABLE': 'Сервіс тимчасово недоступний',
                    'RATE_LIMIT': 'Перевищено ліміт запитів до API',
                    'INVALID_API_KEY': 'Помилка авторизації API',
                    'MAINTENANCE': 'API на технічному обслуговуванні',
                }

                user_friendly_error = error_messages.get(error_code, error)

                logger.error(
                    f"Failed to send order to Nakrutochka: {error} (code: {error_code})"
                )

                return False, user_friendly_error

        except requests.exceptions.Timeout:
            logger.error(f"Timeout sending order {order.id} to Nakrutochka")
            return False, "Час очікування вичерпано. Спробуйте ще раз"
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error sending order {order.id} to Nakrutochka")
            return False, "Помилка з'єднання з сервісом. Спробуйте пізніше"
        except Exception as e:
            logger.error(f"Error sending order to Nakrutochka: {e}")
            return False, "Внутрішня помилка. Зверніться до підтримки"

    @staticmethod
    def cancel_in_nakrutochka(order: Order) -> bool:
        """Скасувати замовлення в Nakrutochka"""
        try:
            if not order.external_id:
                return True  # Немає що скасовувати

            result = nakrutochka.cancel_orders([order.external_id])
            return result.get('success', False)

        except Exception as e:
            logger.error(f"Error cancelling order in Nakrutochka: {e}")
            return False

    @staticmethod
    def sync_multiple_orders(order_ids: List[str]) -> Dict[str, bool]:
        """
        Синхронізувати статуси кількох замовлень

        Returns:
            Dict з результатами {order_id: success}
        """
        results = {}

        try:
            # Отримуємо замовлення з external_id
            orders = []
            external_ids = []

            for order_id in order_ids:
                order = Order.get_by_id(order_id)
                if order and order.external_id:
                    orders.append(order)
                    external_ids.append(order.external_id)
                else:
                    results[order_id] = False

            if not external_ids:
                return results

            # Отримуємо статуси з API
            api_result = nakrutochka.get_multiple_order_status(external_ids)

            if not api_result.get('success'):
                logger.error(
                    f"Failed to get multiple order statuses: "
                    f"{api_result.get('error', 'Unknown error')}"
                )
                for order in orders:
                    results[order.id] = False
                return results

            # Оновлюємо кожне замовлення
            statuses = api_result.get('orders', {})

            for order in orders:
                if order.external_id in statuses:
                    status_data = statuses[order.external_id]

                    # Використання мапінгу статусів
                    external_status = status_data.get('status', 'Processing')
                    mapped_status = NAKRUTOCHKA_STATUS_MAP.get(
                        external_status,
                        order.status  # Залишаємо поточний статус якщо невідомий
                    )

                    # Валідація числових даних
                    try:
                        start_count = int(status_data.get('start_count', 0))
                        remains = int(status_data.get('remains', 0))
                    except (ValueError, TypeError):
                        start_count = 0
                        remains = 0

                    success = order.update_status(
                        new_status=mapped_status,
                        external_status=external_status,
                        start_count=start_count,
                        remains=remains
                    )

                    results[order.id] = success
                else:
                    results[order.id] = False

            return results

        except Exception as e:
            logger.error(f"Error syncing multiple orders: {e}")
            # Помічаємо всі як failed
            for order_id in order_ids:
                if order_id not in results:
                    results[order_id] = False
            return results


class OrderCalculator:
    """Калькулятор для замовлень"""

    @staticmethod
    def calculate_price(service_id: int, quantity: int = None, **params) -> Optional[Dict[str, Any]]:
        """
        Розрахувати вартість замовлення

        Returns:
            {
                'price': float,
                'currency': str,
                'quantity': int,
                'rate': float,
                'service_name': str
            }
        """
        try:
            service = Service.get_by_id(service_id)
            if not service:
                return None

            # Визначаємо кількість для різних типів
            if service.type == SERVICE_TYPE.CUSTOM_COMMENTS:
                if 'comments' in params:
                    comments_list = params['comments'].strip().split('\n')
                    quantity = len([c for c in comments_list if c.strip()])

            if not quantity:
                quantity = service.min

            # Перевіряємо ліміти
            is_valid, error = service.validate_quantity(quantity)
            if not is_valid:
                return None

            # Розраховуємо ціну
            price = service.calculate_price(quantity)

            return {
                'price': price,
                'currency': 'USD',
                'quantity': quantity,
                'rate': service.rate,
                'service_name': service.name,
                'min': service.min,
                'max': service.max
            }

        except Exception as e:
            logger.error(f"Error calculating price: {e}")
            return None

    @staticmethod
    def calculate_drip_feed_total(base_price: float, runs: int) -> float:
        """Розрахувати загальну вартість для drip-feed"""
        return base_price * runs

    @staticmethod
    def estimate_completion_time(service: Service, quantity: int) -> Optional[str]:
        """Оцінити час виконання замовлення"""
        # Це приблизна оцінка, можна налаштувати
        estimates = {
            'instagram': {
                'followers': '24-48 годин',
                'likes': '1-6 годин',
                'views': '1-3 години',
                'comments': '6-24 години'
            },
            'telegram': {
                'members': '12-24 години',
                'views': '1-3 години',
                'reactions': '1-6 годин'
            },
            'youtube': {
                'views': '24-72 години',
                'likes': '12-24 години',
                'subscribers': '24-48 годин'
            }
        }

        # Тут можна додати більш складну логіку
        category = service.category.key
        if category in estimates:
            # Простий приклад - можна покращити
            for keyword, time in estimates[category].items():
                if keyword in service.name.lower():
                    return time

        return "24-72 години"