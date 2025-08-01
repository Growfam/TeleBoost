# backend/utils/validators.py
"""
TeleBoost Validators
Функції для валідації даних
"""
import re
from typing import Dict, List, Optional, Union, Any, Tuple
from urllib.parse import urlparse

from backend.utils.constants import (
    LIMITS, TELEGRAM_LIMITS, REGEX_PATTERNS,
    SERVICE_TYPE, ORDER_STATUS, PAYMENT_STATUS
)


def validate_telegram_id(telegram_id: Union[str, int]) -> bool:
    """
    Валідація Telegram ID

    Args:
        telegram_id: ID користувача

    Returns:
        True якщо валідний
    """
    try:
        tid = int(telegram_id)
        # Telegram ID має бути позитивним числом
        return tid > 0 and tid < 10 ** 15
    except (ValueError, TypeError):
        return False


def validate_telegram_username(username: str) -> bool:
    """
    Валідація Telegram username

    Args:
        username: Username

    Returns:
        True якщо валідний
    """
    if not username:
        return False

    # Видаляємо @ якщо є
    username = username.lstrip('@')

    # Перевіряємо довжину
    if len(username) < TELEGRAM_LIMITS['USERNAME_MIN_LENGTH'] or \
            len(username) > TELEGRAM_LIMITS['USERNAME_MAX_LENGTH']:
        return False

    # Перевіряємо паттерн
    return bool(re.match(REGEX_PATTERNS['TELEGRAM_USERNAME'], username))


def validate_url(url: str, allowed_domains: Optional[List[str]] = None) -> bool:
    """
    Валідація URL

    Args:
        url: URL для перевірки
        allowed_domains: Список дозволених доменів

    Returns:
        True якщо валідний
    """
    if not url:
        return False

    # Базова перевірка паттерном
    if not re.match(REGEX_PATTERNS['URL'], url):
        return False

    # Перевірка домену якщо потрібно
    if allowed_domains:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Видаляємо www.
            domain = domain.replace('www.', '')

            return any(domain.endswith(allowed) for allowed in allowed_domains)
        except:
            return False

    return True


def validate_service_url(url: str, service_name: str) -> bool:
    """
    Валідація URL для конкретного сервісу

    Args:
        url: URL
        service_name: Назва сервісу (instagram, telegram, youtube, tiktok)

    Returns:
        True якщо валідний для сервісу
    """
    service_patterns = {
        'instagram': REGEX_PATTERNS['INSTAGRAM_URL'],
        'telegram': REGEX_PATTERNS['TELEGRAM_URL'],
        'youtube': REGEX_PATTERNS['YOUTUBE_URL'],
        'tiktok': REGEX_PATTERNS['TIKTOK_URL'],
    }

    pattern = service_patterns.get(service_name.lower())
    if not pattern:
        # Якщо немає специфічного паттерну, використовуємо загальний
        return validate_url(url)

    return bool(re.match(pattern, url))


def validate_amount(amount: Union[int, float],
                    min_amount: Optional[float] = None,
                    max_amount: Optional[float] = None) -> bool:
    """
    Валідація суми

    Args:
        amount: Сума
        min_amount: Мінімальна сума
        max_amount: Максимальна сума

    Returns:
        True якщо валідна
    """
    try:
        amount = float(amount)

        if amount <= 0:
            return False

        if min_amount is not None and amount < min_amount:
            return False

        if max_amount is not None and amount > max_amount:
            return False

        return True
    except (ValueError, TypeError):
        return False


def validate_payment_amount(amount: Union[int, float],
                            operation: str = 'deposit') -> Tuple[bool, Optional[str]]:
    """
    Валідація суми платежу з урахуванням лімітів

    Args:
        amount: Сума
        operation: Тип операції (deposit, withdraw)

    Returns:
        (is_valid, error_message)
    """
    if operation == 'deposit':
        min_limit = LIMITS['MIN_DEPOSIT']
        max_limit = LIMITS['MAX_DEPOSIT']
    elif operation == 'withdraw':
        min_limit = LIMITS['MIN_WITHDRAW']
        max_limit = LIMITS['MAX_WITHDRAW']
    else:
        return False, 'Invalid operation type'

    if not validate_amount(amount, min_limit, max_limit):
        if amount < min_limit:
            return False, f'Мінімальна сума: {min_limit}'
        elif amount > max_limit:
            return False, f'Максимальна сума: {max_limit}'
        else:
            return False, 'Некоректна сума'

    return True, None


def validate_order_amount(amount: Union[int, float]) -> Tuple[bool, Optional[str]]:
    """
    Валідація суми замовлення

    Args:
        amount: Сума

    Returns:
        (is_valid, error_message)
    """
    min_limit = LIMITS['MIN_ORDER']
    max_limit = LIMITS['MAX_ORDER']

    if not validate_amount(amount, min_limit, max_limit):
        if amount < min_limit:
            return False, f'Мінімальна сума замовлення: {min_limit}'
        elif amount > max_limit:
            return False, f'Максимальна сума замовлення: {max_limit}'
        else:
            return False, 'Некоректна сума'

    return True, None


def validate_quantity(quantity: Union[int, str],
                      min_quantity: int = 1,
                      max_quantity: Optional[int] = None) -> bool:
    """
    Валідація кількості

    Args:
        quantity: Кількість
        min_quantity: Мінімальна кількість
        max_quantity: Максимальна кількість

    Returns:
        True якщо валідна
    """
    try:
        qty = int(quantity)

        if qty < min_quantity:
            return False

        if max_quantity is not None and qty > max_quantity:
            return False

        return True
    except (ValueError, TypeError):
        return False


def validate_service_params(params: Dict[str, Any], service_type: str) -> Tuple[bool, Optional[str]]:
    """
    Валідація параметрів сервісу

    Args:
        params: Параметри сервісу
        service_type: Тип сервісу

    Returns:
        (is_valid, error_message)
    """
    # Обов'язкові поля для всіх типів
    if 'link' not in params or not params['link']:
        return False, 'Посилання обов\'язкове'

    # Валідація в залежності від типу
    if service_type == SERVICE_TYPE.DEFAULT:
        if 'quantity' not in params:
            return False, 'Кількість обов\'язкова'
        if not validate_quantity(params['quantity']):
            return False, 'Некоректна кількість'

    elif service_type == SERVICE_TYPE.CUSTOM_COMMENTS:
        if 'comments' not in params or not params['comments']:
            return False, 'Коментарі обов\'язкові'
        comments = params['comments'].strip().split('\n')
        if len(comments) < 1:
            return False, 'Потрібен хоча б один коментар'

    elif service_type == SERVICE_TYPE.MENTIONS:
        if 'usernames' not in params or not params['usernames']:
            return False, 'Список користувачів обов\'язковий'

    elif service_type == SERVICE_TYPE.POLL:
        if 'answer_number' not in params:
            return False, 'Номер відповіді обов\'язковий'
        try:
            answer = int(params['answer_number'])
            if answer < 1 or answer > 10:
                return False, 'Номер відповіді має бути від 1 до 10'
        except:
            return False, 'Некоректний номер відповіді'

    elif service_type == SERVICE_TYPE.SUBSCRIPTIONS:
        required = ['username', 'min', 'max', 'posts']
        for field in required:
            if field not in params:
                return False, f'Поле {field} обов\'язкове'

    return True, None


def validate_order_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Повна валідація даних замовлення

    Args:
        data: Дані замовлення

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Перевірка обов'язкових полів
    required_fields = ['service_id', 'link']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f'Поле {field} обов\'язкове')

    # Валідація service_id
    if 'service_id' in data:
        try:
            service_id = int(data['service_id'])
            if service_id <= 0:
                errors.append('Некоректний ID сервісу')
        except:
            errors.append('ID сервісу має бути числом')

    # Валідація посилання
    if 'link' in data and not validate_url(data['link']):
        errors.append('Некоректне посилання')

    # Валідація кількості якщо є
    if 'quantity' in data:
        if not validate_quantity(data['quantity']):
            errors.append('Некоректна кількість')

    return len(errors) == 0, errors


def validate_email(email: str) -> bool:
    """
    Валідація email

    Args:
        email: Email адреса

    Returns:
        True якщо валідний
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """
    Валідація телефону (український формат)

    Args:
        phone: Номер телефону

    Returns:
        True якщо валідний
    """
    # Видаляємо всі символи крім цифр
    phone_digits = re.sub(r'\D', '', phone)

    # Перевіряємо довжину та префікс
    if len(phone_digits) == 12 and phone_digits.startswith('380'):
        return True
    elif len(phone_digits) == 10 and phone_digits.startswith('0'):
        return True

    return False


def validate_status(status: str, status_type: str = 'order') -> bool:
    """
    Валідація статусу

    Args:
        status: Статус
        status_type: Тип статусу (order, payment)

    Returns:
        True якщо валідний
    """
    if status_type == 'order':
        return status in ORDER_STATUS.all()
    elif status_type == 'payment':
        return status in PAYMENT_STATUS.all()

    return False


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    Очищення та санітизація тексту

    Args:
        text: Текст
        max_length: Максимальна довжина

    Returns:
        Очищений текст
    """
    if not text:
        return ''

    # Видаляємо керуючі символи
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)

    # Видаляємо зайві пробіли
    text = ' '.join(text.split())

    # Обрізаємо якщо потрібно
    if max_length and len(text) > max_length:
        text = text[:max_length]

    return text.strip()


def is_valid_uuid(uuid_string: str) -> bool:
    """
    Перевірка чи є строка валідним UUID

    Args:
        uuid_string: Строка для перевірки

    Returns:
        True якщо валідний UUID
    """
    uuid_pattern = re.compile(
        r'^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(uuid_string))


def validate_crypto_address(address: str, network: str) -> bool:
    """
    Валідація криптовалютної адреси

    Args:
        address: Адреса гаманця
        network: Мережа (TRC20, BEP20, ERC20, etc.)

    Returns:
        True якщо адреса валідна для вказаної мережі
    """
    if not address or not network:
        return False

    # Видаляємо пробіли
    address = address.strip()

    # Валідація по мережах
    if network.upper() == 'TRC20':
        # TRON адреси починаються з T і мають 34 символи
        return bool(re.match(r'^T[a-zA-Z0-9]{33}$', address))

    elif network.upper() in ['BEP20', 'ERC20']:
        # Ethereum/BSC адреси починаються з 0x і мають 42 символи
        return bool(re.match(r'^0x[a-fA-F0-9]{40}$', address))

    elif network.upper() == 'SOL':
        # Solana адреси - base58, довжина 32-44 символи
        return bool(re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address))

    elif network.upper() == 'TON':
        # TON адреси різних форматів
        # Raw: 0:... або -1:... (workchain:hash)
        # User-friendly: 48 символів base64url
        if ':' in address:
            return bool(re.match(r'^-?[0-9]:[a-fA-F0-9]{64}$', address))
        else:
            return bool(re.match(r'^[a-zA-Z0-9_-]{48}$', address))

    elif network.upper() == 'BITCOIN':
        # Bitcoin адреси різних типів
        # Legacy (1...), SegWit (3...), Native SegWit (bc1...)
        return bool(re.match(REGEX_PATTERNS['BTC_ADDRESS'], address))

    else:
        # Для невідомих мереж - базова перевірка
        # Мінімум 20 символів, тільки алфавіт та цифри
        return bool(re.match(r'^[a-zA-Z0-9]{20,}$', address))


def validate_payment_currency(currency: str, provider: str) -> bool:
    """
    Валідація валюти для платіжного провайдера

    Args:
        currency: Код валюти (USDT, BTC, etc.)
        provider: Платіжний провайдер (cryptobot, nowpayments)

    Returns:
        True якщо валюта підтримується провайдером
    """
    supported_currencies = {
        'cryptobot': ['USDT', 'BTC', 'TON', 'ETH', 'BNB'],
        'nowpayments': ['USDT', 'BTC', 'ETH', 'BNB', 'TRX', 'BUSD']
    }

    provider_currencies = supported_currencies.get(provider.lower(), [])
    return currency.upper() in provider_currencies


def validate_withdrawal_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Повна валідація даних для виведення коштів

    Args:
        data: Дані виведення

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Перевірка обов'язкових полів
    required_fields = ['amount', 'address', 'network']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f'Поле {field} обов\'язкове')

    # Валідація суми
    if 'amount' in data:
        try:
            amount = float(data['amount'])
            if amount <= 0:
                errors.append('Сума має бути більше 0')
            elif amount < LIMITS['MIN_WITHDRAW']:
                errors.append(f'Мінімальна сума виведення: ${LIMITS["MIN_WITHDRAW"]}')
            elif amount > LIMITS['MAX_WITHDRAW']:
                errors.append(f'Максимальна сума виведення: ${LIMITS["MAX_WITHDRAW"]}')
        except (ValueError, TypeError):
            errors.append('Некоректна сума')

    # Валідація адреси
    if 'address' in data and 'network' in data:
        if not validate_crypto_address(data['address'], data['network']):
            errors.append(f'Некоректна адреса для мережі {data["network"]}')

    return len(errors) == 0, errors


def validate_network_for_currency(currency: str, network: str) -> bool:
    """
    Перевірка чи підтримується мережа для валюти

    Args:
        currency: Валюта (USDT, BTC, etc.)
        network: Мережа (TRC20, BEP20, etc.)

    Returns:
        True якщо комбінація валідна
    """
    valid_combinations = {
        'USDT': ['TRC20', 'BEP20', 'ERC20', 'SOL', 'TON'],
        'BTC': ['Bitcoin'],
        'ETH': ['Ethereum', 'ERC20'],
        'BNB': ['BEP20', 'BSC'],
        'TRX': ['Tron', 'TRC20'],
        'TON': ['TON'],
        'BUSD': ['BEP20', 'ERC20']
    }

    currency_networks = valid_combinations.get(currency.upper(), [])
    return network.upper() in [n.upper() for n in currency_networks]


def validate_payment_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Валідація даних платежу

    Args:
        data: Дані платежу

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Обов'язкові поля
    required_fields = ['amount', 'currency', 'provider']
    for field in required_fields:
        if field not in data:
            errors.append(f'{field} is required')

    # Валідація суми
    if 'amount' in data:
        is_valid, error = validate_payment_amount(data['amount'], 'deposit')
        if not is_valid:
            errors.append(error)

    # Валідація валюти
    if 'currency' in data and 'provider' in data:
        if not validate_payment_currency(data['currency'], data['provider']):
            errors.append(f'Currency {data["currency"]} not supported by {data["provider"]}')

    # Валідація мережі якщо є
    if 'network' in data and 'currency' in data:
        if not validate_network_for_currency(data['currency'], data['network']):
            errors.append(f'Network {data["network"]} not supported for {data["currency"]}')

    return len(errors) == 0, errors