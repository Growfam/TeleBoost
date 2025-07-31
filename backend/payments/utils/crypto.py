# backend/payments/utils/crypto.py
"""
TeleBoost Crypto Utilities
Утиліти для роботи з криптовалютами
"""
import logging
import requests
from typing import Dict, Optional, Tuple, List, Any
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from datetime import datetime, timedelta

from backend.utils.redis_client import cache_get, cache_set
from backend.utils.constants import CRYPTO_CURRENCIES

logger = logging.getLogger(__name__)


class CryptoUtils:
    """Утиліти для роботи з криптовалютами"""

    # API endpoints для курсів валют
    RATE_APIS = {
        'coingecko': 'https://api.coingecko.com/api/v3/simple/price',
        'binance': 'https://api.binance.com/api/v3/ticker/price',
        'coinbase': 'https://api.coinbase.com/v2/exchange-rates',
    }

    # Мапінг ID валют для різних API
    CURRENCY_IDS = {
        'BTC': {
            'coingecko': 'bitcoin',
            'binance': 'BTCUSDT',
            'symbol': 'BTC'
        },
        'ETH': {
            'coingecko': 'ethereum',
            'binance': 'ETHUSDT',
            'symbol': 'ETH'
        },
        'USDT': {
            'coingecko': 'tether',
            'binance': 'USDTUSDT',
            'symbol': 'USDT'
        },
        'TON': {
            'coingecko': 'the-open-network',
            'binance': 'TONUSDT',
            'symbol': 'TON'
        },
        'BNB': {
            'coingecko': 'binancecoin',
            'binance': 'BNBUSDT',
            'symbol': 'BNB'
        },
        'TRX': {
            'coingecko': 'tron',
            'binance': 'TRXUSDT',
            'symbol': 'TRX'
        }
    }

    @classmethod
    def get_exchange_rate(cls, from_currency: str, to_currency: str,
                          use_cache: bool = True) -> Optional[Decimal]:
        """
        Отримати курс обміну між валютами

        Args:
            from_currency: З валюти
            to_currency: В валюту
            use_cache: Використовувати кеш

        Returns:
            Курс обміну або None
        """
        try:
            # Нормалізуємо валюти
            from_currency = from_currency.upper()
            to_currency = to_currency.upper()

            # Якщо однакові валюти
            if from_currency == to_currency:
                return Decimal('1')

            # Перевіряємо кеш
            if use_cache:
                cache_key = f"rate:{from_currency}:{to_currency}"
                cached_rate = cache_get(cache_key, data_type='float')
                if cached_rate:
                    return Decimal(str(cached_rate))

            # Отримуємо курс з API
            rate = cls._fetch_rate_from_apis(from_currency, to_currency)

            if rate:
                # Кешуємо на 5 хвилин
                cache_key = f"rate:{from_currency}:{to_currency}"
                cache_set(cache_key, float(rate), ttl=300)

            return rate

        except Exception as e:
            logger.error(f"Error getting exchange rate {from_currency}/{to_currency}: {e}")
            return None

    @classmethod
    def _fetch_rate_from_apis(cls, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """
        Отримати курс з різних API

        Пробуємо декілька API для надійності
        """
        # Спробуємо CoinGecko
        rate = cls._fetch_from_coingecko(from_currency, to_currency)
        if rate:
            return rate

        # Спробуємо Binance
        rate = cls._fetch_from_binance(from_currency, to_currency)
        if rate:
            return rate

        # Якщо нічого не вийшло - використовуємо фіксовані курси
        return cls._get_fallback_rate(from_currency, to_currency)

    @classmethod
    def _fetch_from_coingecko(cls, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """Отримати курс з CoinGecko API"""
        try:
            # Отримуємо ID валют
            from_id = cls.CURRENCY_IDS.get(from_currency, {}).get('coingecko')

            if not from_id:
                return None

            # Визначаємо vs_currency
            vs_currency = 'usd'
            if to_currency in ['USD', 'USDT']:
                vs_currency = 'usd'
            elif to_currency == 'EUR':
                vs_currency = 'eur'
            else:
                # Для крипто-крипто пар отримуємо через USD
                return cls._get_cross_rate_via_usd(from_currency, to_currency)

            # Запит до API
            params = {
                'ids': from_id,
                'vs_currencies': vs_currency
            }

            response = requests.get(
                cls.RATE_APIS['coingecko'],
                params=params,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                rate = data.get(from_id, {}).get(vs_currency)

                if rate:
                    # Для USDT коригуємо на 1%
                    if to_currency == 'USDT':
                        rate = rate * 1.01

                    return Decimal(str(rate))

        except Exception as e:
            logger.debug(f"CoinGecko API error: {e}")

        return None

    @classmethod
    def _fetch_from_binance(cls, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """Отримати курс з Binance API"""
        try:
            # Binance працює з парами до USDT
            if to_currency not in ['USD', 'USDT']:
                return cls._get_cross_rate_via_usd(from_currency, to_currency)

            symbol = cls.CURRENCY_IDS.get(from_currency, {}).get('binance')
            if not symbol:
                return None

            # Запит до API
            params = {'symbol': symbol}
            response = requests.get(
                cls.RATE_APIS['binance'],
                params=params,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                price = data.get('price')

                if price:
                    return Decimal(str(price))

        except Exception as e:
            logger.debug(f"Binance API error: {e}")

        return None

    @classmethod
    def _get_cross_rate_via_usd(cls, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """
        Отримати крос-курс через USD

        Наприклад: BTC/TON = BTC/USD * USD/TON
        """
        try:
            # Отримуємо курси до USD
            from_to_usd = cls._fetch_from_coingecko(from_currency, 'USD')
            to_to_usd = cls._fetch_from_coingecko(to_currency, 'USD')

            if from_to_usd and to_to_usd:
                # Розраховуємо крос-курс
                cross_rate = from_to_usd / to_to_usd
                return cross_rate

        except Exception as e:
            logger.debug(f"Cross rate calculation error: {e}")

        return None

    @classmethod
    def _get_fallback_rate(cls, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """Фіксовані курси як fallback"""
        fallback_rates = {
            # USD to crypto
            ('USD', 'USDT'): Decimal('1.01'),
            ('USD', 'BTC'): Decimal('0.000023'),  # ~$43,000 per BTC
            ('USD', 'ETH'): Decimal('0.00031'),  # ~$3,200 per ETH
            ('USD', 'TON'): Decimal('0.17'),  # ~$6 per TON

            # USDT pairs
            ('USDT', 'USD'): Decimal('0.99'),
            ('USDT', 'BTC'): Decimal('0.0000228'),
            ('USDT', 'ETH'): Decimal('0.000307'),
            ('USDT', 'TON'): Decimal('0.168'),

            # Reverse pairs
            ('BTC', 'USD'): Decimal('43478'),
            ('BTC', 'USDT'): Decimal('43913'),
            ('ETH', 'USD'): Decimal('3225'),
            ('ETH', 'USDT'): Decimal('3257'),
            ('TON', 'USD'): Decimal('5.88'),
            ('TON', 'USDT'): Decimal('5.94'),
        }

        return fallback_rates.get((from_currency, to_currency))

    @classmethod
    def convert_amount(cls, amount: Decimal, from_currency: str,
                       to_currency: str, use_cache: bool = True) -> Optional[Decimal]:
        """
        Конвертувати суму між валютами

        Args:
            amount: Сума
            from_currency: З валюти
            to_currency: В валюту
            use_cache: Використовувати кеш

        Returns:
            Конвертована сума або None
        """
        try:
            rate = cls.get_exchange_rate(from_currency, to_currency, use_cache)

            if not rate:
                logger.error(f"Cannot get exchange rate {from_currency}/{to_currency}")
                return None

            # Конвертуємо
            result = amount * rate

            # Округлюємо відповідно до decimals валюти
            decimals = CRYPTO_CURRENCIES.get(to_currency, {}).get('decimals', 2)

            # Створюємо квантизатор
            quantizer = Decimal(10) ** -decimals

            # Округлюємо вниз для криптовалют (щоб не перевищити баланс)
            result = result.quantize(quantizer, rounding=ROUND_DOWN)

            return result

        except Exception as e:
            logger.error(f"Error converting amount: {e}")
            return None

    @classmethod
    def format_crypto_amount(cls, amount: Decimal, currency: str,
                             show_symbol: bool = True) -> str:
        """
        Форматувати суму криптовалюти для відображення

        Args:
            amount: Сума
            currency: Валюта
            show_symbol: Показувати символ валюти

        Returns:
            Відформатована строка
        """
        try:
            # Отримуємо кількість десяткових знаків
            decimals = CRYPTO_CURRENCIES.get(currency, {}).get('decimals', 8)

            # Форматуємо число
            format_str = f"{{:.{decimals}f}}"
            formatted = format_str.format(amount).rstrip('0').rstrip('.')

            # Додаємо символ якщо потрібно
            if show_symbol:
                return f"{formatted} {currency}"
            else:
                return formatted

        except Exception:
            return str(amount)

    @classmethod
    def validate_crypto_amount(cls, amount: Decimal, currency: str) -> Tuple[bool, Optional[str]]:
        """
        Валідація суми криптовалюти

        Args:
            amount: Сума
            currency: Валюта

        Returns:
            (is_valid, error_message)
        """
        try:
            # Перевіряємо що валюта підтримується
            if currency not in CRYPTO_CURRENCIES:
                return False, f"Unsupported currency: {currency}"

            # Перевіряємо що сума позитивна
            if amount <= 0:
                return False, "Amount must be positive"

            # Перевіряємо кількість десяткових знаків
            decimals = CRYPTO_CURRENCIES[currency]['decimals']

            # Отримуємо кількість знаків після коми
            sign, digits, exponent = amount.as_tuple()
            decimal_places = -exponent if exponent < 0 else 0

            if decimal_places > decimals:
                return False, f"Too many decimal places for {currency} (max: {decimals})"

            # Перевіряємо мінімальну суму (dust limit)
            dust_limits = {
                'BTC': Decimal('0.00000546'),  # Bitcoin dust limit
                'ETH': Decimal('0.000001'),
                'USDT': Decimal('0.01'),
                'TON': Decimal('0.001'),
                'BNB': Decimal('0.00001'),
                'TRX': Decimal('0.001'),
            }

            dust_limit = dust_limits.get(currency, Decimal('0'))
            if amount < dust_limit:
                return False, f"Amount below dust limit ({dust_limit} {currency})"

            return True, None

        except Exception as e:
            logger.error(f"Error validating crypto amount: {e}")
            return False, "Validation error"

    @classmethod
    def get_network_fee(cls, currency: str, network: Optional[str] = None) -> Optional[Decimal]:
        """
        Отримати приблизну комісію мережі

        Args:
            currency: Валюта
            network: Мережа (для USDT)

        Returns:
            Комісія або None
        """
        # Приблизні комісії мереж
        network_fees = {
            'BTC': Decimal('0.0001'),  # ~$4-5
            'ETH': Decimal('0.005'),  # ~$15-20
            'USDT': {
                'TRC20': Decimal('1'),  # ~$1
                'BEP20': Decimal('0.5'),  # ~$0.5
                'ERC20': Decimal('15'),  # ~$15
                'SOL': Decimal('0.1'),  # ~$0.1
                'TON': Decimal('0.05'),  # ~$0.05
            },
            'TON': Decimal('0.05'),  # ~$0.05
            'BNB': Decimal('0.0005'),  # ~$0.15
            'TRX': Decimal('1'),  # ~$0.1
        }

        if currency == 'USDT' and network:
            fees = network_fees.get('USDT', {})
            return fees.get(network, Decimal('5'))  # Default $5
        else:
            return network_fees.get(currency, Decimal('5'))

    @classmethod
    def get_confirmation_time(cls, currency: str, network: Optional[str] = None) -> int:
        """
        Отримати приблизний час підтвердження в хвилинах

        Args:
            currency: Валюта
            network: Мережа

        Returns:
            Час в хвилинах
        """
        confirmation_times = {
            'BTC': 10,  # 1 блок ~10 хвилин
            'ETH': 5,  # ~5 хвилин для 20 підтверджень
            'USDT': {
                'TRC20': 3,
                'BEP20': 1,
                'ERC20': 5,
                'SOL': 1,
                'TON': 1,
            },
            'TON': 1,
            'BNB': 1,
            'TRX': 3,
        }

        if currency == 'USDT' and network:
            times = confirmation_times.get('USDT', {})
            return times.get(network, 10)
        else:
            return confirmation_times.get(currency, 30)

    @classmethod
    def get_blockchain_explorer_url(cls, currency: str, tx_hash: str,
                                    network: Optional[str] = None) -> Optional[str]:
        """
        Отримати URL для перегляду транзакції в блокчейн експлорері

        Args:
            currency: Валюта
            tx_hash: Хеш транзакції
            network: Мережа

        Returns:
            URL або None
        """
        explorers = {
            'BTC': f"https://blockchain.info/tx/{tx_hash}",
            'ETH': f"https://etherscan.io/tx/{tx_hash}",
            'USDT': {
                'TRC20': f"https://tronscan.org/#/transaction/{tx_hash}",
                'BEP20': f"https://bscscan.com/tx/{tx_hash}",
                'ERC20': f"https://etherscan.io/tx/{tx_hash}",
                'SOL': f"https://solscan.io/tx/{tx_hash}",
                'TON': f"https://tonscan.org/tx/{tx_hash}",
            },
            'TON': f"https://tonscan.org/tx/{tx_hash}",
            'BNB': f"https://bscscan.com/tx/{tx_hash}",
            'TRX': f"https://tronscan.org/#/transaction/{tx_hash}",
        }

        if currency == 'USDT' and network:
            urls = explorers.get('USDT', {})
            return urls.get(network)
        else:
            return explorers.get(currency)