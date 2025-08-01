# backend/users/__init__.py
"""
TeleBoost Users Module
Система управління користувачами
"""

# Models
from backend.users.models import (
    UserProfile,
    UserSettings,
    UserActivity,
    UserNotification
)

# Services
from backend.users.services import (
    UserService,
    UserTransactionService
)

# Routes
from backend.users.routes import users_bp

__all__ = [
    # Models
    'UserProfile',
    'UserSettings',
    'UserActivity',
    'UserNotification',

    # Services
    'UserService',
    'UserTransactionService',

    # Blueprint
    'users_bp',
]

__version__ = '1.0.0'
__module_name__ = 'TeleBoost Users System'