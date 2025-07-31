# backend/payments/__init__.py
"""
TeleBoost Payments Package
Платіжна система з підтримкою CryptoBot та NOWPayments
"""

from backend.payments.models import Payment, PaymentMethod
from backend.payments.services import (
    payment_service,  # Екземпляр сервісу
    create_payment,
    get_payment,
    check_payment_status,
    process_payment_webhook,
    get_user_payments,
    get_available_methods,
    get_payment_limits,
    calculate_crypto_amount,
)
from backend.payments.validators import (
    validate_payment_amount,
    validate_crypto_address,
    validate_payment_currency,
    validate_payment_data,
)

__all__ = [
    # Models
    'Payment',
    'PaymentMethod',

    # Service instance
    'payment_service',

    # Functions
    'create_payment',
    'get_payment',
    'check_payment_status',
    'process_payment_webhook',
    'get_user_payments',
    'get_available_methods',
    'get_payment_limits',
    'calculate_crypto_amount',

    # Validators
    'validate_payment_amount',
    'validate_crypto_address',
    'validate_payment_currency',
    'validate_payment_data',
]