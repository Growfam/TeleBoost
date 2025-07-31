# backend/middleware/__init__.py
"""
TeleBoost Middleware Package
High-performance middleware stack with proper ordering
"""
from typing import List, Callable
from flask import Flask

from backend.middleware.compression_middleware import CompressionMiddleware
from backend.middleware.cache_middleware import CacheMiddleware
from backend.middleware.performance_middleware import PerformanceMiddleware
from backend.middleware.auth_middleware import AuthMiddleware
from backend.middleware.rate_limit_middleware import RateLimitMiddleware
from backend.middleware.error_middleware import ErrorMiddleware

__all__ = [
    'init_middleware',
    'CompressionMiddleware',
    'CacheMiddleware',
    'PerformanceMiddleware',
    'AuthMiddleware',
    'RateLimitMiddleware',
    'ErrorMiddleware',
]


def init_middleware(app: Flask) -> None:
    """
    Initialize all middleware in the correct order

    Order matters! From outermost to innermost:
    1. Error handling (catch all exceptions)
    2. Performance monitoring (track everything)
    3. Compression (compress responses)
    4. Rate limiting (prevent abuse)
    5. Caching (serve cached responses)
    6. Authentication (validate users)

    Args:
        app: Flask application instance
    """
    # Error handling wraps everything
    error_middleware = ErrorMiddleware(app)

    # Performance monitoring
    performance_middleware = PerformanceMiddleware(app)

    # Response compression
    compression_middleware = CompressionMiddleware(app)

    # Rate limiting
    rate_limit_middleware = RateLimitMiddleware(app)

    # Response caching
    cache_middleware = CacheMiddleware(app)

    # Authentication
    auth_middleware = AuthMiddleware(app)

    # Store middleware instances on app for access
    app.middleware = {
        'error': error_middleware,
        'performance': performance_middleware,
        'compression': compression_middleware,
        'rate_limit': rate_limit_middleware,
        'cache': cache_middleware,
        'auth': auth_middleware,
    }

    # Log middleware initialization
    import logging
    logger = logging.getLogger(__name__)
    logger.info("✅ All middleware initialized successfully")