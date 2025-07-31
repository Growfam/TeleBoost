# backend/payments/providers/cryptobot.py
"""
TeleBoost CryptoBot Provider
Інтеграція з @CryptoBot платіжною системою
"""
import json
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal

from backend.payments.providers.base import BasePaymentProvider
from backend.config import config
from backend.utils.constants import PAYMENT_STATUS, CRYPTO_CURRENCIES

logger = logging.getLogger(__name__)


class CryptoBotProvider(BasePaymentProvider):
    """
    CryptoBot Payment Provider

    Docs: https://help.crypt.bot/crypto-pay-api
    """

    def __init__(self):
        """Ініціалізація CryptoBot провайдера"""
        super().__init__()
        self.name = 'cryptobot'
        self.api_token = config.CRYPTOBOT_TOKEN
        self.base_url = 'https://pay.crypt.bot/api'

        # Тестовий режим
        if config.CRYPTOBOT_NETWORK == 'testnet':
            self.base_url = 'https://testnet-pay.crypt.bot/api'

        # Налаштування
        self.supported_currencies = ['USDT', 'BTC', 'TON', 'ETH', 'BUSD', 'BNB']
        self.invoice_lifetime = 3600  # 1 година

        # HTTP сесія
        self.session = requests.Session()
        self.session.headers.update({
            'Crypto-Pay-API-Token': self.api_token,
            'Content-Type': 'application/json'
        })

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Виконати запит до CryptoBot API

        Args:
            method: HTTP метод
            endpoint: API endpoint
            data: Дані запиту

        Returns:
            Відповідь API
        """
        url = f"{self.base_url}/{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                timeout=30
            )

            # Логуємо запит
            logger.debug(f"CryptoBot API {method} {endpoint}: {response.status_code}")

            # Перевіряємо статус
            response.raise_for_status()

            # Парсимо відповідь
            result = response.json()

            # CryptoBot повертає {ok: true/false, result: data}
            if result.get('ok'):
                return result.get('result', {})
            else:
                error = result.get('error', {})
                logger.error(f"CryptoBot API error: {error}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"CryptoBot API request failed: {e}")
            return None

    def create_payment(self, amount: Decimal, currency: str,
                       network: Optional[str] = None, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Створити платіж через CryptoBot

        Args:
            amount: Сума платежу
            currency: Валюта (USDT, BTC, TON)
            network: Не використовується для CryptoBot
            **kwargs: Додаткові параметри

        Returns:
            {
                'payment_id': 'invoice_id',
                'payment_url': 'https://t.me/CryptoBot?start=...',
                'expires_at': '2024-01-01T00:00:00Z',
                'metadata': {...}
            }
        """
        try:
            # Перевіряємо валюту
            if currency not in self.supported_currencies:
                logger.error(f"CryptoBot: Unsupported currency {currency}")
                return None

            # Отримуємо payment_id для payload
            our_payment_id = kwargs.get('payment_id')

            # Параметри інвойсу
            invoice_data = {
                'asset': currency,
                'amount': str(amount),
                'description': kwargs.get('description', 'TeleBoost Deposit'),
                'hidden_message': f'Thank you for using TeleBoost!',
                'paid_btn_name': 'callback',
                'paid_btn_url': f"{config.FRONTEND_URL}/payments/success",
                'payload': our_payment_id,  # Наш ID для ідентифікації
                'expires_in': self.invoice_lifetime
            }

            # Створюємо інвойс
            result = self._make_request('POST', 'createInvoice', invoice_data)

            if not result:
                logger.error("Failed to create CryptoBot invoice")
                return None

            # Розраховуємо час експірації
            expires_at = datetime.utcnow() + timedelta(seconds=self.invoice_lifetime)

            return {
                'payment_id': str(result.get('invoice_id')),
                'payment_url': result.get('pay_url'),
                'expires_at': expires_at.isoformat() + 'Z',
                'metadata': {
                    'bot_invoice_url': result.get('bot_invoice_url'),
                    'mini_app_invoice_url': result.get('mini_app_invoice_url'),
                    'web_app_invoice_url': result.get('web_app_invoice_url'),
                    'hash': result.get('hash'),
                    'currency_type': result.get('currency_type', 'crypto'),
                    'asset': currency,
                    'amount': str(amount),
                    'status': result.get('status', 'active')
                }
            }

        except Exception as e:
            logger.error(f"Error creating CryptoBot payment: {e}")
            return None

    def check_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Перевірити статус платежу

        Args:
            payment_id: ID інвойсу в CryptoBot

        Returns:
            {
                'status': 'confirmed',
                'metadata': {...}
            }
        """
        try:
            # Отримуємо список інвойсів з фільтром по ID
            result = self._make_request('GET', 'getInvoices', {
                'invoice_ids': payment_id
            })

            if not result or not result.get('items'):
                logger.error(f"CryptoBot invoice {payment_id} not found")
                return None

            invoice = result['items'][0]

            # Мапимо статуси CryptoBot на наші
            status_map = {
                'active': PAYMENT_STATUS.WAITING,
                'paid': PAYMENT_STATUS.CONFIRMED,
                'expired': PAYMENT_STATUS.EXPIRED
            }

            cryptobot_status = invoice.get('status', 'active')
            our_status = status_map.get(cryptobot_status, PAYMENT_STATUS.WAITING)

            return {
                'status': our_status,
                'metadata': {
                    'invoice_id': invoice.get('invoice_id'),
                    'hash': invoice.get('hash'),
                    'asset': invoice.get('asset'),
                    'amount': invoice.get('amount'),
                    'paid_asset': invoice.get('paid_asset'),
                    'paid_amount': invoice.get('paid_amount'),
                    'paid_at': invoice.get('paid_at'),
                    'paid_anonymously': invoice.get('paid_anonymously', False),
                    'is_confirmed': invoice.get('is_confirmed', False)
                }
            }

        except Exception as e:
            logger.error(f"Error checking CryptoBot payment status: {e}")
            return None

    def process_webhook(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обробити webhook від CryptoBot

        Args:
            data: Дані webhook (вже перевірені)

        Returns:
            {
                'payment_id': 'external_id',
                'status': 'confirmed',
                'metadata': {...}
            }
        """
        try:
            # CryptoBot відправляє дані в форматі:
            # {
            #     "update_id": 12345,
            #     "update_type": "invoice_paid",
            #     "request_date": "2024-01-01T00:00:00Z",
            #     "payload": {...}
            # }

            update_type = data.get('update_type')
            payload = data.get('payload', {})

            if update_type == 'invoice_paid':
                return {
                    'payment_id': str(payload.get('invoice_id')),
                    'status': PAYMENT_STATUS.CONFIRMED,
                    'metadata': {
                        'update_id': data.get('update_id'),
                        'request_date': data.get('request_date'),
                        'invoice_id': payload.get('invoice_id'),
                        'hash': payload.get('hash'),
                        'asset': payload.get('asset'),
                        'amount': payload.get('amount'),
                        'paid_at': payload.get('paid_at'),
                        'paid_anonymously': payload.get('paid_anonymously', False)
                    }
                }

            elif update_type == 'invoice_expired':
                return {
                    'payment_id': str(payload.get('invoice_id')),
                    'status': PAYMENT_STATUS.EXPIRED,
                    'metadata': {
                        'update_id': data.get('update_id'),
                        'request_date': data.get('request_date'),
                        'expired_at': data.get('request_date')
                    }
                }

            else:
                logger.warning(f"Unknown CryptoBot update type: {update_type}")
                return None

        except Exception as e:
            logger.error(f"Error processing CryptoBot webhook: {e}")
            return None

    def get_balance(self) -> Optional[Dict[str, Decimal]]:
        """
        Отримати баланс CryptoBot

        Returns:
            {'USDT': Decimal('100.50'), 'BTC': Decimal('0.01')}
        """
        try:
            result = self._make_request('GET', 'getBalance')

            if not result:
                return None

            balances = {}
            for item in result:
                currency = item.get('currency_code')
                available = item.get('available', '0')
                balances[currency] = Decimal(available)

            return balances

        except Exception as e:
            logger.error(f"Error getting CryptoBot balance: {e}")
            return None

    def get_exchange_rates(self) -> Optional[Dict[str, Dict[str, Decimal]]]:
        """
        Отримати курси обміну CryptoBot

        Returns:
            {
                'USDT': {'USD': Decimal('1.00'), 'RUB': Decimal('90.50')},
                'BTC': {'USD': Decimal('45000.00'), 'RUB': Decimal('4050000')}
            }
        """
        try:
            result = self._make_request('GET', 'getExchangeRates')

            if not result:
                return None

            rates = {}
            for item in result:
                source = item.get('source')
                target = item.get('target')
                rate = item.get('rate', '1')

                if source not in rates:
                    rates[source] = {}

                rates[source][target] = Decimal(rate)

            return rates

        except Exception as e:
            logger.error(f"Error getting CryptoBot exchange rates: {e}")
            return None

    def get_currencies(self) -> Optional[List[Dict[str, Any]]]:
        """
        Отримати список підтримуваних валют

        Returns:
            [
                {
                    'is_blockchain': True,
                    'is_stablecoin': True,
                    'is_fiat': False,
                    'name': 'Tether',
                    'code': 'USDT',
                    'decimals': 6
                }
            ]
        """
        try:
            result = self._make_request('GET', 'getCurrencies')
            return result

        except Exception as e:
            logger.error(f"Error getting CryptoBot currencies: {e}")
            return None

    def delete_invoice(self, invoice_id: str) -> bool:
        """
        Видалити (скасувати) інвойс

        Args:
            invoice_id: ID інвойсу

        Returns:
            True якщо успішно
        """
        try:
            result = self._make_request('POST', 'deleteInvoice', {
                'invoice_id': invoice_id
            })

            return result is not None

        except Exception as e:
            logger.error(f"Error deleting CryptoBot invoice: {e}")
            return False

    def create_check(self, asset: str, amount: Decimal) -> Optional[Dict[str, Any]]:
        """
        Створити чек (для виведення коштів)

        Args:
            asset: Валюта
            amount: Сума

        Returns:
            Інформація про чек
        """
        try:
            result = self._make_request('POST', 'createCheck', {
                'asset': asset,
                'amount': str(amount)
            })

            if not result:
                return None

            return {
                'check_id': result.get('check_id'),
                'hash': result.get('hash'),
                'bot_check_url': result.get('bot_check_url'),
                'asset': asset,
                'amount': str(amount),
                'created_at': datetime.utcnow().isoformat() + 'Z'
            }

        except Exception as e:
            logger.error(f"Error creating CryptoBot check: {e}")
            return None