# backend/utils/constants.py
"""
TeleBoost Constants
Всі константи проекту в одному місці
"""
from enum import Enum
from typing import Dict, Any


class ORDER_STATUS:
    """Статуси замовлень"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    PARTIAL = 'partial'
    CANCELLED = 'cancelled'
    FAILED = 'failed'

    @classmethod
    def all(cls) -> list:
        return [cls.PENDING, cls.PROCESSING, cls.IN_PROGRESS,
                cls.COMPLETED, cls.PARTIAL, cls.CANCELLED, cls.FAILED]

    @classmethod
    def active(cls) -> list:
        return [cls.PENDING, cls.PROCESSING, cls.IN_PROGRESS]

    @classmethod
    def final(cls) -> list:
        return [cls.COMPLETED, cls.PARTIAL, cls.CANCELLED, cls.FAILED]


class PAYMENT_STATUS:
    """Статуси платежів"""
    WAITING = 'waiting'
    CONFIRMING = 'confirming'
    CONFIRMED = 'confirmed'
    SENDING = 'sending'
    PARTIALLY_PAID = 'partially_paid'
    FINISHED = 'finished'
    FAILED = 'failed'
    REFUNDED = 'refunded'
    EXPIRED = 'expired'

    @classmethod
    def all(cls) -> list:
        return [cls.WAITING, cls.CONFIRMING, cls.CONFIRMED, cls.SENDING,
                cls.PARTIALLY_PAID, cls.FINISHED, cls.FAILED, cls.REFUNDED, cls.EXPIRED]

    @classmethod
    def success(cls) -> list:
        return [cls.CONFIRMED, cls.FINISHED]

    @classmethod
    def pending(cls) -> list:
        return [cls.WAITING, cls.CONFIRMING, cls.SENDING, cls.PARTIALLY_PAID]


class TRANSACTION_TYPE:
    """Типи транзакцій"""
    DEPOSIT = 'deposit'
    WITHDRAW = 'withdraw'
    ORDER = 'order'
    REFUND = 'refund'
    REFERRAL_BONUS = 'referral_bonus'
    CASHBACK = 'cashback'
    ADMIN_CREDIT = 'admin_credit'
    ADMIN_DEBIT = 'admin_debit'

    @classmethod
    def income(cls) -> list:
        return [cls.DEPOSIT, cls.REFUND, cls.REFERRAL_BONUS, cls.CASHBACK, cls.ADMIN_CREDIT]

    @classmethod
    def expense(cls) -> list:
        return [cls.WITHDRAW, cls.ORDER, cls.ADMIN_DEBIT]


class SERVICE_TYPE:
    """Типи сервісів Nakrutochka"""
    DEFAULT = 'default'
    PACKAGE = 'package'
    CUSTOM_COMMENTS = 'custom_comments'
    CUSTOM_COMMENTS_PACKAGE = 'custom_comments_package'
    MENTIONS = 'mentions'
    MENTIONS_WITH_HASHTAGS = 'mentions_with_hashtags'
    MENTIONS_CUSTOM_LIST = 'mentions_custom_list'
    MENTIONS_HASHTAG = 'mentions_hashtag'
    MENTIONS_USER_FOLLOWERS = 'mentions_user_followers'
    MENTIONS_MEDIA_LIKERS = 'mentions_media_likers'
    PACKAGE_TEXT = 'package_text'
    COMMENT_LIKES = 'comment_likes'
    POLL = 'poll'
    INVITES_FROM_GROUPS = 'invites_from_groups'
    SUBSCRIPTIONS = 'subscriptions'
    DRIP_FEED = 'drip_feed'
    SUBSCRIPTION = 'subscription'


# Референтні винагороди
REFERRAL_LEVELS = {
    1: 0.10,  # 10% для прямого реферала
    2: 0.05,  # 5% для реферала другого рівня (якщо потрібно)
}

# Ліміти
LIMITS = {
    'MIN_DEPOSIT': 100,
    'MAX_DEPOSIT': 100000,
    'MIN_WITHDRAW': 500,
    'MAX_WITHDRAW': 50000,
    'MIN_ORDER': 10,
    'MAX_ORDER': 100000,
    'MAX_REFERRAL_LEVELS': 1,  # Тільки один рівень рефералів
    'MAX_COMMENT_LENGTH': 1000,  # Максимальна довжина коментаря
    'MAX_COMMENTS_PER_ORDER': 10000,  # Максимум коментарів в замовленні
    'MAX_ACTIVE_ORDERS': 50,  # Максимум активних замовлень на користувача
}

# Комісії
FEES = {
    'DEPOSIT': 0.0,  # 0% комісія на поповнення
    'WITHDRAW': 0.03,  # 3% комісія на виведення
    'ORDER': 0.0,  # 0% комісія на замовлення
}


# Cache ключі
class CACHE_KEYS:
    """Префікси для Redis ключів"""
    USER = 'user:{user_id}'
    USER_BALANCE = 'balance:{user_id}'
    USER_ORDERS = 'orders:{user_id}'
    USER_REFERRALS = 'referrals:{user_id}'
    SERVICES = 'services:all'
    SERVICE = 'service:{service_id}'
    ORDER = 'order:{order_id}'
    PAYMENT = 'payment:{payment_id}'
    JWT_TOKEN = 'jwt:{jti}'
    RATE_LIMIT = 'rate:{user_id}:{endpoint}'

    @classmethod
    def format(cls, key: str, **kwargs) -> str:
        """Форматування ключа з параметрами"""
        return key.format(**kwargs)


# Cache префікси для middleware
CACHE_PREFIX = {
    'services': 'cache:services',
    'users': 'cache:users',
    'orders': 'cache:orders',
    'response': 'response:',
    'statistics': 'cache:stats',
    'referrals': 'cache:referrals',
}

# Cache TTL для різних типів даних
CACHE_TTL = {
    'services': 3600,  # 1 година
    'user': 300,  # 5 хвилин
    'balance': 60,  # 1 хвилина
    'orders': 180,  # 3 хвилини
    'referrals': 600,  # 10 хвилин
    'statistics': 300,  # 5 хвилин
    'exchange_rates': 3600,  # 1 година
}

# Telegram limits
TELEGRAM_LIMITS = {
    'USERNAME_MIN_LENGTH': 5,
    'USERNAME_MAX_LENGTH': 32,
    'FIRST_NAME_MAX_LENGTH': 64,
    'LAST_NAME_MAX_LENGTH': 64,
    'MESSAGE_MAX_LENGTH': 4096,
    'CAPTION_MAX_LENGTH': 1024,
    'CALLBACK_DATA_MAX_LENGTH': 64,
}

# Error messages
ERROR_MESSAGES = {
    'INVALID_TOKEN': 'Недійсний токен авторизації',
    'TOKEN_EXPIRED': 'Токен авторизації закінчився',
    'USER_NOT_FOUND': 'Користувача не знайдено',
    'INSUFFICIENT_BALANCE': 'Недостатньо коштів на балансі',
    'SERVICE_NOT_FOUND': 'Сервіс не знайдено',
    'INVALID_ORDER_DATA': 'Некоректні дані замовлення',
    'ORDER_NOT_FOUND': 'Замовлення не знайдено',
    'PAYMENT_NOT_FOUND': 'Платіж не знайдено',
    'INVALID_AMOUNT': 'Некоректна сума',
    'LIMIT_EXCEEDED': 'Перевищено ліміт',
    'RATE_LIMIT': 'Занадто багато запитів',
    'INTERNAL_ERROR': 'Внутрішня помилка сервера',
    'MAINTENANCE_MODE': 'Сервіс на технічному обслуговуванні',
    'FEATURE_DISABLED': 'Ця функція тимчасово недоступна',
    'INVALID_REFERRAL_CODE': 'Недійсний реферальний код',
    'SELF_REFERRAL': 'Не можна використовувати власний реферальний код',
    'ALREADY_REFERRED': 'Ви вже були запрошені іншим користувачем',
}

# Success messages
SUCCESS_MESSAGES = {
    'LOGIN_SUCCESS': 'Успішна авторизація',
    'ORDER_CREATED': 'Замовлення створено',
    'PAYMENT_CREATED': 'Платіж створено',
    'PAYMENT_SUCCESS': 'Платіж успішно оброблено',
    'BALANCE_UPDATED': 'Баланс оновлено',
    'WITHDRAWAL_REQUESTED': 'Запит на виведення прийнято',
    'PROFILE_UPDATED': 'Профіль оновлено',
    'REFERRAL_ACTIVATED': 'Реферальний код активовано',
}

# Nakrutochka API endpoints (Legacy - for compatibility)
NAKRUTOCHKA_ENDPOINTS = {
    'SERVICES': '/services',
    'ORDER': '/order',
    'STATUS': '/status',
    'MULTI_STATUS': '/multi-status',
    'BALANCE': '/balance',
    'REFILL': '/refill',
    'REFILL_STATUS': '/refill-status',
    'CANCEL': '/cancel',
}

# Add OrderStatus and ServiceType aliases for nakrutochka_api.py
OrderStatus = ORDER_STATUS
ServiceType = SERVICE_TYPE


# Payment providers
class PAYMENT_PROVIDERS:
    """Доступні платіжні провайдери"""
    CRYPTOBOT = 'cryptobot'
    NOWPAYMENTS = 'nowpayments'
    MONOBANK = 'monobank'

    @classmethod
    def all(cls) -> list:
        return [cls.CRYPTOBOT, cls.NOWPAYMENTS, cls.MONOBANK]

    @classmethod
    def crypto(cls) -> list:
        return [cls.CRYPTOBOT, cls.NOWPAYMENTS]

    @classmethod
    def fiat(cls) -> list:
        return [cls.MONOBANK]


# Supported cryptocurrencies
CRYPTO_CURRENCIES = {
    'BTC': {'name': 'Bitcoin', 'decimals': 8},
    'ETH': {'name': 'Ethereum', 'decimals': 18},
    'USDT': {'name': 'Tether', 'decimals': 6},
    'TON': {'name': 'Toncoin', 'decimals': 9},
    'BNB': {'name': 'Binance Coin', 'decimals': 18},
    'TRX': {'name': 'TRON', 'decimals': 6},
}

# Регулярні вирази
REGEX_PATTERNS = {
    'TELEGRAM_USERNAME': r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$',
    'URL': r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$',
    'INSTAGRAM_URL': r'^https?:\/\/(www\.)?instagram\.com\/.*$',
    'TELEGRAM_URL': r'^https?:\/\/(www\.)?(t\.me|telegram\.me)\/.*$',
    'YOUTUBE_URL': r'^https?:\/\/(www\.)?(youtube\.com|youtu\.be)\/.*$',
    'TIKTOK_URL': r'^https?:\/\/(www\.)?tiktok\.com\/.*$',
    'TWITTER_URL': r'^https?:\/\/(www\.)?(twitter\.com|x\.com)\/.*$',
    'FACEBOOK_URL': r'^https?:\/\/(www\.)?(facebook\.com|fb\.com)\/.*$',
    'EMAIL': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    'PHONE_UA': r'^(\+?38)?(0\d{9})$',
    'UUID': r'^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$',
}

# Social media categories
SOCIAL_MEDIA_CATEGORIES = {
    'instagram': {
        'name': 'Instagram',
        'icon': '📷',
        'color': '#E4405F',
        'services': ['followers', 'likes', 'views', 'comments', 'reels', 'story', 'live'],
    },
    'telegram': {
        'name': 'Telegram',
        'icon': '✈️',
        'color': '#0088CC',
        'services': ['members', 'views', 'reactions', 'comments', 'votes'],
    },
    'youtube': {
        'name': 'YouTube',
        'icon': '📺',
        'color': '#FF0000',
        'services': ['subscribers', 'views', 'likes', 'comments', 'shorts'],
    },
    'tiktok': {
        'name': 'TikTok',
        'icon': '🎵',
        'color': '#000000',
        'services': ['followers', 'likes', 'views', 'comments', 'shares'],
    },
    'twitter': {
        'name': 'Twitter / X',
        'icon': '🐦',
        'color': '#1DA1F2',
        'services': ['followers', 'likes', 'retweets', 'comments', 'views'],
    },
    'facebook': {
        'name': 'Facebook',
        'icon': '👤',
        'color': '#1877F2',
        'services': ['likes', 'followers', 'views', 'comments', 'shares'],
    },
}

# Bot commands
BOT_COMMANDS = {
    'start': 'Почати роботу з ботом',
    'help': 'Допомога',
    'balance': 'Баланс',
    'orders': 'Мої замовлення',
    'referral': 'Реферальна програма',
    'support': 'Підтримка',
    'settings': 'Налаштування',
    'language': 'Змінити мову',
}

# Supported languages
LANGUAGES = {
    'uk': {'name': 'Українська', 'flag': '🇺🇦'},
    'en': {'name': 'English', 'flag': '🇬🇧'},
    'ru': {'name': 'Русский', 'flag': '🇷🇺'},
}

# Order priorities
ORDER_PRIORITIES = {
    'low': {'name': 'Низький', 'multiplier': 1.0},
    'normal': {'name': 'Звичайний', 'multiplier': 1.0},
    'high': {'name': 'Високий', 'multiplier': 1.2},
    'urgent': {'name': 'Терміновий', 'multiplier': 1.5},
}

# Time intervals for drip-feed
DRIP_FEED_INTERVALS = {
    '1m': 1,  # 1 хвилина
    '5m': 5,  # 5 хвилин
    '10m': 10,  # 10 хвилин
    '30m': 30,  # 30 хвилин
    '1h': 60,  # 1 година
    '2h': 120,  # 2 години
    '6h': 360,  # 6 годин
    '12h': 720,  # 12 годин
    '24h': 1440,  # 24 години
}

# Default values
DEFAULTS = {
    'LANGUAGE': 'uk',
    'CURRENCY': 'USD',
    'PAGE_SIZE': 20,
    'ORDER_PRIORITY': 'normal',
    'DRIP_FEED_INTERVAL': '1h',
    'REFERRAL_BONUS': 10.0,  # відсотки
}