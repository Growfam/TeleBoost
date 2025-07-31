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
    DEBUG = ENV == 'development'
    TESTING = ENV == 'testing'

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'teleboost-secret-key-change-in-production')

    # Railway
    PORT = int(os.getenv('PORT', 5000))
    HOST = '0.0.0.0'  # Railway вимагає 0.0.0.0

    # URLs
    BACKEND_URL = os.getenv('BACKEND_URL', 'https://teleboost-teleboost.up.railway.app')
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://teleboost-teleboost.up.railway.app')

    # Database - Supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')

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
    }

    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    BOT_USERNAME = os.getenv('BOT_USERNAME', 'TeleBoostBot')

    # JWT Settings
    JWT_SECRET = os.getenv('JWT_SECRET', SECRET_KEY)
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Nakrutochka API
    NAKRUTOCHKA_API_URL = os.getenv('NAKRUTOCHKA_API_URL', 'https://nakrutochka.com/api/v2')
    NAKRUTOCHKA_API_KEY = os.getenv('NAKRUTOCHKA_API_KEY', '')

    # CryptoBot
    CRYPTOBOT_TOKEN = os.getenv('CRYPTOBOT_TOKEN', '')
    CRYPTOBOT_WEBHOOK_PATH = '/api/webhooks/cryptobot'
    CRYPTOBOT_NETWORK = 'mainnet'  # або 'testnet' для тестування

    # NOWPayments
    NOWPAYMENTS_API_KEY = os.getenv('NOWPAYMENTS_API_KEY', '')
    NOWPAYMENTS_IPN_SECRET = os.getenv('NOWPAYMENTS_IPN_SECRET', '')
    NOWPAYMENTS_WEBHOOK_PATH = '/api/webhooks/nowpayments'

    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_HEADERS_ENABLED = True

    # CORS
    CORS_ORIGINS = [
        "https://web.telegram.org",
        "https://telegram.org",
        FRONTEND_URL,
        "http://localhost:3000",  # для розробки
    ]

    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    }

    # Business Logic
    REFERRAL_BONUS_PERCENT = 10.0  # 10% для реферера
    REFERRAL_USER_BONUS = 5.0  # 5% для нового користувача
    MIN_DEPOSIT = 100  # Мінімальний депозит
    MIN_ORDER = 10  # Мінімальне замовлення

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO' if not DEBUG else 'DEBUG')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    @classmethod
    def validate(cls):
        """Перевірка обов'язкових налаштувань"""
        required = [
            ('SUPABASE_URL', cls.SUPABASE_URL),
            ('SUPABASE_SERVICE_KEY', cls.SUPABASE_SERVICE_KEY),
            ('TELEGRAM_BOT_TOKEN', cls.TELEGRAM_BOT_TOKEN),
            ('NAKRUTOCHKA_API_KEY', cls.NAKRUTOCHKA_API_KEY),
            ('CRYPTOBOT_TOKEN', cls.CRYPTOBOT_TOKEN),
        ]

        missing = []
        for name, value in required:
            if not value:
                missing.append(name)

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return True

    @classmethod
    def to_dict(cls) -> dict:
        """Експорт конфігурації (без секретів)"""
        return {
            'ENV': cls.ENV,
            'DEBUG': cls.DEBUG,
            'BACKEND_URL': cls.BACKEND_URL,
            'FRONTEND_URL': cls.FRONTEND_URL,
            'BOT_USERNAME': cls.BOT_USERNAME,
            'REFERRAL_BONUS_PERCENT': cls.REFERRAL_BONUS_PERCENT,
            'MIN_DEPOSIT': cls.MIN_DEPOSIT,
            'MIN_ORDER': cls.MIN_ORDER,
        }


# Створюємо екземпляр конфігурації
config = Config()