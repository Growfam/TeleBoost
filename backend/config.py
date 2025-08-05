# backend/config.py
"""
TeleBoost Configuration
Централізована конфігурація всього проекту
"""
import os
from datetime import timedelta
from typing import Optional
import json


class Config:
    """Основна конфігурація"""

    # Environment
    ENV = os.getenv('ENVIRONMENT', 'development')

    # DEBUG вимкнено для production
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true' if ENV == 'production' else ENV == 'development'

    TESTING = ENV == 'testing'

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'teleboost-secret-key-change-in-production')

    # Railway
    PORT = int(os.getenv('PORT', 5000))
    HOST = '0.0.0.0'  # Railway вимагає 0.0.0.0

    # URLs - ЗАВЖДИ HTTPS для Railway!
    BACKEND_URL = 'https://teleboost-teleboost.up.railway.app'
    FRONTEND_URL = 'https://teleboost-teleboost.up.railway.app'

    # Додаткові URL для сумісності
    API_URL = BACKEND_URL
    APP_URL = FRONTEND_URL

    # Database - Supabase (виправлено відповідно до Railway)
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_DECODE_RESPONSES = True
    REDIS_MAX_CONNECTIONS = 50

    # Cache TTL (seconds)
    CACHE_TTL = {
        'services': 3600,  # 1 година для списку сервісів
        'user': 300,  # 5 хвилин для користувача
        'balance': 60,  # 1 хвилина для балансу
        'orders': 180,  # 3 хвилини для замовлень
        'referrals': 600,  # 10 хвилин для рефералів
        'statistics': 300,  # 5 хвилин для статистики
    }

    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    BOT_USERNAME = os.getenv('BOT_USERNAME', 'TeleeBoost_bot')
    TELEGRAM_WEBHOOK_PATH = '/api/telegram/webhook'
    TELEGRAM_WEBHOOK_SECRET = os.getenv('TELEGRAM_WEBHOOK_SECRET', SECRET_KEY)

    # JWT Settings
    JWT_SECRET = os.getenv('JWT_SECRET', SECRET_KEY)
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Nakrutochka API
    NAKRUTOCHKA_API_URL = os.getenv('NAKRUTOCHKA_API_URL', 'https://nakrutochka.com/api/v2')
    NAKRUTOCHKA_API_KEY = os.getenv('NAKRUTOCHKA_API_KEY', '')

    # CryptoBot (виправлено відповідно до Railway)
    CRYPTOBOT_TOKEN = os.getenv('CRYPTOBOT_API_TOKEN', '')  # Змінено на CRYPTOBOT_API_TOKEN
    CRYPTOBOT_API_TOKEN = os.getenv('CRYPTOBOT_API_TOKEN', '')  # Для сумісності
    CRYPTOBOT_WEBHOOK_TOKEN = os.getenv('CRYPTOBOT_WEBHOOK_TOKEN', '')  # Додано
    CRYPTOBOT_WEBHOOK_PATH = '/api/webhooks/cryptobot'
    CRYPTOBOT_NETWORK = os.getenv('CRYPTOBOT_NETWORK', 'mainnet')  # або 'testnet' для тестування
    CRYPTOBOT_WEBHOOK_SECRET = os.getenv('CRYPTOBOT_WEBHOOK_TOKEN', '')  # Використовуємо WEBHOOK_TOKEN

    # NOWPayments
    NOWPAYMENTS_API_KEY = os.getenv('NOWPAYMENTS_API_KEY', '')
    NOWPAYMENTS_IPN_SECRET = os.getenv('NOWPAYMENTS_IPN_SECRET', '')
    NOWPAYMENTS_WEBHOOK_PATH = '/api/webhooks/nowpayments'
    NOWPAYMENTS_SANDBOX = os.getenv('NOWPAYMENTS_SANDBOX', 'false').lower() == 'true'

    # Payment Methods (додано з Railway)
    PAYMENT_METHODS = os.getenv('PAYMENT_METHODS', 'cryptobot,nowpayments').split(',')

    # Withdrawal Addresses (додано з Railway)
    WITHDRAWAL_ADDRESSES = {
        'USDT_TRC20': os.getenv('USDT_TRC20_ADDRESS', ''),
        'USDT_BEP20': os.getenv('USDT_BEP20_ADDRESS', ''),
        'USDT_SOL': os.getenv('USDT_SOLANA_ADDRESS', ''),
        'USDT_TON': os.getenv('USDT_TON_ADDRESS', ''),
    }

    # USDT Exchange Rate
    USDT_TO_UAH_RATE = float(os.getenv('USDT_TO_UAH_RATE', '40.0'))

    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_HEADERS_ENABLED = True

    # CORS - оновлено для підтримки Telegram Web App
    CORS_ORIGINS = [
        "https://web.telegram.org",
        "https://telegram.org",
        FRONTEND_URL,
    ]

    # Add localhost for development
    if DEBUG:
        CORS_ORIGINS.extend([
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ])

    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',  # Змінено з DENY для Telegram Web App
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    }

    # Business Logic - Two-level referral system
    REFERRAL_BONUS_PERCENT = 7.0  # 7% для першого рівня
    REFERRAL_BONUS_LEVEL2_PERCENT = 2.5  # 2.5% для другого рівня
    REFERRAL_USER_BONUS = 0.0  # Бонус для нового користувача (вимкнено)
    MIN_DEPOSIT = float(os.getenv('MIN_PAYMENT_USD', '10'))  # Мінімальний депозит в USD
    MAX_DEPOSIT = 100000  # Максимальний депозит в USD
    MIN_WITHDRAW = 10  # Мінімальне виведення в USD
    MAX_WITHDRAW = 50000  # Максимальне виведення в USD
    MIN_ORDER = 1  # Мінімальне замовлення в USD
    MAX_ORDER = 100000  # Максимальне замовлення в USD

    # Currency Settings
    DEFAULT_CURRENCY = 'USD'
    SUPPORTED_CURRENCIES = ['USD', 'UAH', 'EUR', 'USDT']
    EXCHANGE_RATES_UPDATE_INTERVAL = 3600  # 1 година

    # Logging - INFO для production
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')  # Завжди INFO для production, не DEBUG
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.getenv('LOG_FILE', 'teleboost.log')
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # Middleware Settings
    MIDDLEWARE_COMPRESSION_ENABLED = True
    MIDDLEWARE_COMPRESSION_LEVEL = 6  # 1-9 for gzip
    MIDDLEWARE_COMPRESSION_MIN_SIZE = 1024  # 1KB

    MIDDLEWARE_CACHE_ENABLED = True
    MIDDLEWARE_CACHE_DEFAULT_TIMEOUT = 300  # 5 хвилин

    MIDDLEWARE_PERFORMANCE_ENABLED = True
    MIDDLEWARE_PERFORMANCE_SLOW_REQUEST_THRESHOLD = 1.0  # 1 секунда

    MIDDLEWARE_RATE_LIMIT_BLACKLIST = os.getenv('RATE_LIMIT_BLACKLIST', '').split(',')
    MIDDLEWARE_RATE_LIMIT_WHITELIST = os.getenv('RATE_LIMIT_WHITELIST', '').split(',')

    # API Settings
    API_TIMEOUT = 30  # Секунди
    API_MAX_RETRIES = 3
    API_RETRY_DELAY = 1.0  # Секунди
    API_RETRY_BACKOFF = 2.0  # Множник затримки

    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    # File Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Session
    SESSION_COOKIE_NAME = 'teleboost_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_SAMESITE = 'None'  # Для Telegram Web App
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

    # Error Tracking (Sentry)
    SENTRY_DSN = os.getenv('SENTRY_DSN', '')
    SENTRY_ENVIRONMENT = ENV
    SENTRY_TRACES_SAMPLE_RATE = 0.1 if not DEBUG else 1.0

    # Feature Flags
    FEATURES = {
        'ORDERS_ENABLED': True,
        'PAYMENTS_ENABLED': True,
        'REFERRALS_ENABLED': True,
        'WITHDRAWALS_ENABLED': True,
        'SUBSCRIPTIONS_ENABLED': False,
        'ANALYTICS_ENABLED': True,
        'MAINTENANCE_MODE': False,
        'TWO_LEVEL_REFERRALS': True,  # Дворівнева реферальна система
    }

    # Email Settings (for future use)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@teleboost.com')

    # Background Jobs
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True

    @classmethod
    def validate(cls):
        """Перевірка обов'язкових налаштувань"""
        required = [
            ('SUPABASE_URL', cls.SUPABASE_URL),
            ('SUPABASE_SERVICE_KEY', cls.SUPABASE_SERVICE_KEY),
            ('TELEGRAM_BOT_TOKEN', cls.TELEGRAM_BOT_TOKEN),
            ('NAKRUTOCHKA_API_KEY', cls.NAKRUTOCHKA_API_KEY),
        ]

        # Payment providers - at least one required
        payment_providers = [
            ('CRYPTOBOT_TOKEN', cls.CRYPTOBOT_TOKEN),
            ('NOWPAYMENTS_API_KEY', cls.NOWPAYMENTS_API_KEY),
        ]

        missing = []
        for name, value in required:
            if not value:
                missing.append(name)

        # Check if at least one payment provider is configured
        if not any(value for _, value in payment_providers):
            missing.append('At least one payment provider')

        if missing:
            # Не виводимо конкретні назви змінних у production
            if cls.ENV == 'production':
                raise ValueError("Missing required environment variables")
            else:
                raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        # Validate URLs
        for url_name, url_value in [('BACKEND_URL', cls.BACKEND_URL), ('FRONTEND_URL', cls.FRONTEND_URL)]:
            if url_value and not url_value.startswith(('http://', 'https://')):
                raise ValueError(f"{url_name} must start with http:// or https://")

        return True

    @classmethod
    def to_dict(cls) -> dict:
        """Експорт конфігурації (без секретів)"""
        return {
            'ENV': cls.ENV,
            'DEBUG': cls.DEBUG,
            'BACKEND_URL': cls.BACKEND_URL,
            'FRONTEND_URL': cls.FRONTEND_URL,
            'API_URL': cls.API_URL,
            'APP_URL': cls.APP_URL,
            'BOT_USERNAME': cls.BOT_USERNAME,
            'REFERRAL_BONUS_PERCENT': cls.REFERRAL_BONUS_PERCENT,
            'REFERRAL_BONUS_LEVEL2_PERCENT': cls.REFERRAL_BONUS_LEVEL2_PERCENT,
            'REFERRAL_USER_BONUS': cls.REFERRAL_USER_BONUS,
            'MIN_DEPOSIT': cls.MIN_DEPOSIT,
            'MAX_DEPOSIT': cls.MAX_DEPOSIT,
            'MIN_WITHDRAW': cls.MIN_WITHDRAW,
            'MAX_WITHDRAW': cls.MAX_WITHDRAW,
            'MIN_ORDER': cls.MIN_ORDER,
            'MAX_ORDER': cls.MAX_ORDER,
            'DEFAULT_CURRENCY': cls.DEFAULT_CURRENCY,
            'SUPPORTED_CURRENCIES': cls.SUPPORTED_CURRENCIES,
            'FEATURES': cls.FEATURES,
            'DEFAULT_PAGE_SIZE': cls.DEFAULT_PAGE_SIZE,
            'MAX_PAGE_SIZE': cls.MAX_PAGE_SIZE,
            'CACHE_TTL': cls.CACHE_TTL,
            'PAYMENT_METHODS': cls.PAYMENT_METHODS,
            'USDT_TO_UAH_RATE': cls.USDT_TO_UAH_RATE,
        }

    @classmethod
    def get_webhook_url(cls, path: str) -> str:
        """Отримати повний URL для webhook"""
        return f"{cls.BACKEND_URL}{path}"

    @classmethod
    def is_feature_enabled(cls, feature: str) -> bool:
        """Перевірити чи увімкнена функція"""
        return cls.FEATURES.get(feature, False)

    @classmethod
    def is_payment_method_enabled(cls, method: str) -> bool:
        """Перевірити чи увімкнений метод оплати"""
        return method.lower() in [m.lower() for m in cls.PAYMENT_METHODS]

    @classmethod
    def get_withdrawal_address(cls, currency: str, network: str) -> Optional[str]:
        """Отримати адресу для виведення"""
        key = f"{currency}_{network}".upper()
        return cls.WITHDRAWAL_ADDRESSES.get(key)

    @classmethod
    def mask_sensitive_value(cls, value: str, visible_chars: int = 4) -> str:
        """Маскувати чутливе значення для безпечного виведення"""
        if not value or len(value) <= visible_chars * 2:
            return '***'
        return f"{value[:visible_chars]}...{value[-visible_chars:]}"


# Створюємо екземпляр конфігурації
config = Config()