# backend/orders/tasks.py
"""
TeleBoost Order Tasks
Фонові задачі для обробки замовлень
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from backend.orders.models import Order
from backend.orders.services import OrderService, OrderProcessor
from backend.supabase_client import supabase
from backend.utils.constants import OrderStatus, TRANSACTION_TYPE
from backend.utils.redis_client import redis_client

logger = logging.getLogger(__name__)


def sync_active_orders():
    """
    Синхронізувати всі активні замовлення з Nakrutochka API

    Запускати кожні 5 хвилин через cron або celery
    """
    try:
        logger.info("Starting active orders sync...")

        # Отримуємо всі активні замовлення
        active_statuses = [
            OrderStatus.PENDING,
            OrderStatus.PROCESSING,
            OrderStatus.IN_PROGRESS
        ]

        result = supabase.table('orders') \
            .select('id, nakrutochka_order_id') \
            .in_('status', active_statuses) \
            .execute()

        if not result.data:
            logger.info("No active orders to sync")
            return

        # Групуємо по 100 для batch запитів
        orders = result.data
        batch_size = 100
        total_synced = 0

        for i in range(0, len(orders), batch_size):
            batch = orders[i:i + batch_size]
            order_ids = [o['id'] for o in batch if o.get('nakrutochka_order_id')]

            if order_ids:
                results = OrderProcessor.sync_multiple_orders(order_ids)
                successful = sum(1 for success in results.values() if success)
                total_synced += successful

                logger.info(f"Synced batch {i // batch_size + 1}: {successful}/{len(order_ids)} orders")

        logger.info(f"Active orders sync completed. Total synced: {total_synced}")

        # Зберігаємо час останньої синхронізації
        redis_client.set('orders:last_sync', datetime.utcnow().isoformat(), ttl=3600)

    except Exception as e:
        logger.error(f"Error syncing active orders: {e}")


def check_stuck_orders():
    """
    Перевірити "застряглі" замовлення та оновити їх статус

    Запускати кожні 30 хвилин
    """
    try:
        logger.info("Checking for stuck orders...")

        # Замовлення в статусі pending більше 30 хвилин
        threshold_time = datetime.utcnow() - timedelta(minutes=30)

        result = supabase.table('orders') \
            .select('*') \
            .eq('status', OrderStatus.PENDING) \
            .lt('created_at', threshold_time.isoformat()) \
            .execute()

        if result.data:
            logger.warning(f"Found {len(result.data)} stuck orders")

            for order_data in result.data:
                order = Order(order_data)

                # Якщо є external_id - пробуємо оновити статус
                if order.external_id:
                    success = OrderService.update_order_status(order)
                    if not success:
                        # Якщо не вдалося - позначаємо як failed
                        order.update_status(
                            OrderStatus.FAILED
                        )
                else:
                    # Немає external_id після 30 хв - щось пішло не так
                    order.update_status(
                        OrderStatus.FAILED
                    )

                    # Повертаємо кошти користувачу
                    _refund_failed_order(order)

        logger.info("Stuck orders check completed")

    except Exception as e:
        logger.error(f"Error checking stuck orders: {e}")


def update_completed_orders_stats():
    """
    Оновити статистику для завершених замовлень

    Запускати раз на годину
    """
    try:
        logger.info("Updating completed orders statistics...")

        # Отримуємо замовлення завершені за останню годину
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        result = supabase.table('orders') \
            .select('user_id, charge, service_id') \
            .eq('status', OrderStatus.COMPLETED) \
            .gt('updated_at', one_hour_ago.isoformat()) \
            .execute()

        if not result.data:
            logger.info("No recently completed orders")
            return

        # Групуємо по користувачах
        user_stats = {}
        for order in result.data:
            user_id = order['user_id']
            charge = float(order['charge'])

            if user_id not in user_stats:
                user_stats[user_id] = {
                    'total_spent': 0,
                    'order_count': 0
                }

            user_stats[user_id]['total_spent'] += charge
            user_stats[user_id]['order_count'] += 1

        # Оновлюємо статистику користувачів
        for user_id, stats in user_stats.items():
            try:
                # Використовуємо RPC функцію для атомарного оновлення
                supabase.client.rpc('increment_value', {
                    'table_name': 'users',
                    'column_name': 'total_spent',
                    'row_id': user_id,
                    'increment_by': stats['total_spent']
                }).execute()

                logger.info(f"Updated stats for user {user_id}: +${stats['total_spent']:.2f}")

            except Exception as e:
                logger.error(f"Error updating stats for user {user_id}: {e}")

        logger.info("Completed orders statistics update finished")

    except Exception as e:
        logger.error(f"Error updating completed orders stats: {e}")


def cleanup_old_cancelled_orders():
    """
    Очистити старі скасовані замовлення

    Запускати раз на тиждень
    """
    try:
        logger.info("Starting cleanup of old cancelled orders...")

        # Видаляємо metadata для скасованих замовлень старше 30 днів
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        result = supabase.table('orders') \
            .update({'metadata': {}}) \
            .eq('status', OrderStatus.CANCELLED) \
            .lt('updated_at', thirty_days_ago.isoformat()) \
            .execute()

        if result.data:
            logger.info(f"Cleaned up metadata for {len(result.data)} old cancelled orders")

        logger.info("Cleanup completed")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


def send_order_notifications():
    """
    Відправити сповіщення про зміни статусів замовлень

    Запускати кожні 10 хвилин
    """
    try:
        # Отримуємо замовлення зі зміненими статусами
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)

        result = supabase.table('orders') \
            .select('id, user_id, status, service_id, metadata') \
            .gt('updated_at', ten_minutes_ago.isoformat()) \
            .in_('status', [OrderStatus.COMPLETED, OrderStatus.FAILED, OrderStatus.CANCELLED]) \
            .execute()

        if not result.data:
            return

        for order_data in result.data:
            # Перевіряємо чи вже відправляли сповіщення
            notification_key = f"order_notification:{order_data['id']}:{order_data['status']}"

            if not redis_client.exists(notification_key):
                # Тут можна інтегрувати з системою сповіщень
                # Наприклад, відправка через Telegram Bot API

                # Помічаємо як відправлене
                redis_client.set(notification_key, "sent", ttl=86400)  # 24 години

                logger.info(f"Notification queued for order {order_data['id']}")

    except Exception as e:
        logger.error(f"Error sending notifications: {e}")


def _refund_failed_order(order: Order):
    """Повернути кошти за невдале замовлення"""
    try:
        # Повертаємо повну суму
        refund_amount = order.charge

        if refund_amount > 0:
            # Оновлюємо баланс
            balance_updated = supabase.client.rpc('increment_balance', {
                'user_id': order.user_id,
                'amount': refund_amount
            }).execute()

            if balance_updated.data is True:
                # Створюємо транзакцію
                transaction_data = {
                    'user_id': order.user_id,
                    'type': TRANSACTION_TYPE.REFUND,
                    'amount': refund_amount,
                    'balance_before': 0,  # Потрібно отримати з БД
                    'balance_after': 0,  # Потрібно отримати з БД
                    'description': f'Automatic refund for failed order #{order.id[:8]}',
                    'metadata': {
                        'order_id': order.id,
                        'reason': 'order_failed'
                    }
                }

                supabase.create_transaction(transaction_data)

                logger.info(f"Refunded ${refund_amount:.2f} for failed order {order.id}")

    except Exception as e:
        logger.error(f"Error refunding failed order {order.id}: {e}")


# Функції для інтеграції з планувальником (Celery, APScheduler, etc)

def register_order_tasks(scheduler):
    """
    Реєстрація задач в планувальнику

    Приклад для APScheduler:
    ```python
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()
    register_order_tasks(scheduler)
    scheduler.start()
    ```
    """
    # Синхронізація активних замовлень кожні 5 хвилин
    scheduler.add_job(
        sync_active_orders,
        'interval',
        minutes=5,
        id='sync_active_orders',
        replace_existing=True
    )

    # Перевірка застряглих замовлень кожні 30 хвилин
    scheduler.add_job(
        check_stuck_orders,
        'interval',
        minutes=30,
        id='check_stuck_orders',
        replace_existing=True
    )

    # Оновлення статистики щогодини
    scheduler.add_job(
        update_completed_orders_stats,
        'interval',
        hours=1,
        id='update_completed_orders_stats',
        replace_existing=True
    )

    # Очищення старих даних щотижня
    scheduler.add_job(
        cleanup_old_cancelled_orders,
        'cron',
        day_of_week='sun',
        hour=3,
        minute=0,
        id='cleanup_old_cancelled_orders',
        replace_existing=True
    )

    # Сповіщення кожні 10 хвилин
    scheduler.add_job(
        send_order_notifications,
        'interval',
        minutes=10,
        id='send_order_notifications',
        replace_existing=True
    )

    logger.info("Order tasks registered successfully")