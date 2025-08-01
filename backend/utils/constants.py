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
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    PARTIAL = 'partial'
    CANCELLED = 'cancelled'
    FAILED = 'failed'


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
    PACKAGE = 'package'
    MENTIONS = 'mentions'


SERVICE_TYPE = ServiceType  # Для сумісності

# === Order Status (старий формат для сумісності) ===
ORDER_STATUS = OrderStatus

# === Crypto Currencies ===

CRYPTO_CURRENCIES = {
    'USDT': {
        'name': 'Tether',
        'symbol': 'USDT',
        'decimals': 6,
        'networks': ['TRC20', 'BEP20', 'ERC20', 'SOL', 'TON'],
        'min_amount': 1.0,
        'max_amount': 100000.0
    },
    'BTC': {
        'name': 'Bitcoin',
        'symbol': 'BTC',
        'decimals': 8,
        'networks': ['Bitcoin'],
        'min_amount': 0.0001,
        'max_amount': 10.0
    },
    'ETH': {
        'name': 'Ethereum',
        'symbol': 'ETH',
        'decimals': 18,
        'networks': ['Ethereum'],
        'min_amount': 0.001,
        'max_amount': 100.0
    },
    'TON': {
        'name': 'Toncoin',
        'symbol': 'TON',
        'decimals': 9,
        'networks': ['TON'],
        'min_amount': 5.0,
        'max_amount': 100000.0
    },
    'BNB': {
        'name': 'Binance Coin',
        'symbol': 'BNB',
        'decimals': 18,
        'networks': ['BEP20'],
        'min_amount': 0.01,
        'max_amount': 1000.0
    },
    'TRX': {
        'name': 'Tron',
        'symbol': 'TRX',
        'decimals': 6,
        'networks': ['Tron'],
        'min_amount': 10.0,
        'max_amount': 1000000.0
    },
    'BUSD': {
        'name': 'Binance USD',
        'symbol': 'BUSD',
        'decimals': 18,
        'networks': ['BEP20', 'ERC20'],
        'min_amount': 1.0,
        'max_amount': 100000.0
    }
}

# === Business Limits ===

LIMITS = {
    'MIN_DEPOSIT': 10,  # Мінімальний депозит (USD)
    'MAX_DEPOSIT': 100000,  # Максимальний депозит (USD)
    'MIN_WITHDRAW': 50,  # Мінімальне виведення (USD)
    'MAX_WITHDRAW': 50000,  # Максимальне виведення (USD)
    'MIN_ORDER': 1,  # Мінімальне замовлення (USD)
    'MAX_ORDER': 10000,  # Максимальне замовлення (USD)
}

# === Fees ===

FEES = {
    'DEPOSIT': 0,  # Комісія за депозит (%)
    'WITHDRAWAL': 2.5,  # Комісія за виведення (%)
    'SERVICE_MARKUP': 30,  # Націнка на сервіси (%)
}

# === Telegram Limits ===

TELEGRAM_LIMITS = {
    'USERNAME_MIN_LENGTH': 5,
    'USERNAME_MAX_LENGTH': 32,
    'FIRST_NAME_MAX_LENGTH': 64,
    'LAST_NAME_MAX_LENGTH': 64,
    'BIO_MAX_LENGTH': 70,
    'MESSAGE_MAX_LENGTH': 4096,
    'CAPTION_MAX_LENGTH': 1024,
    'CALLBACK_DATA_MAX_LENGTH': 64,
}

# === Regex Patterns ===

REGEX_PATTERNS = {
    # General
    'URL': r'^https?://[^\s<>"{}|\\^`\[\]]+$',
    'EMAIL': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    'PHONE': r'^\+?[1-9]\d{1,14}$',

    # Telegram
    'TELEGRAM_USERNAME': r'^[a-zA-Z0-9_]{5,32}$',
    'TELEGRAM_URL': r'^https?://(www\.)?(t\.me|telegram\.me|telegram\.dog)/[\w\-]+/?(\d+)?$',

    # Social Media
    'INSTAGRAM_URL': r'^https?://(www\.)?instagram\.com/(p/[\w\-]+|[\w\-\.]+|reel/[\w\-]+|tv/[\w\-]+|stories/[\w\-\.]+/\d+)/?$',
    'YOUTUBE_URL': r'^https?://(www\.)?(youtube\.com/(watch\?v=|channel/|c/|@)[\w\-]+|youtu\.be/[\w\-]+)/?$',
    'TIKTOK_URL': r'^https?://(www\.)?(tiktok\.com/@[\w\-\.]+(/video/\d+)?|vm\.tiktok\.com/[\w\-]+)/?$',
    'TWITTER_URL': r'^https?://(www\.)?(twitter\.com|x\.com)/[\w\-]+(/(status|with_replies|media|likes))?(/\d+)?/?$',
    'FACEBOOK_URL': r'^https?://(www\.)?(facebook\.com|fb\.com)/[\w\-\.]+(/(posts|videos|photos)/[\w\-]+)?/?$',

    # Crypto
    'BTC_ADDRESS': r'^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$',
    'ETH_ADDRESS': r'^0x[a-fA-F0-9]{40}$',
    'USDT_TRC20_ADDRESS': r'^T[a-zA-Z0-9]{33}$',
    'TON_ADDRESS': r'^[a-zA-Z0-9_-]{48}$',
}

# === Cache Keys ===

CACHE_KEYS = {
    'USER': 'user:{user_id}',
    'USER_BALANCE': 'user:{user_id}:balance',
    'USER_ORDERS': 'user:{user_id}:orders',
    'USER_REFERRALS': 'user:{user_id}:referrals',
    'SERVICES': 'services:all',
    'SERVICE': 'service:{service_id}',
    'BALANCE': 'balance:{user_id}',
    'ORDERS': 'orders:{user_id}',
    'ORDER': 'order:{order_id}',
    'REFERRALS': 'referrals:{user_id}',
    'PAYMENT': 'payment:{payment_id}',
    'RATES': 'rates:{from_currency}:{to_currency}',
    'STATS': 'stats:{key}',
    'RATE_LIMIT': 'rate_limit:{user_id}:{endpoint}',
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
    'payment': 300,  # 5 хвилин
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
    'REFERRAL_ACTIVATED': 'Реферальний код активовано',
    'BONUS_CREDITED': 'Бонус нараховано',
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
    'INVALID_REFERRAL_CODE': 'Invalid referral code',
    'SELF_REFERRAL': 'Cannot use your own referral code',
    'ALREADY_REFERRED': 'You have already been referred',
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
    ('deposit', '💳 Поповнити'),
    ('withdraw', '💸 Вивести'),
    ('history', '📊 Історія'),
    ('cancel', '❌ Скасувати'),
]

# === Telegram Keyboards ===

TELEGRAM_KEYBOARDS = {
    'MAIN_MENU': [
        ['💰 Баланс', '📋 Сервіси'],
        ['📦 Замовлення', '👥 Рефералі'],
        ['💳 Поповнити', '💸 Вивести'],
        ['⚙️ Налаштування', '💬 Підтримка']
    ],
    'BACK_ONLY': [
        ['⬅️ Назад']
    ],
    'CONFIRM_CANCEL': [
        ['✅ Підтвердити', '❌ Скасувати']
    ],
}

# === Social Platforms ===

SOCIAL_PLATFORMS = {
    'instagram': {
        'name': 'Instagram',
        'icon': '📷',
        'color': '#E4405F',
        'domains': ['instagram.com', 'www.instagram.com']
    },
    'tiktok': {
        'name': 'TikTok',
        'icon': '🎵',
        'color': '#000000',
        'domains': ['tiktok.com', 'www.tiktok.com', 'vm.tiktok.com']
    },
    'youtube': {
        'name': 'YouTube',
        'icon': '📺',
        'color': '#FF0000',
        'domains': ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com']
    },
    'telegram': {
        'name': 'Telegram',
        'icon': '✈️',
        'color': '#0088cc',
        'domains': ['t.me', 'telegram.me', 'telegram.dog']
    },
    'facebook': {
        'name': 'Facebook',
        'icon': '👤',
        'color': '#1877F2',
        'domains': ['facebook.com', 'www.facebook.com', 'fb.com', 'm.facebook.com']
    },
    'twitter': {
        'name': 'Twitter/X',
        'icon': '🐦',
        'color': '#1DA1F2',
        'domains': ['twitter.com', 'www.twitter.com', 'x.com', 'www.x.com']
    },
    'twitch': {
        'name': 'Twitch',
        'icon': '🎮',
        'color': '#9146FF',
        'domains': ['twitch.tv', 'www.twitch.tv']
    },
    'spotify': {
        'name': 'Spotify',
        'icon': '🎧',
        'color': '#1DB954',
        'domains': ['spotify.com', 'open.spotify.com']
    },
    'discord': {
        'name': 'Discord',
        'icon': '💬',
        'color': '#5865F2',
        'domains': ['discord.gg', 'discord.com']
    },
    'vk': {
        'name': 'VKontakte',
        'icon': '📱',
        'color': '#0077FF',
        'domains': ['vk.com', 'www.vk.com', 'm.vk.com']
    },
    'threads': {
        'name': 'Threads',
        'icon': '🧵',
        'color': '#000000',
        'domains': ['threads.net', 'www.threads.net']
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
    'DUPLICATE': 'DUPLICATE',
    'EXPIRED': 'EXPIRED',
    'INVALID_STATE': 'INVALID_STATE',
}

# === Permissions ===

PERMISSIONS = {
    'USER': 'user',
    'MODERATOR': 'moderator',
    'ADMIN': 'admin',
    'SUPER_ADMIN': 'super_admin',
}

# === User Roles ===

USER_ROLES = {
    'DEFAULT': 'default',
    'PREMIUM': 'premium',
    'VIP': 'vip',
    'PARTNER': 'partner',
}


# === Withdrawal Status ===

class WITHDRAWAL_STATUS:
    """Статуси виведення"""
    PENDING = 'pending'  # Очікує обробки
    PROCESSING = 'processing'  # Обробляється
    APPROVED = 'approved'  # Підтверджено
    COMPLETED = 'completed'  # Виконано
    REJECTED = 'rejected'  # Відхилено
    CANCELLED = 'cancelled'  # Скасовано
    FAILED = 'failed'  # Помилка

    @classmethod
    def all(cls):
        return [
            cls.PENDING, cls.PROCESSING, cls.APPROVED,
            cls.COMPLETED, cls.REJECTED, cls.CANCELLED, cls.FAILED
        ]


# === Promo Code Types ===

class PROMO_CODE_TYPE:
    """Типи промокодів"""
    FIXED = 'fixed'  # Фіксована сума
    PERCENTAGE = 'percentage'  # Відсоток
    DEPOSIT_BONUS = 'deposit_bonus'  # Бонус на депозит
    SERVICE_DISCOUNT = 'service_discount'  # Знижка на сервіс


# === Notification Types ===

NOTIFICATION_TYPES = {
    'ORDER_CREATED': 'order_created',
    'ORDER_COMPLETED': 'order_completed',
    'ORDER_FAILED': 'order_failed',
    'PAYMENT_RECEIVED': 'payment_received',
    'WITHDRAWAL_APPROVED': 'withdrawal_approved',
    'WITHDRAWAL_COMPLETED': 'withdrawal_completed',
    'REFERRAL_BONUS': 'referral_bonus',
    'PROMO_ACTIVATED': 'promo_activated',
    'SYSTEM_MESSAGE': 'system_message',
}

# === Time Zones ===

DEFAULT_TIMEZONE = 'Europe/Kyiv'  # Ukrainian timezone
SUPPORTED_TIMEZONES = [
    'Europe/Kyiv',
    'Europe/London',
    'Europe/Paris',
    'Europe/Berlin',
    'Europe/Moscow',
    'America/New_York',
    'America/Los_Angeles',
    'America/Chicago',
    'Asia/Tokyo',
    'Asia/Shanghai',
    'Asia/Dubai',
    'Australia/Sydney',
]

# === Languages ===

SUPPORTED_LANGUAGES = {
    'uk': {'name': 'Українська', 'flag': '🇺🇦'},
    'en': {'name': 'English', 'flag': '🇬🇧'},
    'ru': {'name': 'Русский', 'flag': '🇷🇺'},
    'es': {'name': 'Español', 'flag': '🇪🇸'},
    'de': {'name': 'Deutsch', 'flag': '🇩🇪'},
    'fr': {'name': 'Français', 'flag': '🇫🇷'},
    'it': {'name': 'Italiano', 'flag': '🇮🇹'},
    'pl': {'name': 'Polski', 'flag': '🇵🇱'},
}

DEFAULT_LANGUAGE = 'uk'

# === Rate Limits ===

RATE_LIMITS = {
    'api_global': '100 per hour',
    'api_authenticated': '1000 per hour',
    'api_premium': '5000 per hour',
    'login': '10 per hour',
    'register': '5 per hour',
    'order_create': '30 per hour',
    'payment_create': '20 per hour',
    'withdrawal_create': '5 per day',
}

# === File Upload ===

FILE_UPLOAD = {
    'MAX_SIZE': 16 * 1024 * 1024,  # 16MB
    'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx'},
    'IMAGE_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
    'DOCUMENT_EXTENSIONS': {'pdf', 'doc', 'docx', 'txt', 'csv', 'xlsx'},
}

# === Pagination ===

PAGINATION = {
    'DEFAULT_PAGE': 1,
    'DEFAULT_PER_PAGE': 20,
    'MAX_PER_PAGE': 100,
}

# === Security ===

SECURITY = {
    'PASSWORD_MIN_LENGTH': 8,
    'PASSWORD_MAX_LENGTH': 128,
    'PASSWORD_REQUIRE_UPPERCASE': True,
    'PASSWORD_REQUIRE_LOWERCASE': True,
    'PASSWORD_REQUIRE_NUMBERS': True,
    'PASSWORD_REQUIRE_SPECIAL': True,
    'SESSION_LIFETIME': 86400,  # 24 hours
    'REMEMBER_ME_DURATION': 2592000,  # 30 days
}

# === External APIs ===

EXTERNAL_APIS = {
    'NAKRUTOCHKA': {
        'BASE_URL': 'https://nakrutochka.com/api/v2',
        'TIMEOUT': 30,
        'MAX_RETRIES': 3,
    },
    'CRYPTOBOT': {
        'BASE_URL': 'https://pay.crypt.bot/api',
        'TESTNET_URL': 'https://testnet-pay.crypt.bot/api',
        'TIMEOUT': 30,
    },
    'NOWPAYMENTS': {
        'BASE_URL': 'https://api.nowpayments.io/v1',
        'SANDBOX_URL': 'https://api-sandbox.nowpayments.io/v1',
        'TIMEOUT': 30,
    },
}

# === System Settings ===

SYSTEM_SETTINGS = {
    'MAINTENANCE_MODE': False,
    'REGISTRATION_ENABLED': True,
    'ORDERS_ENABLED': True,
    'PAYMENTS_ENABLED': True,
    'WITHDRAWALS_ENABLED': True,
    'REFERRALS_ENABLED': True,
    'PROMO_CODES_ENABLED': True,
    'TWO_FACTOR_ENABLED': False,
}

# === Webhook Endpoints ===

WEBHOOK_ENDPOINTS = {
    'TELEGRAM': '/api/telegram/webhook',
    'CRYPTOBOT': '/api/webhooks/cryptobot',
    'NOWPAYMENTS': '/api/webhooks/nowpayments',
}

# === Default Values ===

DEFAULTS = {
    'CURRENCY': 'USDT',
    'LANGUAGE': 'uk',
    'TIMEZONE': 'Europe/Kyiv',
    'PAGE_SIZE': 20,
    'CACHE_TTL': 300,
}

# === Referral System ===

REFERRAL_SETTINGS = {
    'ENABLED': True,
    'LEVELS': 2,
    'LEVEL_1_RATE': 0.07,  # 7%
    'LEVEL_2_RATE': 0.025,  # 2.5%
    'MINIMUM_DEPOSIT': 10,  # Мінімальний депозит для нарахування бонусу
    'BONUS_ON_REGISTRATION': 0,  # Бонус за реєстрацію по рефералу
    'CODE_LENGTH': 10,  # Довжина реферального коду
    'CODE_PREFIX': 'TB',  # Префікс реферального коду
}

# === Emojis ===

EMOJIS = {
    'SUCCESS': '✅',
    'ERROR': '❌',
    'WARNING': '⚠️',
    'INFO': 'ℹ️',
    'MONEY': '💰',
    'COIN': '🪙',
    'CARD': '💳',
    'ROCKET': '🚀',
    'CROWN': '👑',
    'STAR': '⭐',
    'FIRE': '🔥',
    'GIFT': '🎁',
    'USERS': '👥',
    'USER': '👤',
    'CHART': '📊',
    'PACKAGE': '📦',
    'SETTINGS': '⚙️',
    'SUPPORT': '💬',
    'BACK': '⬅️',
    'FORWARD': '➡️',
    'UP': '⬆️',
    'DOWN': '⬇️',
}