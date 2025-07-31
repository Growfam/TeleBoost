# backend/utils/formatters.py
"""
TeleBoost Formatters
Функції для форматування даних
"""
import re
from datetime import datetime, timezone
from typing import Optional, Union
import hashlib

from backend.utils.constants import TELEGRAM_LIMITS


def format_price(amount: Union[int, float], currency: str = 'UAH', decimals: int = 2) -> str:
    """
    Форматування ціни

    Args:
        amount: Сума
        currency: Валюта (UAH, USD, USDT)
        decimals: Кількість знаків після коми

    Returns:
        Відформатована ціна
    """
    if currency in ['USDT', 'USD']:
        # Для криптовалют та доларів
        return f"{amount:,.{decimals}f} {currency}"
    elif currency == 'UAH':
        # Для гривні
        return f"{amount:,.{decimals}f} ₴"
    else:
        return f"{amount:,.{decimals}f} {currency}"


def format_number(number: Union[int, float], decimals: int = 0) -> str:
    """Форматування числа з роздільниками тисяч"""
    if decimals > 0:
        return f"{number:,.{decimals}f}"
    return f"{int(number):,}"


def format_datetime(dt: Union[datetime, str], format: str = 'full') -> str:
    """
    Форматування дати та часу

    Args:
        dt: Дата (datetime об'єкт або ISO string)
        format: Формат виводу ('full', 'date', 'time', 'short', 'iso')

    Returns:
        Відформатована дата
    """
    # Конвертуємо строку в datetime якщо потрібно
    if isinstance(dt, str):
        try:
            # Видаляємо мілісекунди якщо є
            if '.' in dt:
                dt = dt.split('.')[0] + 'Z' if dt.endswith('Z') else dt.split('.')[0]
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt

    # Переконуємося що є timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Форматуємо відповідно до вибраного формату
    if format == 'full':
        return dt.strftime('%d.%m.%Y %H:%M:%S')
    elif format == 'date':
        return dt.strftime('%d.%m.%Y')
    elif format == 'time':
        return dt.strftime('%H:%M:%S')
    elif format == 'short':
        return dt.strftime('%d.%m %H:%M')
    elif format == 'iso':
        return dt.isoformat()
    else:
        return str(dt)


def format_telegram_username(username: Optional[str]) -> str:
    """
    Форматування Telegram username

    Args:
        username: Username

    Returns:
        Відформатований username з @
    """
    if not username:
        return 'Anonymous'

    # Видаляємо @ якщо є на початку
    username = username.lstrip('@')

    # Обрізаємо до максимальної довжини
    if len(username) > TELEGRAM_LIMITS['USERNAME_MAX_LENGTH']:
        username = username[:TELEGRAM_LIMITS['USERNAME_MAX_LENGTH']]

    return f"@{username}"


def format_telegram_name(first_name: str, last_name: Optional[str] = None) -> str:
    """
    Форматування повного імені Telegram користувача

    Args:
        first_name: Ім'я
        last_name: Прізвище (опціонально)

    Returns:
        Повне ім'я
    """
    # Обрізаємо до максимальної довжини
    if len(first_name) > TELEGRAM_LIMITS['FIRST_NAME_MAX_LENGTH']:
        first_name = first_name[:TELEGRAM_LIMITS['FIRST_NAME_MAX_LENGTH']]

    if last_name:
        if len(last_name) > TELEGRAM_LIMITS['LAST_NAME_MAX_LENGTH']:
            last_name = last_name[:TELEGRAM_LIMITS['LAST_NAME_MAX_LENGTH']]
        return f"{first_name} {last_name}"

    return first_name


def format_order_id(order_id: Union[int, str]) -> str:
    """
    Форматування ID замовлення

    Args:
        order_id: ID замовлення

    Returns:
        Відформатований ID
    """
    return f"#{str(order_id).zfill(6)}"


def format_payment_id(payment_id: str) -> str:
    """
    Форматування ID платежу

    Args:
        payment_id: ID платежу

    Returns:
        Відформатований ID
    """
    # Показуємо перші та останні символи
    if len(payment_id) > 12:
        return f"{payment_id[:6]}...{payment_id[-4:]}"
    return payment_id


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Форматування відсотків

    Args:
        value: Значення (0.1 = 10%)
        decimals: Кількість знаків після коми

    Returns:
        Відформатовані відсотки
    """
    percentage = value * 100
    return f"{percentage:.{decimals}f}%"


def format_status(status: str) -> str:
    """
    Форматування статусу для відображення

    Args:
        status: Статус (pending, completed, etc.)

    Returns:
        Локалізований статус з емодзі
    """
    status_map = {
        # Order statuses
        'pending': '⏳ Очікується',
        'processing': '⚙️ Обробляється',
        'in_progress': '🔄 Виконується',
        'completed': '✅ Виконано',
        'partial': '⚠️ Частково',
        'cancelled': '❌ Скасовано',
        'failed': '❌ Помилка',

        # Payment statuses
        'waiting': '⏳ Очікує оплати',
        'confirming': '🔍 Перевіряється',
        'confirmed': '✅ Підтверджено',
        'sending': '📤 Відправляється',
        'partially_paid': '⚠️ Частково оплачено',
        'finished': '✅ Завершено',
        'refunded': '↩️ Повернено',
        'expired': '⏰ Прострочено',
    }

    return status_map.get(status, status.replace('_', ' ').title())


def format_service_type(service_type: str) -> str:
    """
    Форматування типу сервісу

    Args:
        service_type: Тип сервісу

    Returns:
        Локалізований тип
    """
    type_map = {
        'default': '👤 Звичайний',
        'package': '📦 Пакет',
        'custom_comments': '💬 Власні коментарі',
        'mentions': '🏷️ Згадки',
        'poll': '📊 Опитування',
        'subscriptions': '🔔 Підписки',
    }

    return type_map.get(service_type, service_type.replace('_', ' ').title())


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Маскування чутливих даних

    Args:
        data: Дані для маскування
        visible_chars: Кількість видимих символів

    Returns:
        Замасковані дані
    """
    if not data or len(data) <= visible_chars * 2:
        return '****'

    return f"{data[:visible_chars]}{'*' * 6}{data[-visible_chars:]}"


def generate_referral_code(user_id: Union[int, str]) -> str:
    """
    Генерація реферального коду

    Args:
        user_id: ID користувача

    Returns:
        Реферальний код
    """
    # Створюємо хеш від user_id
    hash_object = hashlib.md5(str(user_id).encode())
    hash_hex = hash_object.hexdigest()

    # Беремо перші 8 символів та робимо uppercase
    return f"TB{hash_hex[:8].upper()}"


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Обрізати текст до максимальної довжини

    Args:
        text: Текст
        max_length: Максимальна довжина
        suffix: Суфікс для обрізаного тексту

    Returns:
        Обрізаний текст
    """
    if not text or len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def clean_html(text: str) -> str:
    """
    Очистити текст від HTML тегів

    Args:
        text: Текст з HTML

    Returns:
        Очищений текст
    """
    if not text:
        return ''

    # Видаляємо HTML теги
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def format_file_size(size_bytes: int) -> str:
    """
    Форматування розміру файлу

    Args:
        size_bytes: Розмір в байтах

    Returns:
        Відформатований розмір
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0

    return f"{size_bytes:.2f} PB"


def pluralize_ukrainian(count: int, forms: tuple) -> str:
    """
    Відмінювання українських слів за числом

    Args:
        count: Кількість
        forms: Кортеж з трьох форм (1, 2-4, 5+)
               Наприклад: ('замовлення', 'замовлення', 'замовлень')

    Returns:
        Правильна форма слова
    """
    if count % 10 == 1 and count % 100 != 11:
        return forms[0]
    elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
        return forms[1]
    else:
        return forms[2]