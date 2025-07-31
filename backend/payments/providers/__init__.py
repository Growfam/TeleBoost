# backend/payments/providers/__init__.py
"""
TeleBoost Payment Providers
Фабрика платіжних провайдерів
"""
import logging
from typing import Optional

from backend.payments.providers.base import BasePaymentProvider
from backend.payments.providers.cryptobot import CryptoBotProvider
from backend.payments.providers.nowpayments import NOWPaymentsProvider
from backend.config import config

logger = logging.getLogger(__name__)


class PAYMENT_PROVIDERS:
    """Константи платіжних провайдерів"""
    CRYPTOBOT = 'cryptobot'
    NOWPAYMENTS = 'nowpayments'
    MONOBANK = 'monobank'


def get_payment_provider(provider_name: str) -> Optional[BasePaymentProvider]:
    """
    Отримати платіжний провайдер за назвою

    Args:
        provider_name: Назва провайдера

    Returns:
        Екземпляр провайдера або None
    """
    try:
        if provider_name == PAYMENT_PROVIDERS.CRYPTOBOT:
            if config.CRYPTOBOT_TOKEN:
                return CryptoBotProvider()
            else:
                logger.warning("CryptoBot token not configured")

        elif provider_name == PAYMENT_PROVIDERS.NOWPAYMENTS:
            if config.NOWPAYMENTS_API_KEY:
                return NOWPaymentsProvider()
            else:
                logger.warning("NOWPayments API key not configured")

        else:
            logger.error(f"Unknown payment provider: {provider_name}")

    except Exception as e:
        logger.error(f"Error creating payment provider {provider_name}: {e}")

    return None


def get_available_providers() -> list:
    """
    Отримати список доступних провайдерів

    Returns:
        Список назв провайдерів
    """
    available = []

    if config.CRYPTOBOT_TOKEN:
        available.append(PAYMENT_PROVIDERS.CRYPTOBOT)

    if config.NOWPAYMENTS_API_KEY:
        available.append(PAYMENT_PROVIDERS.NOWPAYMENTS)

    if config.MONOBANK_TOKEN:
        available.append(PAYMENT_PROVIDERS.MONOBANK)

    return available


__all__ = [
    'BasePaymentProvider',
    'CryptoBotProvider',
    'NOWPaymentsProvider',
    'get_payment_provider',
    'get_available_providers',
    'PAYMENT_PROVIDERS'
]