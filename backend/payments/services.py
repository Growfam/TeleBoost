# backend/payments/services.py
"""
TeleBoost Payment Services
Бізнес-логіка платіжної системи
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta

from backend.payments.models import Payment, PaymentMethod
from backend.payments.providers import get_payment_provider
from backend.supabase_client import supabase
from backend.utils.redis_client import cache_get, cache_set
from backend.utils.constants import (
    PAYMENT_STATUS, PAYMENT_PROVIDERS, TRANSACTION_TYPE,
    LIMITS, CRYPTO_CURRENCIES
)

logger = logging.getLogger(__name__)


class PaymentService:
    """Сервіс для роботи з платежами"""

    def __init__(self):
        """Ініціалізація сервісу"""
        self.providers = {}
        self._init_providers()

    def _init_providers(self):
        """Ініціалізація платіжних провайдерів"""
        try:
            # CryptoBot
            cryptobot = get_payment_provider(PAYMENT_PROVIDERS.CRYPTOBOT)
            if cryptobot:
                self.providers[PAYMENT_PROVIDERS.CRYPTOBOT] = cryptobot
                logger.info("CryptoBot provider initialized")

            # NOWPayments
            nowpayments = get_payment_provider(PAYMENT_PROVIDERS.NOWPAYMENTS)
            if nowpayments:
                self.providers[PAYMENT_PROVIDERS.NOWPAYMENTS] = nowpayments
                logger.info("NOWPayments provider initialized")

        except Exception as e:
            logger.error(f"Error initializing payment providers: {e}")

    def create_payment(self, user_id: str, amount: Decimal, currency: str,
                       provider: str, network: Optional[str] = None) -> Optional[Payment]:
        """
        Створити новий платіж

        Args:
            user_id: ID користувача
            amount: Сума
            currency: Валюта
            provider: Провайдер
            network: Мережа (для NOWPayments)

        Returns:
            Payment об'єкт або None
        """
        try:
            # Перевіряємо провайдера
            if provider not in self.providers:
                logger.error(f"Unknown payment provider: {provider}")
                return None

            payment_provider = self.providers[provider]

            # Створюємо платіж через провайдера
            provider_result = payment_provider.create_payment(
                amount=amount,
                currency=currency,
                network=network
            )

            if not provider_result:
                logger.error(f"Provider {provider} failed to create payment")
                return None

            # Створюємо запис в БД
            payment_data = {
                'user_id': user_id,
                'payment_id': provider_result['payment_id'],
                'provider': provider,
                'type': 'deposit',
                'amount': float(amount),
                'currency': currency,
                'status': PAYMENT_STATUS.WAITING,
                'payment_url': provider_result.get('payment_url'),
                'expires_at': provider_result.get('expires_at'),
                'metadata': {
                    'network': network,
                    'provider_data': provider_result.get('metadata', {})
                }
            }

            payment = Payment.create(payment_data)

            if payment:
                logger.info(f"Created payment {payment.id} via {provider}")

            return payment

        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            return None

    def check_payment_status(self, payment_id: str) -> bool:
        """
        Перевірити та оновити статус платежу

        Args:
            payment_id: ID платежу

        Returns:
            True якщо статус оновлено
        """
        try:
            # Отримуємо платіж
            payment = Payment.get_by_id(payment_id)

            if not payment:
                logger.error(f"Payment {payment_id} not found")
                return False

            # Якщо платіж вже завершений - нічого не робимо
            if payment.status in [PAYMENT_STATUS.FINISHED, PAYMENT_STATUS.FAILED]:
                return False

            # Отримуємо провайдера
            provider = self.providers.get(payment.provider)
            if not provider:
                logger.error(f"Provider {payment.provider} not found")
                return False

            # Перевіряємо статус через провайдера
            status_result = provider.check_payment_status(payment.payment_id)

            if not status_result:
                return False

            new_status = status_result.get('status')

            # Якщо статус змінився
            if new_status and new_status != payment.status:
                # Оновлюємо статус
                payment.update_status(new_status, status_result.get('metadata'))

                # Якщо платіж успішний - нараховуємо баланс
                if new_status in [PAYMENT_STATUS.CONFIRMED, PAYMENT_STATUS.FINISHED]:
                    self._process_successful_payment(payment)

                return True

            return False

        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return False

    def _process_successful_payment(self, payment: Payment) -> bool:
        """
        Обробити успішний платіж

        Args:
            payment: Платіж

        Returns:
            True якщо успішно
        """
        try:
            # Перевіряємо чи не оброблений вже
            if payment.metadata.get('processed'):
                logger.warning(f"Payment {payment.id} already processed")
                return True

            # Оновлюємо баланс користувача
            balance_updated = supabase.update_user_balance(
                payment.user_id,
                payment.amount,
                operation='add'
            )

            if not balance_updated:
                logger.error(f"Failed to update balance for payment {payment.id}")
                return False

            # Створюємо транзакцію
            transaction_data = {
                'user_id': payment.user_id,
                'type': TRANSACTION_TYPE.DEPOSIT,
                'amount': float(payment.amount),
                'description': f'Поповнення через {payment.provider.upper()}',
                'metadata': {
                    'payment_id': payment.id,
                    'provider': payment.provider,
                    'currency': payment.currency,
                    'external_id': payment.payment_id
                }
            }

            transaction = supabase.create_transaction(transaction_data)

            if transaction:
                # Позначаємо платіж як оброблений
                payment.update({
                    'metadata': {**payment.metadata, 'processed': True}
                })

                logger.info(f"Successfully processed payment {payment.id}")

                # Обробляємо реферальні бонуси
                from backend.referrals.services import process_deposit_referral_bonuses
                process_deposit_referral_bonuses(payment.user_id, float(payment.amount))

                return True

            return False

        except Exception as e:
            logger.error(f"Error processing successful payment: {e}")
            return False

    def process_webhook(self, provider: str, data: Dict[str, Any]) -> bool:
        """
        Обробити webhook від провайдера

        Args:
            provider: Назва провайдера
            data: Дані webhook

        Returns:
            True якщо успішно
        """
        try:
            payment_provider = self.providers.get(provider)

            if not payment_provider:
                logger.error(f"Unknown provider for webhook: {provider}")
                return False

            # Обробляємо webhook через провайдера
            webhook_result = payment_provider.process_webhook(data)

            if not webhook_result:
                return False

            # Отримуємо платіж
            payment_id = webhook_result.get('payment_id')
            payment = Payment.get_by_payment_id(payment_id, provider)

            if not payment:
                logger.error(f"Payment not found for webhook: {payment_id}")
                return False

            # Оновлюємо статус
            new_status = webhook_result.get('status')
            if new_status and new_status != payment.status:
                payment.update_status(new_status, webhook_result.get('metadata'))

                # Обробляємо успішний платіж
                if new_status in [PAYMENT_STATUS.CONFIRMED, PAYMENT_STATUS.FINISHED]:
                    self._process_successful_payment(payment)

            return True

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return False

    def get_available_methods(self) -> List[Dict[str, Any]]:
        """Отримати доступні методи оплати"""
        methods = []

        # CryptoBot
        if PAYMENT_PROVIDERS.CRYPTOBOT in self.providers:
            methods.append({
                'provider': PAYMENT_PROVIDERS.CRYPTOBOT,
                'name': 'CryptoBot',
                'currencies': ['USDT', 'BTC', 'TON'],
                'limits': {
                    'USDT': {'min': 1, 'max': 100000},
                    'BTC': {'min': 0.0001, 'max': 10},
                    'TON': {'min': 5, 'max': 100000}
                },
                'fee': 0,
                'processing_time': '1-5 minutes'
            })

        # NOWPayments
        if PAYMENT_PROVIDERS.NOWPAYMENTS in self.providers:
            methods.append({
                'provider': PAYMENT_PROVIDERS.NOWPAYMENTS,
                'name': 'NOWPayments',
                'currencies': ['USDT'],
                'networks': ['TRC20', 'BEP20', 'SOL', 'TON'],
                'limits': {
                    'USDT': {'min': 10, 'max': 100000}
                },
                'fee': 0,
                'processing_time': '10-30 minutes'
            })

        return methods


# Створюємо глобальний екземпляр сервісу
payment_service = PaymentService()


# Експортовані функції
def create_payment(user_id: str, amount: Decimal, currency: str,
                   provider: str, network: Optional[str] = None) -> Optional[Payment]:
    """Створити платіж"""
    return payment_service.create_payment(user_id, amount, currency, provider, network)


def get_payment(payment_id: str) -> Optional[Payment]:
    """Отримати платіж"""
    return Payment.get_by_id(payment_id)


def check_payment_status(payment_id: str) -> bool:
    """Перевірити статус платежу"""
    return payment_service.check_payment_status(payment_id)


def process_payment_webhook(provider: str, data: Dict[str, Any]) -> bool:
    """Обробити webhook"""
    return payment_service.process_webhook(provider, data)


def get_user_payments(user_id: str, status: Optional[str] = None,
                      limit: int = 50, offset: int = 0) -> List[Payment]:
    """Отримати платежі користувача"""
    return Payment.get_user_payments(user_id, status, limit, offset)


def get_available_methods() -> List[Dict[str, Any]]:
    """Отримати доступні методи оплати"""
    return payment_service.get_available_methods()


def get_payment_limits() -> Dict[str, Any]:
    """Отримати ліміти платежів"""
    return {
        'min_deposit': LIMITS['MIN_DEPOSIT'],
        'max_deposit': LIMITS['MAX_DEPOSIT'],
        'currencies': {
            'USDT': {
                'min': 10,
                'max': 100000,
                'decimals': 6
            },
            'BTC': {
                'min': 0.0001,
                'max': 10,
                'decimals': 8
            },
            'TON': {
                'min': 5,
                'max': 100000,
                'decimals': 9
            }
        }
    }


def calculate_crypto_amount(amount: Decimal, from_currency: str,
                            to_currency: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """
    Розрахувати суму в криптовалюті

    Args:
        amount: Сума
        from_currency: З валюти
        to_currency: В валюту

    Returns:
        (result, rate) або (None, None)
    """
    try:
        # Простий розрахунок для USD/USDT
        if from_currency == 'USD' and to_currency == 'USDT':
            rate = Decimal('1.01')  # Приклад курсу
            result = amount * rate
            return result, rate

        # Для інших пар потрібна інтеграція з API курсів
        # TODO: Implement real exchange rates

        return None, None

    except Exception as e:
        logger.error(f"Error calculating crypto amount: {e}")
        return None, None