# backend/payments/routes.py
"""
TeleBoost Payments Routes
API endpoints для платіжної системи
"""
import logging
from flask import Blueprint, request, jsonify, g
from decimal import Decimal

from backend.auth.decorators import jwt_required, rate_limit
from backend.payments.services import (
    create_payment,
    get_payment,
    check_payment_status,
    get_user_payments,
    get_available_methods,
    get_payment_limits,
    calculate_crypto_amount,
)
from backend.payments.validators import (
    validate_payment_amount,
    validate_payment_currency,
    validate_payment_data,
)
from backend.utils.constants import SUCCESS_MESSAGES, ERROR_MESSAGES
from backend.utils.formatters import format_price

logger = logging.getLogger(__name__)

# Створюємо Blueprint
payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')


@payments_bp.route('/create', methods=['POST'])
@jwt_required
@rate_limit(calls=10, period=60)  # 10 платежів за хвилину
def create_payment_route():
    """
    Створити новий платіж

    Request body:
    {
        "amount": 100.50,
        "currency": "USDT",
        "provider": "cryptobot",  // або "nowpayments"
        "network": "TRC20"  // опціонально для NOWPayments
    }

    Response:
    {
        "success": true,
        "data": {
            "payment": {
                "id": "...",
                "payment_id": "...",
                "amount": 100.50,
                "currency": "USDT",
                "status": "waiting",
                "payment_url": "https://...",
                "expires_at": "2024-01-01T00:00:00Z"
            }
        }
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required',
                'code': 'MISSING_BODY'
            }), 400

        # Валідація даних
        is_valid, errors = validate_payment_data(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'code': 'VALIDATION_ERROR',
                'errors': errors
            }), 400

        # Отримуємо дані
        amount = Decimal(str(data['amount']))
        currency = data['currency'].upper()
        provider = data.get('provider', 'cryptobot')
        network = data.get('network')

        # Створюємо платіж
        payment = create_payment(
            user_id=g.current_user.id,
            amount=amount,
            currency=currency,
            provider=provider,
            network=network
        )

        if not payment:
            return jsonify({
                'success': False,
                'error': 'Failed to create payment',
                'code': 'PAYMENT_CREATION_FAILED'
            }), 500

        logger.info(f"Payment created: {payment.id} for user {g.current_user.telegram_id}")

        return jsonify({
            'success': True,
            'message': SUCCESS_MESSAGES['PAYMENT_CREATED'],
            'data': {
                'payment': payment.to_public_dict()
            }
        }), 201

    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'PAYMENT_ERROR'
        }), 500


@payments_bp.route('/<payment_id>', methods=['GET'])
@jwt_required
def get_payment_route(payment_id):
    """
    Отримати деталі платежу

    Response:
    {
        "success": true,
        "data": {
            "payment": {...}
        }
    }
    """
    try:
        payment = get_payment(payment_id)

        if not payment:
            return jsonify({
                'success': False,
                'error': ERROR_MESSAGES['PAYMENT_NOT_FOUND'],
                'code': 'PAYMENT_NOT_FOUND'
            }), 404

        # Перевіряємо що платіж належить користувачу
        if payment.user_id != g.current_user.id and not g.current_user.is_admin:
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'code': 'ACCESS_DENIED'
            }), 403

        return jsonify({
            'success': True,
            'data': {
                'payment': payment.to_public_dict()
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting payment {payment_id}: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'PAYMENT_ERROR'
        }), 500


@payments_bp.route('/<payment_id>/check', methods=['POST'])
@jwt_required
@rate_limit(calls=30, period=60)  # 30 перевірок за хвилину
def check_payment_route(payment_id):
    """
    Перевірити статус платежу

    Response:
    {
        "success": true,
        "data": {
            "status": "confirmed",
            "updated": true
        }
    }
    """
    try:
        payment = get_payment(payment_id)

        if not payment:
            return jsonify({
                'success': False,
                'error': ERROR_MESSAGES['PAYMENT_NOT_FOUND'],
                'code': 'PAYMENT_NOT_FOUND'
            }), 404

        # Перевіряємо що платіж належить користувачу
        if payment.user_id != g.current_user.id:
            return jsonify({
                'success': False,
                'error': 'Access denied',
                'code': 'ACCESS_DENIED'
            }), 403

        # Перевіряємо статус
        updated = check_payment_status(payment.id)

        # Отримуємо оновлений платіж
        payment = get_payment(payment_id)

        return jsonify({
            'success': True,
            'data': {
                'status': payment.status,
                'updated': updated,
                'payment': payment.to_public_dict()
            }
        }), 200

    except Exception as e:
        logger.error(f"Error checking payment {payment_id}: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'CHECK_ERROR'
        }), 500


@payments_bp.route('/', methods=['GET'])
@jwt_required
def get_user_payments_route():
    """
    Отримати список платежів користувача

    Query params:
    - status: Фільтр по статусу
    - page: Сторінка (default: 1)
    - limit: Елементів на сторінку (default: 20)

    Response:
    {
        "success": true,
        "data": {
            "payments": [...],
            "total": 10,
            "page": 1,
            "pages": 1
        }
    }
    """
    try:
        # Параметри
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))

        # Валідація
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 20

        offset = (page - 1) * limit

        # Отримуємо платежі
        payments = get_user_payments(
            user_id=g.current_user.id,
            status=status,
            limit=limit,
            offset=offset
        )

        # Конвертуємо в словники
        payments_data = [p.to_public_dict() for p in payments]

        # Рахуємо загальну кількість
        # TODO: Додати метод для підрахунку
        total = len(payments_data)

        return jsonify({
            'success': True,
            'data': {
                'payments': payments_data,
                'total': total,
                'page': page,
                'pages': (total + limit - 1) // limit
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting user payments: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'PAYMENTS_ERROR'
        }), 500


@payments_bp.route('/methods', methods=['GET'])
def get_payment_methods():
    """
    Отримати доступні методи оплати

    Response:
    {
        "success": true,
        "data": {
            "methods": [
                {
                    "provider": "cryptobot",
                    "currencies": ["USDT", "BTC", "TON"],
                    "limits": {...}
                },
                {
                    "provider": "nowpayments",
                    "currencies": ["USDT"],
                    "networks": ["TRC20", "BEP20", "SOL", "TON"],
                    "limits": {...}
                }
            ]
        }
    }
    """
    try:
        methods = get_available_methods()

        return jsonify({
            'success': True,
            'data': {
                'methods': methods
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting payment methods: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'METHODS_ERROR'
        }), 500


@payments_bp.route('/limits', methods=['GET'])
def get_limits():
    """
    Отримати ліміти платежів

    Response:
    {
        "success": true,
        "data": {
            "limits": {
                "min_deposit": 10,
                "max_deposit": 100000,
                "currencies": {
                    "USDT": {"min": 10, "max": 100000},
                    "BTC": {"min": 0.0001, "max": 10},
                    "TON": {"min": 5, "max": 100000}
                }
            }
        }
    }
    """
    try:
        limits = get_payment_limits()

        return jsonify({
            'success': True,
            'data': {
                'limits': limits
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting payment limits: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'LIMITS_ERROR'
        }), 500


@payments_bp.route('/calculate', methods=['POST'])
def calculate_amount():
    """
    Розрахувати суму в криптовалюті

    Request body:
    {
        "amount": 100,
        "from_currency": "USD",
        "to_currency": "USDT"
    }

    Response:
    {
        "success": true,
        "data": {
            "amount": 100,
            "from_currency": "USD",
            "to_currency": "USDT",
            "result": 100.50,
            "rate": 1.005
        }
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required',
                'code': 'MISSING_BODY'
            }), 400

        amount = Decimal(str(data.get('amount', 0)))
        from_currency = data.get('from_currency', 'USD').upper()
        to_currency = data.get('to_currency', 'USDT').upper()

        # Валідація суми
        if amount <= 0:
            return jsonify({
                'success': False,
                'error': 'Amount must be positive',
                'code': 'INVALID_AMOUNT'
            }), 400

        # Розраховуємо
        result, rate = calculate_crypto_amount(amount, from_currency, to_currency)

        if result is None:
            return jsonify({
                'success': False,
                'error': 'Calculation failed',
                'code': 'CALCULATION_ERROR'
            }), 500

        return jsonify({
            'success': True,
            'data': {
                'amount': float(amount),
                'from_currency': from_currency,
                'to_currency': to_currency,
                'result': float(result),
                'rate': float(rate)
            }
        }), 200

    except Exception as e:
        logger.error(f"Error calculating amount: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'CALCULATION_ERROR'
        }), 500