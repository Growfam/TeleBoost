# backend/api/__init__.py
"""
TeleBoost API Package
External API integrations and error handling
"""

from backend.api.nakrutochka_api import nakrutochka, NakrutochkaAPI
from backend.api.error_handlers import (
    APIError,
    RateLimitError,
    AuthenticationError,
    ServiceUnavailableError,
    handle_api_error,
    retry_on_error,
)

__all__ = [
    # Nakrutochka client
    'nakrutochka',
    'NakrutochkaAPI',

    # Error classes
    'APIError',
    'RateLimitError',
    'AuthenticationError',
    'ServiceUnavailableError',

    # Error handlers
    'handle_api_error',
    'retry_on_error',
]