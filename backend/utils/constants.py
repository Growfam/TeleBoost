# backend/utils/constants.py
"""
TeleBoost Constants
Централізовані константи проекту
"""
from typing import Dict, Any


# === Payment Constants ===

class PAYMENT_STATUS:
    """Статуси платежів"""
    WAITING = 'waiting'  # Очікує оплати
    CONFIRMING = 'confirming'  # Підтверджується мережею
    CONFIRMED = 'confirmed'  # Підтверджено
    SENDING = 'sending'  # Відправляється
    PARTIALLY_PAID = 'partially_paid'  # Частково оплачено
    FINISHED = 'finished'  # Завершено
    FAILED = 'failed'  # Невдалий
    REFUNDED = 'refunded'  # Повернено
    EXPIRED = 'expired'  # Прострочено
    PROCESSING = 'processing'  # Обробляється

    @classmethod
    def all(cls):
        """Всі статуси"""
        return [
            cls.WAITING, cls.CONFIRMING, cls.CONFIRMED, cls.SENDING,
            cls.PARTIALLY_PAID, cls.FINISHED, cls.FAILED,
            cls.REFUNDED, cls.EXPIRED, cls.PROCESSING
        ]


class PAYMENT_PROVIDERS:
    """Платіжні провайдери"""
    CRYPTOBOT = 'cryptobot'
    NOWPAYMENTS = 'nowpayments'

# === Transaction Types ===

class TRANSACTION_TYPE:
    """Типи транзакцій"""
    DEPOSIT = 'deposit'  # Поповнення
    WITHDRAWAL = 'withdrawal'  # Виведення
    ORDER = 'order'  # Оплата замовлення
    REFERRAL_BONUS = 'referral_bonus'  # Реферальний бонус
    REFUND = 'refund'  # Повернення
    ADMIN_ADD = 'admin_add'  # Адмін додав
    ADMIN_DEDUCT = 'admin_deduct'  # Адмін зняв
    PROMO_BONUS = 'promo_bonus'  # Промо бонус


# === Order Status ===

class OrderStatus:
    """Статуси замовлень"""
    PENDING = 'Pending'
    IN_PROGRESS = 'In progress'
    PROCESSING = 'Processing'
    COMPLETED = 'Completed'
    PARTIAL = 'Partial'
    CANCELLED = 'Cancelled'
    FAILED = 'Failed'

    @classmethod
    def all(cls):
        return [
            cls.PENDING, cls.IN_PROGRESS, cls.PROCESSING,
            cls.COMPLETED, cls.PARTIAL, cls.CANCELLED, cls.FAILED
        ]


# === Service Types ===

class ServiceType:
    """Типи сервісів"""
    DEFAULT = 'default'
    DRIP_FEED = 'drip_feed'
    CUSTOM_COMMENTS = 'custom_comments'
    SUBSCRIPTION = 'subscription'
    POLL = 'poll'


SERVICE_TYPE = ServiceType  # Для сумісності

# === Crypto Currencies ===

CRYPTO_CURRENCIES = {
    'USDT': {
        'name': 'Tether',
        'symbol': 'USDT',
        'decimals': 6,
        'networks': ['TRC20', 'BEP20', 'ERC20', 'SOL', 'TON']
    },
    'BTC': {
        'name': 'Bitcoin',
        'symbol': 'BTC',
        'decimals': 8,
        'networks': ['Bitcoin']
    },
    'ETH': {
        'name': 'Ethereum',
        'symbol': 'ETH',
        'decimals': 18,
        'networks': ['Ethereum']
    },
    'TON': {
        'name': 'Toncoin',
        'symbol': 'TON',
        'decimals': 9,
        'networks': ['TON']
    },
    'BNB': {
        'name': 'Binance Coin',
        'symbol': 'BNB',
        'decimals': 18,
        'networks': ['BEP20']
    },
    'TRX': {
        'name': 'Tron',
        'symbol': 'TRX',
        'decimals': 6,
        'networks': ['Tron']
    },
    'BUSD': {
        'name': 'Binance USD',
        'symbol': 'BUSD',
        'decimals': 18,
        'networks': ['BEP20', 'ERC20']
    }
}

# === Business Limits ===

LIMITS = {
    'MIN_DEPOSIT': 100,  # Мінімальний депозит (UAH)
    'MAX_DEPOSIT': 100000,  # Максимальний депозит (UAH)
    'MIN_WITHDRAW': 500,  # Мінімальне виведення (UAH)
    'MAX_WITHDRAW': 50000,  # Максимальне виведення (UAH)
    'MIN_ORDER': 10,  # Мінімальне замовлення (UAH)
    'MAX_ORDER': 100000,  # Максимальне замовлення (UAH)
}

# === Fees ===

FEES = {
    'DEPOSIT': 0,  # Комісія за депозит (%)
    'WITHDRAWAL': 2.5,  # Комісія за виведення (%)
    'SERVICE_MARKUP': 30,  # Націнка на сервіси (%)
}

# === Cache Keys ===

CACHE_KEYS = {
    'USER': 'user:{user_id}',
    'SERVICES': 'services:all',
    'SERVICE': 'service:{service_id}',
    'BALANCE': 'balance:{user_id}',
    'ORDERS': 'orders:{user_id}',
    'ORDER': 'order:{order_id}',
    'REFERRALS': 'referrals:{user_id}',
    'PAYMENT': 'payment:{payment_id}',
    'RATES': 'rates:{from_currency}:{to_currency}',
    'STATS': 'stats:{key}',
}

# === Cache TTL (seconds) ===

CACHE_TTL = {
    'services': 3600,  # 1 година
    'user': 300,  # 5 хвилин
    'balance': 60,  # 1 хвилина
    'orders': 180,  # 3 хвилини
    'referrals': 600,  # 10 хвилин
    'rates': 300,  # 5 хвилин
    'stats': 300,  # 5 хвилин
}

# === Messages ===

SUCCESS_MESSAGES = {
    'LOGIN_SUCCESS': 'Успішний вхід',
    'LOGOUT_SUCCESS': 'Ви вийшли з системи',
    'PAYMENT_CREATED': 'Платіж створено',
    'ORDER_CREATED': 'Замовлення створено',
    'SERVICE_UPDATED': 'Сервіс оновлено',
    'PROFILE_UPDATED': 'Профіль оновлено',
    'PASSWORD_CHANGED': 'Пароль змінено',
    'WITHDRAWAL_REQUESTED': 'Запит на виведення створено',
}

ERROR_MESSAGES = {
    'UNAUTHORIZED': 'Unauthorized access',
    'INVALID_TOKEN': 'Invalid or expired token',
    'USER_NOT_FOUND': 'User not found',
    'INVALID_CREDENTIALS': 'Invalid credentials',
    'INSUFFICIENT_BALANCE': 'Insufficient balance',
    'SERVICE_NOT_FOUND': 'Service not found',
    'ORDER_NOT_FOUND': 'Order not found',
    'PAYMENT_NOT_FOUND': 'Payment not found',
    'INVALID_AMOUNT': 'Invalid amount',
    'INTERNAL_ERROR': 'Internal server error',
    'RATE_LIMIT': 'Too many requests',
    'MAINTENANCE': 'Service under maintenance',
}

# === Telegram Constants ===

TELEGRAM_COMMANDS = [
    ('start', '🚀 Почати'),
    ('help', '❓ Допомога'),
    ('balance', '💰 Баланс'),
    ('services', '📋 Сервіси'),
    ('orders', '📦 Замовлення'),
    ('referral', '👥 Реферальна програма'),
    ('support', '💬 Підтримка'),
    ('settings', '⚙️ Налаштування'),
]

# === Social Platforms ===

SOCIAL_PLATFORMS = {
    'instagram': {
        'name': 'Instagram',
        'icon': '📷',
        'color': '#E4405F'
    },
    'tiktok': {
        'name': 'TikTok',
        'icon': '🎵',
        'color': '#000000'
    },
    'youtube': {
        'name': 'YouTube',
        'icon': '📺',
        'color': '#FF0000'
    },
    'telegram': {
        'name': 'Telegram',
        'icon': '✈️',
        'color': '#0088cc'
    },
    'facebook': {
        'name': 'Facebook',
        'icon': '👤',
        'color': '#1877F2'
    },
    'twitter': {
        'name': 'Twitter',
        'icon': '🐦',
        'color': '#1DA1F2'
    },
    'twitch': {
        'name': 'Twitch',
        'icon': '🎮',
        'color': '#9146FF'
    },
    'spotify': {
        'name': 'Spotify',
        'icon': '🎧',
        'color': '#1DB954'
    },
    'discord': {
        'name': 'Discord',
        'icon': '💬',
        'color': '#5865F2'
    },
    'vk': {
        'name': 'VKontakte',
        'icon': '📱',
        'color': '#0077FF'
    },
    'threads': {
        'name': 'Threads',
        'icon': '🧵',
        'color': '#000000'
    }
}

# === API Response Codes ===

API_CODES = {
    'SUCCESS': 'SUCCESS',
    'ERROR': 'ERROR',
    'VALIDATION_ERROR': 'VALIDATION_ERROR',
    'NOT_FOUND': 'NOT_FOUND',
    'UNAUTHORIZED': 'UNAUTHORIZED',
    'FORBIDDEN': 'FORBIDDEN',
    'RATE_LIMIT': 'RATE_LIMIT',
    'MAINTENANCE': 'MAINTENANCE',
    'PAYMENT_REQUIRED': 'PAYMENT_REQUIRED',
    'INSUFFICIENT_BALANCE': 'INSUFFICIENT_BALANCE',
}

# === Permissions ===

PERMISSIONS = {
    'USER': 'user',
    'MODERATOR': 'moderator',
    'ADMIN': 'admin',
    'SUPER_ADMIN': 'super_admin',
}

# === Time Zones ===

DEFAULT_TIMEZONE = 'Europe/Kyiv'  # Ukrainian timezone
SUPPORTED_TIMEZONES = [
    'Europe/Kyiv',
    'Europe/London',
    'Europe/Paris',
    'America/New_York',
    'America/Los_Angeles',
    'Asia/Tokyo',
    'Asia/Shanghai',
    'Australia/Sydney',
]