# backend/payments/validators.py
"""
TeleBoost Payment Validators
Валідація платіжних даних
"""
import re
import logging
from typing import Tuple, List, Optional, Dict, Any
from decimal import Decimal, InvalidOperation

from backend.utils.constants import (
    LIMITS, CRYPTO_CURRENCIES, PAYMENT_PROVIDERS,
    PAYMENT_STATUS
)

logger = logging.getLogger(__name__)


def validate_payment_amount(amount: Any, currency: str = 'USD',
                            operation: str = 'deposit') -> Tuple[bool, Optional[str]]:
    """
    Валідація суми платежу

    Args:
        amount: Сума
        currency: Валюта
        operation: Тип операції (deposit/withdraw)

    Returns:
        (is_valid, error_message)
    """
    try:
        # Конвертуємо в Decimal
        decimal_amount = Decimal(str(amount))

        # Перевіряємо що позитивне
        if decimal_amount <= 0:
            return False, "Amount must be positive"

        # Перевіряємо ліміти
        if operation == 'deposit':
            min_limit = Decimal(str(LIMITS['MIN_DEPOSIT']))
            max_limit = Decimal(str(LIMITS['MAX_DEPOSIT']))
        elif operation == 'withdraw':
            min_limit = Decimal(str(LIMITS['MIN_WITHDRAW']))
            max_limit = Decimal(str(LIMITS['MAX_WITHDRAW']))
        else:
            return False, "Invalid operation type"

        # Конвертуємо ліміти для криптовалют
        if currency in CRYPTO_CURRENCIES:
            # Для криптовалют свої ліміти
            if currency == 'BTC':
                min_limit = Decimal('0.0001')
                max_limit = Decimal('10')
            elif currency == 'TON':
                min_limit = Decimal('5')
                max_limit = Decimal('100000')
            elif currency == 'USDT':
                min_limit = Decimal('10')
                max_limit = Decimal('100000')

        # Перевіряємо ліміти
        if decimal_amount < min_limit:
            return False, f"Minimum amount is {min_limit} {currency}"

        if decimal_amount > max_limit:
            return False, f"Maximum amount is {max_limit} {currency}"

        # Перевіряємо кількість десяткових знаків
        decimals = CRYPTO_CURRENCIES.get(currency, {}).get('decimals', 2)
        decimal_places = abs(decimal_amount.as_tuple().exponent)

        if decimal_places > decimals:
            return False, f"Too many decimal places for {currency} (max: {decimals})"

        return True, None

    except (InvalidOperation, ValueError):
        return False, "Invalid amount format"
    except Exception as e:
        logger.error(f"Error validating amount: {e}")
        return False, "Amount validation failed"


def validate_crypto_address(address: str, currency: str) -> Tuple[bool, Optional[str]]:
    """
    Валідація криптовалютної адреси

    Args:
        address: Адреса
        currency: Валюта

    Returns:
        (is_valid, error_message)
    """
    if not address:
        return False, "Address is required"

    # Базові перевірки для різних валют
    validators = {
        'BTC': {
            'pattern': r'^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}$',
            'min_length': 26,
            'max_length': 42
        },
        'USDT': {
            # TRC20 addresses
            'pattern': r'^T[a-zA-Z0-9]{33}$',
            'min_length': 34,
            'max_length': 34
        },
        'TON': {
            'pattern': r'^[a-zA-Z0-9_-]{48}$',
            'min_length': 48,
            'max_length': 48
        }
    }

    validator = validators.get(currency)
    if not validator:
        # Якщо немає специфічної валідації - базова перевірка
        if len(address) < 10 or len(address) > 100:
            return False, "Invalid address length"
        return True, None

    # Перевірка довжини
    if len(address) < validator['min_length'] or len(address) > validator['max_length']:
        return False, f"Invalid {currency} address length"

    # Перевірка паттерну
    if not re.match(validator['pattern'], address):
        return False, f"Invalid {currency} address format"

    return True, None


def validate_payment_currency(currency: str, provider: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Валідація валюти платежу

    Args:
        currency: Валюта
        provider: Провайдер платежів

    Returns:
        (is_valid, error_message)
    """
    if not currency:
        return False, "Currency is required"

    currency = currency.upper()

    # Перевіряємо чи підтримується валюта
    supported_currencies = {
        PAYMENT_PROVIDERS.CRYPTOBOT: ['USDT', 'BTC', 'TON'],
        PAYMENT_PROVIDERS.NOWPAYMENTS: ['USDT', 'BTC', 'ETH', 'BNB', 'TRX']
    }

    # Якщо вказаний провайдер - перевіряємо його список
    if provider:
        if provider not in supported_currencies:
            return False, f"Unknown provider: {provider}"

        if currency not in supported_currencies[provider]:
            return False, f"{currency} is not supported by {provider}"

    else:
        # Перевіряємо чи валюта підтримується хоча б одним провайдером
        all_currencies = set()
        for currencies in supported_currencies.values():
            all_currencies.update(currencies)

        if currency not in all_currencies:
            return False, f"Unsupported currency: {currency}"

    return True, None


def validate_payment_network(network: str, currency: str = 'USDT') -> Tuple[bool, Optional[str]]:
    """
    Валідація мережі для криптовалюти

    Args:
        network: Мережа
        currency: Валюта

    Returns:
        (is_valid, error_message)
    """
    # Мережі доступні тільки для USDT в NOWPayments
    if currency != 'USDT':
        if network:
            return False, f"Network selection not available for {currency}"
        return True, None

    valid_networks = ['TRC20', 'BEP20', 'SOL', 'TON']

    if network and network not in valid_networks:
        return False, f"Invalid network. Available: {', '.join(valid_networks)}"

    return True, None


def validate_payment_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Повна валідація даних платежу

    Args:
        data: Дані платежу

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Перевірка обов'язкових полів
    required_fields = ['amount', 'currency']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"{field} is required")

    if errors:
        return False, errors

    # Валідація суми
    is_valid, error = validate_payment_amount(
        data['amount'],
        data.get('currency', 'USD'),
        'deposit'
    )
    if not is_valid:
        errors.append(error)

    # Валідація валюти
    is_valid, error = validate_payment_currency(
        data['currency'],
        data.get('provider')
    )
    if not is_valid:
        errors.append(error)

    # Валідація мережі якщо вказана
    if 'network' in data:
        is_valid, error = validate_payment_network(
            data['network'],
            data.get('currency', 'USDT')
        )
        if not is_valid:
            errors.append(error)

    # Валідація провайдера
    if 'provider' in data:
        valid_providers = [PAYMENT_PROVIDERS.CRYPTOBOT, PAYMENT_PROVIDERS.NOWPAYMENTS]
        if data['provider'] not in valid_providers:
            errors.append(f"Invalid provider. Available: {', '.join(valid_providers)}")

    return len(errors) == 0, errors


def validate_payment_status(status: str) -> bool:
    """
    Валідація статусу платежу

    Args:
        status: Статус

    Returns:
        True якщо валідний
    """
    return status in PAYMENT_STATUS.all()


def validate_webhook_signature(provider: str, signature: str, data: Any) -> bool:
    """
    Валідація підпису webhook

    Args:
        provider: Провайдер
        signature: Підпис
        data: Дані webhook

    Returns:
        True якщо підпис валідний
    """
    # Це буде реалізовано в utils/security.py
    # Кожен провайдер має свій метод перевірки підпису
    return True  # TODO: Implement actual signature validation


def validate_exchange_rate(rate: Decimal, from_currency: str, to_currency: str) -> bool:
    """
    Валідація курсу обміну

    Args:
        rate: Курс
        from_currency: З валюти
        to_currency: В валюту

    Returns:
        True якщо курс в розумних межах
    """
    try:
        # Перевіряємо що курс позитивний
        if rate <= 0:
            return False

        # Перевіряємо розумні межі для популярних пар
        if from_currency == 'USD' and to_currency == 'USDT':
            # USDT зазвичай близько 1 USD
            if rate < Decimal('0.95') or rate > Decimal('1.05'):
                logger.warning(f"Suspicious USD/USDT rate: {rate}")
                return False

        # Можна додати більше перевірок для інших пар

        return True

    except Exception as e:
        logger.error(f"Error validating exchange rate: {e}")
        return False