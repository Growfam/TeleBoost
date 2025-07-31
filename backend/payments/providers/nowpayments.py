# backend/payments/providers/nowpayments.py
"""
TeleBoost NOWPayments Provider
Інтеграція з NOWPayments API
"""
import logging
import requests
import hashlib
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timedelta
from urllib.parse import urljoin

from backend.payments.providers.base import BasePaymentProvider
from backend.config import config
from backend.utils.constants import PAYMENT_STATUS

logger = logging.getLogger(__name__)


class NOWPaymentsProvider(BasePaymentProvider):
    """
    NOWPayments платіжний провайдер

    Підтримує:
    - USDT (TRC20, BEP20, SOL, TON)
    - BTC, ETH, BNB, TRX та інші
    """

    def __init__(self):
        """Ініціалізація провайдера"""
        super().__init__()
        self.name = 'nowpayments'
        self.api_key = config.NOWPAYMENTS_API_KEY
        self.ipn_secret = config.NOWPAYMENTS_IPN_SECRET

        # API URLs
        if config.NOWPAYMENTS_SANDBOX:
            self.base_url = 'https://api-sandbox.nowpayments.io/v1/'
        else:
            self.base_url = 'https://api.nowpayments.io/v1/'

        # Headers для API запитів
        self.headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # Підтримувані валюти та мережі
        self.supported_currencies = {
            'USDT': ['TRC20', 'BEP20', 'SOL', 'TON'],
            'BTC': [None],  # Тільки основна мережа
            'ETH': [None],
            'BNB': ['BEP20'],
            'TRX': [None],
        }

        # Мінімальні суми (в USD еквіваленті)
        self.min_amounts = {
            'USDT': 10,
            'BTC': 10,
            'ETH': 10,
            'BNB': 10,
            'TRX': 10,
        }

        logger.info(f"NOWPayments provider initialized (sandbox: {config.NOWPAYMENTS_SANDBOX})")

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Виконати API запит

        Args:
            method: HTTP метод
            endpoint: API endpoint
            data: Дані запиту

        Returns:
            Відповідь API або None
        """
        try:
            url = urljoin(self.base_url, endpoint)

            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                timeout=30
            )

            # Логуємо для debug
            logger.debug(f"NOWPayments API {method} {endpoint}: {response.status_code}")

            # Перевіряємо статус
            if response.status_code == 401:
                logger.error("NOWPayments API: Authentication failed")
                return None
            elif response.status_code == 422:
                logger.error(f"NOWPayments API: Validation error: {response.text}")
                return None
            elif response.status_code >= 400:
                logger.error(f"NOWPayments API error: {response.status_code} - {response.text}")
                return None

            return response.json()

        except requests.exceptions.Timeout:
            logger.error("NOWPayments API: Request timeout")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"NOWPayments API request error: {e}")
            return None
        except Exception as e:
            logger.error(f"NOWPayments API unexpected error: {e}")
            return None

    def get_available_currencies(self) -> List[str]:
        """
        Отримати список доступних валют

        Returns:
            Список валют
        """
        try:
            result = self._make_request('GET', 'currencies')

            if result and 'currencies' in result:
                return result['currencies']

            return []

        except Exception as e:
            logger.error(f"Error getting available currencies: {e}")
            return []

    def get_minimum_payment_amount(self, currency_from: str, currency_to: str) -> Optional[float]:
        """
        Отримати мінімальну суму платежу

        Args:
            currency_from: Валюта платежу (fiat)
            currency_to: Криптовалюта

        Returns:
            Мінімальна сума або None
        """
        try:
            params = {
                'currency_from': currency_from.lower(),
                'currency_to': currency_to.lower()
            }

            result = self._make_request('GET', f'min-amount?{urlencode(params)}')

            if result and 'min_amount' in result:
                return float(result['min_amount'])

            return None

        except Exception as e:
            logger.error(f"Error getting minimum amount: {e}")
            return None

    def estimate_price(self, amount: float, currency_from: str, currency_to: str) -> Optional[Dict]:
        """
        Отримати приблизну ціну конвертації

        Args:
            amount: Сума
            currency_from: З валюти
            currency_to: В валюту

        Returns:
            Інформація про конвертацію
        """
        try:
            params = {
                'amount': amount,
                'currency_from': currency_from.lower(),
                'currency_to': currency_to.lower()
            }

            result = self._make_request('GET', f'estimate?{urlencode(params)}')

            if result:
                return {
                    'estimated_amount': float(result.get('estimated_amount', 0)),
                    'rate': float(result.get('rate', 0))
                }

            return None

        except Exception as e:
            logger.error(f"Error estimating price: {e}")
            return None

    def create_payment(self, amount: Decimal, currency: str,
                       network: Optional[str] = None, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Створити платіж

        Args:
            amount: Сума в USD
            currency: Криптовалюта
            network: Мережа (для USDT)

        Returns:
            Дані платежу або None
        """
        try:
            # Валідація валюти
            currency = currency.upper()
            if currency not in self.supported_currencies:
                logger.error(f"Unsupported currency: {currency}")
                return None

            # Формуємо валюту з мережею
            pay_currency = currency.lower()
            if network and currency == 'USDT':
                # Мапимо мережі на NOWPayments формат
                network_map = {
                    'TRC20': 'usdttrc20',
                    'BEP20': 'usdtbsc',  # BSC = BEP20
                    'SOL': 'usdtsol',
                    'TON': 'usdtton'
                }
                pay_currency = network_map.get(network, 'usdttrc20')

            # Готуємо дані для створення платежу
            payment_data = {
                'price_amount': float(amount),
                'price_currency': 'usd',
                'pay_currency': pay_currency,
                'ipn_callback_url': config.get_webhook_url(config.NOWPAYMENTS_WEBHOOK_PATH),
                'order_id': kwargs.get('order_id', ''),  # Наш внутрішній ID
                'order_description': 'TeleBoost Deposit',
                'is_fixed_rate': False,  # Плаваючий курс
                'is_fee_paid_by_user': True,  # Користувач платить комісію
            }

            # Додаємо success URL якщо є
            if 'success_url' in kwargs:
                payment_data['success_url'] = kwargs['success_url']

            # Додаємо email якщо є
            if 'payout_email' in kwargs:
                payment_data['payout_email'] = kwargs['payout_email']

            # Створюємо платіж
            result = self._make_request('POST', 'payment', payment_data)

            if not result:
                logger.error("Failed to create NOWPayments payment")
                return None

            # Перевіряємо обов'язкові поля
            if 'payment_id' not in result or 'pay_address' not in result:
                logger.error(f"Invalid NOWPayments response: {result}")
                return None

            # Формуємо відповідь
            return {
                'payment_id': str(result['payment_id']),
                'payment_url': result.get('invoice_url'),  # Якщо використовується invoice
                'address': result['pay_address'],
                'amount': result.get('pay_amount'),
                'currency': result.get('pay_currency'),
                'expires_at': self._calculate_expiry(result.get('expiry_estimate', 3600)),
                'metadata': {
                    'price_amount': result.get('price_amount'),
                    'price_currency': result.get('price_currency'),
                    'pay_amount': result.get('pay_amount'),
                    'pay_currency': result.get('pay_currency'),
                    'network': network,
                    'payment_status': result.get('payment_status'),
                    'purchase_id': result.get('purchase_id'),
                }
            }

        except Exception as e:
            logger.error(f"Error creating NOWPayments payment: {e}")
            return None

    def check_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Перевірити статус платежу

        Args:
            payment_id: ID платежу в NOWPayments

        Returns:
            Статус та деталі або None
        """
        try:
            result = self._make_request('GET', f'payment/{payment_id}')

            if not result:
                return None

            # Мапимо статуси
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

            nowpayments_status = result.get('payment_status')
            our_status = status_map.get(nowpayments_status, PAYMENT_STATUS.PROCESSING)

            return {
                'status': our_status,
                'original_status': nowpayments_status,
                'metadata': {
                    'pay_address': result.get('pay_address'),
                    'pay_amount': result.get('pay_amount'),
                    'actually_paid': result.get('actually_paid'),
                    'outcome_amount': result.get('outcome_amount'),
                    'confirmations': result.get('confirmations'),
                    'created_at': result.get('created_at'),
                    'updated_at': result.get('updated_at'),
                }
            }

        except Exception as e:
            logger.error(f"Error checking NOWPayments status: {e}")
            return None

    def process_webhook(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обробити webhook від NOWPayments

        Args:
            data: Дані webhook (вже перевірені в webhooks.py)

        Returns:
            Оброблені дані або None
        """
        try:
            # Мапимо статуси
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
                return None

            return {
                'payment_id': str(data.get('payment_id')),
                'status': our_status,
                'metadata': data  # Зберігаємо всі дані
            }

        except Exception as e:
            logger.error(f"Error processing NOWPayments webhook: {e}")
            return None

    def get_payment_address(self, payment_id: str) -> Optional[str]:
        """
        Отримати адресу для оплати

        Args:
            payment_id: ID платежу

        Returns:
            Адреса або None
        """
        try:
            status = self.check_payment_status(payment_id)

            if status and 'metadata' in status:
                return status['metadata'].get('pay_address')

            return None

        except Exception as e:
            logger.error(f"Error getting payment address: {e}")
            return None

    def _calculate_expiry(self, seconds: int) -> str:
        """
        Розрахувати час закінчення платежу

        Args:
            seconds: Кількість секунд до закінчення

        Returns:
            ISO дата
        """
        expiry_time = datetime.utcnow() + timedelta(seconds=seconds)
        return expiry_time.isoformat() + 'Z'

    def create_invoice(self, amount: Decimal, currency: str,
                       network: Optional[str] = None, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Створити інвойс (альтернативний метод)

        NOWPayments також підтримує інвойси з веб-інтерфейсом
        """
        try:
            # Формуємо валюту з мережею
            pay_currency = currency.lower()
            if network and currency == 'USDT':
                network_map = {
                    'TRC20': 'usdttrc20',
                    'BEP20': 'usdtbsc',
                    'SOL': 'usdtsol',
                    'TON': 'usdtton'
                }
                pay_currency = network_map.get(network, 'usdttrc20')

            invoice_data = {
                'price_amount': float(amount),
                'price_currency': 'usd',
                'pay_currency': pay_currency,
                'ipn_callback_url': config.get_webhook_url(config.NOWPAYMENTS_WEBHOOK_PATH),
                'order_id': kwargs.get('order_id', ''),
                'order_description': 'TeleBoost Deposit',
                'success_url': kwargs.get('success_url', config.FRONTEND_URL),
                'cancel_url': kwargs.get('cancel_url', config.FRONTEND_URL),
                'is_fixed_rate': False,
                'is_fee_paid_by_user': True,
            }

            result = self._make_request('POST', 'invoice', invoice_data)

            if not result:
                return None

            return {
                'payment_id': str(result['id']),
                'payment_url': result['invoice_url'],
                'expires_at': self._calculate_expiry(3600),  # 1 година
                'metadata': {
                    'invoice_id': result['id'],
                    'order_id': result.get('order_id'),
                }
            }

        except Exception as e:
            logger.error(f"Error creating NOWPayments invoice: {e}")
            return None

    def get_available_networks(self, currency: str) -> List[str]:
        """
        Отримати доступні мережі для валюти

        Args:
            currency: Валюта

        Returns:
            Список мереж
        """
        return self.supported_currencies.get(currency.upper(), [])