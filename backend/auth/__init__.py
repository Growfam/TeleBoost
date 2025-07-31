# backend/auth/__init__.py
"""
TeleBoost Auth Package
Авторизація через Telegram Web App
"""

# Імпортуємо для зручного доступу
from backend.auth.telegram_auth import verify_telegram_data
from backend.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    create_tokens_pair,
    decode_token,
    revoke_token
)
from backend.auth.decorators import jwt_required, admin_required
from backend.auth.models import User, UserSession

__all__ = [
    # Telegram auth
    'verify_telegram_data',

    # JWT
    'create_access_token',
    'create_refresh_token',
    'create_tokens_pair',
    'decode_token',
    'revoke_token',

    # Decorators
    'jwt_required',
    'admin_required',

    # Models
    'User',
    'UserSession',
]