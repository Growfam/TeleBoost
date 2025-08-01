# backend/orders/tasks.py
"""
TeleBoost Order Tasks
Фонові задачі для обробки замовлень
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from backend.orders.models import Order
from backend.orders.services import OrderService, OrderProcessor, NAKRUTOCHKA_STATUS_MAP
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
        total_errors = 0

        for i in range(0, len(orders), batch_size):
            batch = orders[i:i + batch_size]
            order_ids = [o['id'] for o in batch if o.get('nakrutochka_order_id')]

            if order_ids:
                results = OrderProcessor.sync_multiple_orders(order_ids)
                successful = sum(1 for success in results.values() if success)
                errors = len(order_ids) - successful
                total_synced += successful
                total_errors += errors

                logger.info(
                    f"Synced batch {i // batch_size + 1}: "
                    f"{successful}/{len(order_ids)} orders"
                )

                if errors > 0:
                    logger.warning(f"Failed to sync {errors} orders in batch")

        logger.info(
            f"Active orders sync completed. "
            f"Total synced: {total_synced}, Errors: {total_errors}"
        )

        # Зберігаємо час останньої синхронізації
        redis_client.set('orders:last_sync', datetime.utcnow().isoformat(), ttl=3600)

        # Зберігаємо статистику синхронізації
        redis_client.hset('orders:sync_stats', 'last_run', datetime.utcnow().isoformat())
        redis_client.hset('orders:sync_stats', 'total_synced', total_synced)
        redis_client.hset('orders:sync_stats', 'total_errors', total_errors)

    except Exception as e:
        logger.error(f"Error syncing active orders: {e}")
        # Зберігаємо помилку в Redis для моніторингу
        redis_client.hset('orders:sync_stats', 'last_error', str(e))
        redis_client.hset('orders:sync_stats', 'last_error_time', datetime.utcnow().isoformat())


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
            stuck_count = 0
            failed_count = 0

            for order_data in result.data:
                order = Order(order_data)

                # Якщо є external_id - пробуємо оновити статус
                if order.external_id:
                    success = OrderService.update_order_status(order)
                    if not success:
                        # Якщо не вдалося - позначаємо як failed
                        order.update_status(OrderStatus.FAILED)
                        failed_count += 1
                        logger.error(f"Failed to update stuck order {order.id}")
                else:
                    # Немає external_id після 30 хв - щось пішло не так
                    order.update_status(OrderStatus.FAILED)
                    failed_count += 1

                    # Повертаємо кошти користувачу
                    _refund_failed_order(order)
                    logger.warning(f"Refunded stuck order {order.id} without external ID")

                stuck_count += 1

            logger.info(
                f"Stuck orders check completed. "
                f"Processed: {stuck_count}, Failed: {failed_count}"
            )
        else:
            logger.info("No stuck orders found")

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
        updated_users = 0
        for user_id, stats in user_stats.items():
            try:
                # Використовуємо RPC функцію для атомарного оновлення
                result = supabase.client.rpc('increment_value', {
                    'table_name': 'users',
                    'column_name': 'total_spent',
                    'row_id': user_id,
                    'increment_by': stats['total_spent']
                }).execute()

                if result.data is True:
                    updated_users += 1
                    logger.info(
                        f"Updated stats for user {user_id}: "
                        f"+${stats['total_spent']:.2f} from {stats['order_count']} orders"
                    )
                else:
                    logger.error(f"Failed to update stats for user {user_id}")

            except Exception as e:
                logger.error(f"Error updating stats for user {user_id}: {e}")

        logger.info(
            f"Completed orders statistics update finished. "
            f"Updated {updated_users}/{len(user_stats)} users"
        )

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
            cleaned_count = len(result.data)
            logger.info(f"Cleaned up metadata for {cleaned_count} old cancelled orders")

            # Зберігаємо статистику очищення
            redis_client.hset('orders:cleanup_stats', 'last_run', datetime.utcnow().isoformat())
            redis_client.hset('orders:cleanup_stats', 'cleaned_count', cleaned_count)
        else:
            logger.info("No old cancelled orders to clean up")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        redis_client.hset('orders:cleanup_stats', 'last_error', str(e))


def send_order_notifications():
    """
    Відправити сповіщення про зміни статусів замовлень

    Запускати кожні 10 хвилин
    """
    try:
        logger.info("Checking for order notifications...")

        # Отримуємо замовлення зі зміненими статусами
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)

        result = supabase.table('orders') \
            .select('id, user_id, status, service_id, metadata') \
            .gt('updated_at', ten_minutes_ago.isoformat()) \
            .in_('status', [OrderStatus.COMPLETED, OrderStatus.FAILED, OrderStatus.CANCELLED]) \
            .execute()

        if not result.data:
            logger.info("No orders requiring notifications")
            return

        notifications_sent = 0
        for order_data in result.data:
            # Перевіряємо чи вже відправляли сповіщення
            notification_key = f"order_notification:{order_data['id']}:{order_data['status']}"

            if not redis_client.exists(notification_key):
                # Тут можна інтегрувати з системою сповіщень
                # Наприклад, відправка через Telegram Bot API

                # Помічаємо як відправлене
                redis_client.set(notification_key, "sent", ttl=86400)  # 24 години
                notifications_sent += 1

                logger.info(
                    f"Notification queued for order {order_data['id']} "
                    f"with status {order_data['status']}"
                )

        logger.info(f"Order notifications check completed. Sent: {notifications_sent}")

    except Exception as e:
        logger.error(f"Error sending notifications: {e}")


def check_orders_integrity():
    """
    Перевірити цілісність даних замовлень

    Запускати раз на добу
    """
    try:
        logger.info("Starting orders integrity check...")

        issues_found = 0

        # 1. Перевірка замовлень без external_id в статусі processing
        result = supabase.table('orders') \
            .select('id, created_at') \
            .eq('status', OrderStatus.PROCESSING) \
            .is_('nakrutochka_order_id', 'null') \
            .execute()

        if result.data:
            issues_found += len(result.data)
            logger.warning(
                f"Found {len(result.data)} orders in PROCESSING status without external ID"
            )

            for order in result.data:
                # Якщо замовлення старше 1 години - позначаємо як failed
                created_at = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00'))
                if datetime.utcnow().replace(tzinfo=created_at.tzinfo) - created_at > timedelta(hours=1):
                    logger.error(f"Marking orphaned order {order['id']} as failed")
                    # Тут можна додати оновлення статусу

        # 2. Перевірка невідповідності статусів
        # Наприклад, completed з remains > 0
        result = supabase.table('orders') \
            .select('id, quantity, remains') \
            .eq('status', OrderStatus.COMPLETED) \
            .gt('remains', 0) \
            .execute()

        if result.data:
            issues_found += len(result.data)
            logger.warning(
                f"Found {len(result.data)} completed orders with remaining quantity"
            )

        # Зберігаємо результати перевірки
        redis_client.hset('orders:integrity_check', 'last_run', datetime.utcnow().isoformat())
        redis_client.hset('orders:integrity_check', 'issues_found', issues_found)

        logger.info(f"Orders integrity check completed. Issues found: {issues_found}")

    except Exception as e:
        logger.error(f"Error during integrity check: {e}")


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
                # Отримуємо поточний баланс користувача для транзакції
                user_result = supabase.table('users') \
                    .select('balance') \
                    .eq('id', order.user_id) \
                    .single() \
                    .execute()

                current_balance = float(user_result.data['balance']) if user_result.data else refund_amount

                # Створюємо транзакцію
                transaction_data = {
                    'user_id': order.user_id,
                    'type': TRANSACTION_TYPE.REFUND,
                    'amount': refund_amount,
                    'balance_before': current_balance - refund_amount,
                    'balance_after': current_balance,
                    'description': f'Automatic refund for failed order #{order.id[:8]}',
                    'metadata': {
                        'order_id': order.id,
                        'reason': 'order_failed'
                    }
                }

                supabase.create_transaction(transaction_data)

                logger.info(f"Refunded ${refund_amount:.2f} for failed order {order.id}")
            else:
                logger.error(f"Failed to refund order {order.id}")

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
        replace_existing=True,
        max_instances=1  # Тільки один екземпляр одночасно
    )

    # Перевірка застряглих замовлень кожні 30 хвилин
    scheduler.add_job(
        check_stuck_orders,
        'interval',
        minutes=30,
        id='check_stuck_orders',
        replace_existing=True,
        max_instances=1
    )

    # Оновлення статистики щогодини
    scheduler.add_job(
        update_completed_orders_stats,
        'interval',
        hours=1,
        id='update_completed_orders_stats',
        replace_existing=True,
        max_instances=1
    )

    # Очищення старих даних щотижня
    scheduler.add_job(
        cleanup_old_cancelled_orders,
        'cron',
        day_of_week='sun',
        hour=3,
        minute=0,
        id='cleanup_old_cancelled_orders',
        replace_existing=True,
        max_instances=1
    )

    # Сповіщення кожні 10 хвилин
    scheduler.add_job(
        send_order_notifications,
        'interval',
        minutes=10,
        id='send_order_notifications',
        replace_existing=True,
        max_instances=1
    )

    # Перевірка цілісності щоночі
    scheduler.add_job(
        check_orders_integrity,
        'cron',
        hour=2,
        minute=0,
        id='check_orders_integrity',
        replace_existing=True,
        max_instances=1
    )

    logger.info("Order tasks registered successfully")


def get_task_status() -> Dict[str, Any]:
    """Отримати статус виконання фонових задач"""
    try:
        stats = {
            'sync': redis_client.hgetall('orders:sync_stats', data_type='auto'),
            'cleanup': redis_client.hgetall('orders:cleanup_stats', data_type='auto'),
            'integrity': redis_client.hgetall('orders:integrity_check', data_type='auto'),
            'last_sync': redis_client.get('orders:last_sync'),
        }

        return stats
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return {}