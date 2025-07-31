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


# Telegram limits
TELEGRAM_LIMITS = {
    'USERNAME_MIN_LENGTH': 5,
    'USERNAME_MAX_LENGTH': 32,
    'FIRST_NAME_MAX_LENGTH': 64,
    'LAST_NAME_MAX_LENGTH': 64,
    'MESSAGE_MAX_LENGTH': 4096,
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
}

# Success messages
SUCCESS_MESSAGES = {
    'LOGIN_SUCCESS': 'Успішна авторизація',
    'ORDER_CREATED': 'Замовлення створено',
    'PAYMENT_CREATED': 'Платіж створено',
    'PAYMENT_SUCCESS': 'Платіж успішно оброблено',
    'BALANCE_UPDATED': 'Баланс оновлено',
}

# Nakrutochka API endpoints
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

# Регулярні вирази
REGEX_PATTERNS = {
    'TELEGRAM_USERNAME': r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$',
    'URL': r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$',
    'INSTAGRAM_URL': r'^https?:\/\/(www\.)?instagram\.com\/.*$',
    'TELEGRAM_URL': r'^https?:\/\/(www\.)?(t\.me|telegram\.me)\/.*$',
    'YOUTUBE_URL': r'^https?:\/\/(www\.)?(youtube\.com|youtu\.be)\/.*$',
    'TIKTOK_URL': r'^https?:\/\/(www\.)?tiktok\.com\/.*$',
}