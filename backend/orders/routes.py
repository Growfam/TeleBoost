# backend/orders/routes.py
"""
TeleBoost Orders Routes
API endpoints для роботи з замовленнями
"""
import logging
from flask import Blueprint, request, jsonify, g

from backend.auth.decorators import jwt_required, rate_limit, validate_request
from backend.orders.services import OrderService, OrderCalculator
from backend.orders.models import Order
from backend.services.models import Service
from backend.utils.constants import OrderStatus, ERROR_MESSAGES
from backend.utils.formatters import format_datetime

logger = logging.getLogger(__name__)

# Створюємо Blueprint
orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')


@orders_bp.route('/', methods=['GET'])
@jwt_required
def get_orders():
    """
    Отримати список замовлень користувача

    Query params:
        - page: номер сторінки (default: 1)
        - limit: кількість на сторінці (default: 20, max: 100)
        - status: фільтр за статусом
    """
    try:
        user = g.current_user

        # Параметри пагінації
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = (page - 1) * limit

        # Фільтр за статусом
        status = request.args.get('status')
        if status and status not in OrderStatus.all():
            return jsonify({
                'success': False,
                'error': 'Invalid status filter',
                'code': 'INVALID_STATUS'
            }), 400

        # Отримуємо замовлення
        orders = Order.get_user_orders(
            user_id=user.id,
            status=status,
            limit=limit,
            offset=offset
        )

        # Рахуємо загальну кількість
        from backend.supabase_client import supabase
        query = supabase.table('orders').select('id', count='exact').eq('user_id', user.id)
        if status:
            query = query.eq('status', status)
        result = query.execute()
        total = result.count if hasattr(result, 'count') else 0

        # Формуємо відповідь
        orders_data = []
        for order in orders:
            # Отримуємо інформацію про сервіс
            service = Service.get_by_id(order.service_id)

            order_data = order.to_dict()
            order_data['service'] = {
                'name': service.name if service else order.service_name,
                'category': service.category.to_dict() if service else None
            }

            orders_data.append(order_data)

        return jsonify({
            'success': True,
            'data': {
                'orders': orders_data,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit if limit > 0 else 0
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'ORDERS_ERROR'
        }), 500


@orders_bp.route('/', methods=['POST'])
@jwt_required
@rate_limit(calls=30, period=3600)  # 30 замовлень на годину
@validate_request({
    'service_id': {'type': 'integer', 'required': True},
    'link': {'type': 'string', 'required': True, 'min_length': 5},
    'quantity': {'type': 'integer', 'required': False, 'min': 1}
})
def create_order():
    """
    Створити нове замовлення

    Request body:
    {
        "service_id": 4212,
        "link": "https://t.me/channel",
        "quantity": 1000,
        // Додаткові параметри в залежності від типу сервісу
    }
    """
    try:
        user = g.current_user
        data = request.get_json()

        # Створюємо замовлення
        success, order, error = OrderService.create_order(
            user=user,
            service_id=data['service_id'],
            link=data['link'],
            quantity=data.get('quantity'),
            **{k: v for k, v in data.items() if k not in ['service_id', 'link', 'quantity']}
        )

        if not success:
            return jsonify({
                'success': False,
                'error': error or 'Failed to create order',
                'code': 'ORDER_CREATION_FAILED'
            }), 400

        # Отримуємо сервіс для додаткової інформації
        service = Service.get_by_id(order.service_id)

        order_data = order.to_dict()
        order_data['service'] = {
            'name': service.name,
            'category': service.category.to_dict()
        } if service else None

        return jsonify({
            'success': True,
            'data': {
                'order': order_data,
                'message': 'Замовлення створено успішно'
            }
        }), 201

    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'ORDER_ERROR'
        }), 500


@orders_bp.route('/<order_id>', methods=['GET'])
@jwt_required
def get_order_details(order_id: str):
    """Отримати деталі замовлення"""
    try:
        user = g.current_user

        # Отримуємо замовлення
        order = OrderService.get_order_details(order_id, user.id)

        if not order:
            return jsonify({
                'success': False,
                'error': 'Order not found',
                'code': 'ORDER_NOT_FOUND'
            }), 404

        # Оновлюємо статус якщо потрібно
        if order.external_id and order.status not in [OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.FAILED]:
            OrderService.update_order_status(order)

        # Отримуємо сервіс
        service = Service.get_by_id(order.service_id)

        order_data = order.to_dict()
        order_data['service'] = {
            'name': service.name,
            'category': service.category.to_dict(),
            'type': service.type,
            'refill': service.refill,
            'cancel': service.cancel
        } if service else None

        return jsonify({
            'success': True,
            'data': {
                'order': order_data
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting order details: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'ORDER_DETAILS_ERROR'
        }), 500


@orders_bp.route('/<order_id>/status', methods=['GET'])
@jwt_required
def check_order_status(order_id: str):
    """Перевірити статус замовлення (з оновленням з API)"""
    try:
        user = g.current_user

        # Отримуємо замовлення
        order = OrderService.get_order_details(order_id, user.id)

        if not order:
            return jsonify({
                'success': False,
                'error': 'Order not found',
                'code': 'ORDER_NOT_FOUND'
            }), 404

        # Оновлюємо статус
        updated = False
        if order.external_id and order.status not in [OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.FAILED]:
            updated = OrderService.update_order_status(order)

        return jsonify({
            'success': True,
            'data': {
                'status': order.status,
                'progress': order.get_progress_percentage(),
                'remains': order.remains,
                'completed': order.completed,
                'updated': updated
            }
        }), 200

    except Exception as e:
        logger.error(f"Error checking order status: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'STATUS_CHECK_ERROR'
        }), 500


@orders_bp.route('/<order_id>/cancel', methods=['POST'])
@jwt_required
def cancel_order(order_id: str):
    """Скасувати замовлення"""
    try:
        user = g.current_user

        # Отримуємо замовлення
        order = OrderService.get_order_details(order_id, user.id)

        if not order:
            return jsonify({
                'success': False,
                'error': 'Order not found',
                'code': 'ORDER_NOT_FOUND'
            }), 404

        # Скасовуємо
        success, error = OrderService.cancel_order(order, user)

        if not success:
            return jsonify({
                'success': False,
                'error': error or 'Failed to cancel order',
                'code': 'CANCEL_FAILED'
            }), 400

        # Розраховуємо суму повернення
        refunded = order.charge

        return jsonify({
            'success': True,
            'data': {
                'message': 'Замовлення скасовано',
                'refunded': refunded if refunded > 0 else 0
            }
        }), 200

    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'CANCEL_ERROR'
        }), 500


@orders_bp.route('/<order_id>/refill', methods=['POST'])
@jwt_required
def request_refill(order_id: str):
    """Запросити поповнення для замовлення"""
    try:
        user = g.current_user

        # Отримуємо замовлення
        order = OrderService.get_order_details(order_id, user.id)

        if not order:
            return jsonify({
                'success': False,
                'error': 'Order not found',
                'code': 'ORDER_NOT_FOUND'
            }), 404

        # Запит на поповнення
        success, error = OrderService.request_refill(order)

        if not success:
            return jsonify({
                'success': False,
                'error': error or 'Failed to request refill',
                'code': 'REFILL_FAILED'
            }), 400

        return jsonify({
            'success': True,
            'data': {
                'message': 'Запит на поповнення надіслано'
            }
        }), 200

    except Exception as e:
        logger.error(f"Error requesting refill: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'REFILL_ERROR'
        }), 500


@orders_bp.route('/calculate-price', methods=['POST'])
@jwt_required
@validate_request({
    'service_id': {'type': 'integer', 'required': True},
    'quantity': {'type': 'integer', 'required': False, 'min': 1}
})
def calculate_price():
    """Розрахувати вартість замовлення"""
    try:
        data = request.get_json()

        # Розраховуємо ціну
        result = OrderCalculator.calculate_price(
            service_id=data['service_id'],
            quantity=data.get('quantity'),
            **{k: v for k, v in data.items() if k not in ['service_id', 'quantity']}
        )

        if not result:
            return jsonify({
                'success': False,
                'error': 'Invalid service or quantity',
                'code': 'CALCULATION_ERROR'
            }), 400

        return jsonify({
            'success': True,
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Error calculating price: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'PRICE_ERROR'
        }), 500


@orders_bp.route('/statistics', methods=['GET'])
@jwt_required
def get_order_statistics():
    """Отримати статистику замовлень користувача"""
    try:
        user = g.current_user

        from backend.supabase_client import supabase

        # Загальна статистика
        stats = {
            'total_orders': 0,
            'completed_orders': 0,
            'active_orders': 0,
            'failed_orders': 0,
            'total_spent': 0.0,
            'orders_by_status': {},
            'orders_by_category': {}
        }

        # Отримуємо всі замовлення користувача
        result = supabase.table('orders') \
            .select('status, charge, service_id') \
            .eq('user_id', user.id) \
            .execute()

        if result.data:
            stats['total_orders'] = len(result.data)

            # Підраховуємо статистику
            for order in result.data:
                status = order['status']
                charge = float(order['charge'])

                # За статусом
                if status not in stats['orders_by_status']:
                    stats['orders_by_status'][status] = 0
                stats['orders_by_status'][status] += 1

                # Загальні підрахунки
                if status == OrderStatus.COMPLETED:
                    stats['completed_orders'] += 1
                    stats['total_spent'] += charge
                elif status in [OrderStatus.PENDING, OrderStatus.PROCESSING, OrderStatus.IN_PROGRESS]:
                    stats['active_orders'] += 1
                elif status == OrderStatus.FAILED:
                    stats['failed_orders'] += 1

                # За категорією (потребує join з services)
                service = Service.get_by_id(order['service_id'])
                if service:
                    category = service.category.key
                    if category not in stats['orders_by_category']:
                        stats['orders_by_category'][category] = 0
                    stats['orders_by_category'][category] += 1

        # Округлюємо total_spent
        stats['total_spent'] = round(stats['total_spent'], 2)

        return jsonify({
            'success': True,
            'data': stats
        }), 200

    except Exception as e:
        logger.error(f"Error getting order statistics: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'STATISTICS_ERROR'
        }), 500