# backend/payments/webhooks.py
"""
TeleBoost Payment Webhooks
Обробка вебхуків від платіжних систем
"""
import hashlib
import hmac
import json
import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional

from backend.payments.services import process_payment_webhook
from backend.payments.models import Payment
from backend.config import config
from backend.utils.constants import PAYMENT_STATUS, PAYMENT_PROVIDERS

logger = logging.getLogger(__name__)

# Створюємо Blueprint
webhooks_bp = Blueprint('payment_webhooks', __name__)


@webhooks_bp.route('/api/webhooks/cryptobot', methods=['POST'])
def cryptobot_webhook():
    """
    Обробка webhook від CryptoBot

    CryptoBot webhook format:
    {
        "update_id": 12345,
        "update_type": "invoice_paid",
        "request_date": "2024-01-01T00:00:00Z",
        "payload": {
            "invoice_id": 123,
            "status": "paid",
            "hash": "...",
            "asset": "USDT",
            "amount": "100.0",
            "paid_at": "2024-01-01T00:00:00Z",
            "payload": "payment_id_from_our_system"
        }
    }
    """
    try:
        # Отримуємо дані
        data = request.get_json()

        if not data:
            logger.error("CryptoBot webhook: No data received")
            return jsonify({'error': 'No data'}), 400

        # Логуємо webhook
        logger.info(f"CryptoBot webhook received: {data.get('update_type')}")

        # Перевіряємо підпис
        if not _verify_cryptobot_signature(request):
            logger.error("CryptoBot webhook: Invalid signature")
            return jsonify({'error': 'Invalid signature'}), 401

        # Обробляємо різні типи подій
        update_type = data.get('update_type')

        if update_type == 'invoice_paid':
            _handle_cryptobot_invoice_paid(data.get('payload', {}))
        elif update_type == 'invoice_expired':
            _handle_cryptobot_invoice_expired(data.get('payload', {}))
        else:
            logger.warning(f"CryptoBot webhook: Unknown update type {update_type}")

        return jsonify({'ok': True}), 200

    except Exception as e:
        logger.error(f"CryptoBot webhook error: {e}")
        return jsonify({'error': 'Internal error'}), 500


@webhooks_bp.route('/api/webhooks/nowpayments', methods=['POST'])
def nowpayments_webhook():
    """
    Обробка IPN webhook від NOWPayments

    NOWPayments IPN format:
    {
        "payment_id": 12345,
        "payment_status": "finished",
        "pay_address": "TRC20_address",
        "price_amount": 100.5,
        "price_currency": "usd",
        "pay_amount": 100.5,
        "pay_currency": "usdt",
        "order_id": "our_payment_id",
        "order_description": "Deposit",
        "ipn_callback_url": "https://...",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "purchase_id": "12345",
        "actually_paid": 100.5,
        "outcome_amount": 100.5,
        "outcome_currency": "usdt"
    }
    """
    try:
        # Отримуємо дані
        data = request.get_json()

        if not data:
            logger.error("NOWPayments webhook: No data received")
            return jsonify({'error': 'No data'}), 400

        # Логуємо webhook
        payment_status = data.get('payment_status')
        logger.info(f"NOWPayments webhook received: status={payment_status}")

        # Перевіряємо підпис
        signature = request.headers.get('X-Nowpayments-Sig')
        if not _verify_nowpayments_signature(signature, request.data):
            logger.error("NOWPayments webhook: Invalid signature")
            return jsonify({'error': 'Invalid signature'}), 401

        # Обробляємо статуси
        _handle_nowpayments_status_update(data)

        return jsonify({'ok': True}), 200

    except Exception as e:
        logger.error(f"NOWPayments webhook error: {e}")
        return jsonify({'error': 'Internal error'}), 500


def _verify_cryptobot_signature(request) -> bool:
    """
    Перевірка підпису CryptoBot webhook

    CryptoBot використовує SHA256 HMAC з токеном як ключ
    """
    try:
        # Отримуємо підпис з заголовка
        signature = request.headers.get('X-Crypto-Bot-Api-Signature')
        if not signature:
            logger.error("CryptoBot signature missing")
            return False

        # Отримуємо тіло запиту
        body = request.get_data(as_text=True)

        # Обчислюємо очікуваний підпис
        expected_signature = hmac.new(
            key=config.CRYPTOBOT_WEBHOOK_TOKEN.encode('utf-8'),
            msg=body.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        # Порівнюємо підписи
        return hmac.compare_digest(signature, expected_signature)

    except Exception as e:
        logger.error(f"Error verifying CryptoBot signature: {e}")
        return False


def _verify_nowpayments_signature(signature: Optional[str], body: bytes) -> bool:
    """
    Перевірка підпису NOWPayments IPN

    NOWPayments використовує HMAC SHA512 з IPN Secret
    """
    try:
        if not signature:
            logger.error("NOWPayments signature missing")
            return False

        # Сортуємо JSON ключі для консистентності
        data = json.loads(body)
        sorted_json = json.dumps(data, sort_keys=True, separators=(',', ':'))

        # Обчислюємо очікуваний підпис
        expected_signature = hmac.new(
            key=config.NOWPAYMENTS_IPN_SECRET.encode('utf-8'),
            msg=sorted_json.encode('utf-8'),
            digestmod=hashlib.sha512
        ).hexdigest()

        # Порівнюємо підписи
        return hmac.compare_digest(signature.lower(), expected_signature.lower())

    except Exception as e:
        logger.error(f"Error verifying NOWPayments signature: {e}")
        return False


def _handle_cryptobot_invoice_paid(payload: Dict[str, Any]) -> None:
    """
    Обробка оплаченого інвойсу CryptoBot
    """
    try:
        # Отримуємо наш payment_id з payload
        our_payment_id = payload.get('payload')
        if not our_payment_id:
            logger.error("CryptoBot: No payment_id in payload")
            return

        # Отримуємо платіж
        payment = Payment.get_by_id(our_payment_id)
        if not payment:
            logger.error(f"Payment not found: {our_payment_id}")
            return

        # Перевіряємо що це наш платіж через CryptoBot
        if payment.provider != PAYMENT_PROVIDERS.CRYPTOBOT:
            logger.error(f"Payment {our_payment_id} is not CryptoBot payment")
            return

        # Оновлюємо payment_id якщо ще не встановлений
        if not payment.payment_id:
            payment.update({
                'payment_id': str(payload.get('invoice_id'))
            })

        # Формуємо дані для оновлення
        webhook_data = {
            'payment_id': str(payload.get('invoice_id')),
            'status': PAYMENT_STATUS.CONFIRMED,
            'metadata': {
                'cryptobot_hash': payload.get('hash'),
                'asset': payload.get('asset'),
                'amount': payload.get('amount'),
                'paid_at': payload.get('paid_at'),
            }
        }

        # Обробляємо через сервіс
        process_payment_webhook(PAYMENT_PROVIDERS.CRYPTOBOT, webhook_data)

        logger.info(f"CryptoBot payment confirmed: {our_payment_id}")

    except Exception as e:
        logger.error(f"Error handling CryptoBot invoice paid: {e}")


def _handle_cryptobot_invoice_expired(payload: Dict[str, Any]) -> None:
    """
    Обробка простроченого інвойсу CryptoBot
    """
    try:
        # Отримуємо наш payment_id
        our_payment_id = payload.get('payload')
        if not our_payment_id:
            return

        # Отримуємо платіж
        payment = Payment.get_by_id(our_payment_id)
        if not payment:
            return

        # Оновлюємо статус на expired
        payment.update_status(PAYMENT_STATUS.EXPIRED)

        logger.info(f"CryptoBot payment expired: {our_payment_id}")

    except Exception as e:
        logger.error(f"Error handling CryptoBot invoice expired: {e}")


def _handle_nowpayments_status_update(data: Dict[str, Any]) -> None:
    """
    Обробка оновлення статусу NOWPayments
    """
    try:
        # Отримуємо наш payment_id з order_id
        our_payment_id = data.get('order_id')
        if not our_payment_id:
            logger.error("NOWPayments: No order_id in data")
            return

        # Отримуємо платіж
        payment = Payment.get_by_id(our_payment_id)
        if not payment:
            logger.error(f"Payment not found: {our_payment_id}")
            return

        # Перевіряємо що це наш платіж через NOWPayments
        if payment.provider != PAYMENT_PROVIDERS.NOWPAYMENTS:
            logger.error(f"Payment {our_payment_id} is not NOWPayments payment")
            return

        # Оновлюємо payment_id якщо ще не встановлений
        if not payment.payment_id:
            payment.update({
                'payment_id': str(data.get('payment_id'))
            })

        # Мапимо статуси NOWPayments на наші
        status_map = {
            'waiting': PAYMENT_STATUS.WAITING,
            'confirming': PAYMENT_STATUS.CONFIRMING,
            'confirmed': PAYMENT_STATUS.CONFIRMED,
            'sending': PAYMENT_STATUS.SENDING,
            'partially_paid': PAYMENT_STATUS.PARTIALLY_PAID,
            'finished': PAYMENT_STATUS.FINISHED,
            'failed': PAYMENT_STATUS.FAILED,
            'refunded': PAYMENT_STATUS.REFUNDED,
            'expired': PAYMENT_STATUS.EXPIRED,
        }

        nowpayments_status = data.get('payment_status')
        our_status = status_map.get(nowpayments_status)

        if not our_status:
            logger.warning(f"Unknown NOWPayments status: {nowpayments_status}")
            return

        # Формуємо дані для оновлення
        webhook_data = {
            'payment_id': str(data.get('payment_id')),
            'status': our_status,
            'metadata': {
                'pay_address': data.get('pay_address'),
                'price_amount': data.get('price_amount'),
                'price_currency': data.get('price_currency'),
                'pay_amount': data.get('pay_amount'),
                'pay_currency': data.get('pay_currency'),
                'actually_paid': data.get('actually_paid'),
                'outcome_amount': data.get('outcome_amount'),
                'outcome_currency': data.get('outcome_currency'),
                'purchase_id': data.get('purchase_id'),
                'created_at': data.get('created_at'),
                'updated_at': data.get('updated_at'),
            }
        }

        # Обробляємо через сервіс
        process_payment_webhook(PAYMENT_PROVIDERS.NOWPAYMENTS, webhook_data)

        logger.info(f"NOWPayments payment status updated: {our_payment_id} -> {our_status}")

    except Exception as e:
        logger.error(f"Error handling NOWPayments status update: {e}")


# Додаткові функції для тестування webhook підписів

def generate_test_cryptobot_signature(body: str) -> str:
    """
    Генерація тестового підпису CryptoBot

    Використовується для тестування
    """
    return hmac.new(
        key=config.CRYPTOBOT_TOKEN.encode('utf-8'),
        msg=body.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()


def generate_test_nowpayments_signature(data: Dict[str, Any]) -> str:
    """
    Генерація тестового підпису NOWPayments

    Використовується для тестування
    """
    sorted_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hmac.new(
        key=config.NOWPAYMENTS_IPN_SECRET.encode('utf-8'),
        msg=sorted_json.encode('utf-8'),
        digestmod=hashlib.sha512
    ).hexdigest()