# backend/middleware/auth_middleware.py
"""
TeleBoost Authentication Middleware
High-performance JWT validation with caching
FIXED: Додано правильні публічні ендпоінти для login та splash
"""
import logging
from functools import wraps
from typing import Optional, Callable, Set, Dict, Any
from flask import Flask, request, jsonify, g

from backend.auth.jwt_handler import decode_token, get_current_user_id
from backend.auth.models import User
from backend.utils.redis_client import redis_client
from backend.utils.constants import CACHE_KEYS

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """
    Authentication middleware with optimizations:
    - Token caching to avoid repeated decoding
    - User data caching
    - Public endpoints whitelist
    - Optional authentication support
    """

    # Public endpoints that don't require authentication
    PUBLIC_ENDPOINTS = {
        # Base routes
        'index', 'health_check', 'api_status', 'ping', 'get_public_config',

        # Auth routes
        'auth.telegram_login', 'auth.refresh_token', 'auth.verify_token', 'auth.auth_status',

        # Payment webhooks
        'payments.cryptobot_webhook', 'payments.nowpayments_webhook',

        # Static files
        'static',

        # Frontend routes - ВСІ ПУБЛІЧНІ
        'root', 'splash_page', 'login_page', 'home_page',
        'serve_frontend', 'serve_shared', 'serve_pages',
        'serve_js', 'serve_css', 'serve_component',

        # Додаткові frontend роути
        'serve_splash', 'serve_login', 'serve_home',

        # Frontend assets
        'serve_assets', 'serve_images', 'serve_fonts',

        # API routes - БАЗОВІ ПУБЛІЧНІ
        'api_index', 'api.get_public_config',
        'statistics.live_statistics',

        # Services - публічний доступ для перегляду
        'services.get_services', 'services.get_service',
        'services.get_categories',

        # Public pages
        'about_page', 'terms_page', 'privacy_page',
        'faq_page', 'contact_page',
    }

    # URL patterns that should be public (prefix matching)
    PUBLIC_URL_PATTERNS = [
        '/splash',
        '/login',
        '/about',
        '/terms',
        '/privacy',
        '/faq',
        '/contact',
        '/api/auth/telegram',
        '/api/auth/status',
        '/api/auth/verify',
        '/api/config',
        '/api/health',
        '/api/ping',
        '/frontend/',
        '/static/',
        '/assets/',
        '/images/',
        '/fonts/',
        '/favicon',
        '/.well-known/',
    ]

    # Endpoints with optional authentication
    OPTIONAL_AUTH_ENDPOINTS = {
        'services.get_services',  # Can see services without login
        'services.get_service',
        'auth.verify_token',  # Can check token validity
        'api.get_config',  # Can get public config
    }

    def __init__(self, app: Flask):
        """Initialize authentication middleware"""
        self.app = app
        self.token_cache_ttl = 300  # 5 minutes
        self.user_cache_ttl = 60  # 1 minute

        # Register before_request handler
        app.before_request(self._authenticate_request)

        logger.info("✅ Authentication middleware initialized")
        logger.info(f"📋 Public endpoints: {len(self.PUBLIC_ENDPOINTS)}")
        logger.info(f"📋 Public URL patterns: {len(self.PUBLIC_URL_PATTERNS)}")

    def _is_public_path(self, path: str) -> bool:
        """Check if path matches any public pattern"""
        # Normalize path
        path = path.rstrip('/')

        # Check exact patterns
        for pattern in self.PUBLIC_URL_PATTERNS:
            if path.startswith(pattern):
                return True

        # Check if it's a file request (has extension)
        if '.' in path.split('/')[-1]:
            # Allow all static files
            if any(path.startswith(p) for p in ['/frontend/', '/static/', '/assets/']):
                return True

        return False

    def _authenticate_request(self) -> Optional[Any]:
        """
        Authenticate incoming request

        Returns:
            None if successful, error response if failed
        """
        # Логування для дебагу
        logger.debug(f"🔍 Auth check for endpoint: {request.endpoint}, path: {request.path}, method: {request.method}")

        # Skip authentication for public endpoints
        if request.endpoint in self.PUBLIC_ENDPOINTS:
            logger.debug(f"✅ Endpoint {request.endpoint} is public, skipping auth")
            return None
            # Check URL patterns FIRST (before endpoint check)
        if self._is_public_path(request.path):
            logger.debug(f"✅ Path {request.path} matches public pattern, skipping auth")
            return None

        # Check URL patterns
        if self._is_public_path(request.path):
            logger.debug(f"✅ Path {request.path} matches public pattern, skipping auth")
            return None

        # Skip for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            logger.debug("✅ OPTIONS request, skipping auth")
            return None

        # Extract token from header
        auth_header = request.headers.get('Authorization', '')

        # Check if endpoint has optional auth
        if request.endpoint in self.OPTIONAL_AUTH_ENDPOINTS:
            if not auth_header:
                # No token provided, continue without auth
                g.current_user = None
                g.jwt_payload = None
                logger.debug(f"📝 Optional auth endpoint {request.endpoint}, no token provided")
                return None

        # For protected endpoints, token is required
        if not auth_header:
            logger.warning(f"❌ Missing authorization header for protected endpoint: {request.endpoint}")
            logger.warning(f"   Path: {request.path}")
            return self._unauthorized_response('Missing authorization header')

        # Validate Bearer format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != 'Bearer':
            logger.warning(f"❌ Invalid auth header format: {auth_header[:30]}...")
            return self._unauthorized_response('Invalid authorization header format')

        token = parts[1]
        logger.debug(f"🔑 Token extracted, length: {len(token)}")

        # Try to get cached token validation
        cached_result = self._get_cached_token_validation(token)
        if cached_result is not None:
            if cached_result['valid']:
                # Set user context from cache
                g.current_user = cached_result['user']
                g.jwt_payload = cached_result['payload']
                logger.debug(f"✅ Token validated from cache for user {cached_result['user'].telegram_id}")
                return None
            else:
                logger.warning("❌ Cached token validation failed")
                return self._unauthorized_response('Invalid token')

        # Validate token
        logger.debug("🔐 Validating token...")
        is_valid, payload = decode_token(token)

        if not is_valid or not payload:
            # Cache negative result
            self._cache_token_validation(token, False)
            logger.warning("❌ Token validation failed")
            return self._unauthorized_response('Invalid or expired token')

        # Check token type
        if payload.get('type') != 'access':
            self._cache_token_validation(token, False)
            logger.warning(f"❌ Invalid token type: {payload.get('type')}")
            return self._unauthorized_response('Invalid token type')

        # Get user data
        user = self._get_user_with_cache(payload['user_id'])

        if not user:
            self._cache_token_validation(token, False)
            logger.warning(f"❌ User not found: {payload['user_id']}")
            return self._unauthorized_response('User not found')

        if not user.is_active:
            self._cache_token_validation(token, False)
            logger.warning(f"❌ User inactive: {user.telegram_id}")
            return self._unauthorized_response('User account is inactive')

        # Cache successful validation
        self._cache_token_validation(token, True, user, payload)

        # Set user context
        g.current_user = user
        g.jwt_payload = payload

        logger.debug(f"✅ Authentication successful for user {user.telegram_id}")

        return None

    def _get_cached_token_validation(self, token: str) -> Optional[Dict[str, Any]]:
        """Get cached token validation result"""
        try:
            # Hash token for cache key (security)
            import hashlib
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
            cache_key = f"auth:token:{token_hash}"

            return redis_client.get(cache_key, data_type='json')
        except Exception as e:
            logger.error(f"❌ Error getting cached token validation: {e}")
            return None

    def _cache_token_validation(self, token: str, valid: bool,
                                user: Optional[User] = None,
                                payload: Optional[Dict] = None) -> None:
        """Cache token validation result"""
        try:
            import hashlib
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
            cache_key = f"auth:token:{token_hash}"

            cache_data = {
                'valid': valid,
                'user': user.to_dict() if user else None,
                'payload': payload,
                'cached_at': time.time()
            }

            redis_client.set(cache_key, cache_data, ttl=self.token_cache_ttl)
            logger.debug(f"📝 Cached token validation: valid={valid}")
        except Exception as e:
            logger.error(f"❌ Error caching token validation: {e}")

    def _get_user_with_cache(self, user_id: str) -> Optional[User]:
        """Get user with caching"""
        try:
            # Try cache first
            cache_key = CACHE_KEYS.format(CACHE_KEYS.USER, user_id=user_id)
            cached_user = redis_client.get(cache_key, data_type='json')

            if cached_user:
                logger.debug(f"📦 User loaded from cache: {user_id}")
                return User(cached_user)

            # Get from database
            user = User.get_by_id(user_id)

            if user:
                # Cache user data
                redis_client.set(cache_key, user.to_dict(), ttl=self.user_cache_ttl)
                logger.debug(f"💾 User cached: {user_id}")

            return user
        except Exception as e:
            logger.error(f"❌ Error getting user with cache: {e}")
            return None

    def _unauthorized_response(self, message: str) -> Any:
        """Create unauthorized response"""
        return jsonify({
            'success': False,
            'error': message,
            'code': 'UNAUTHORIZED'
        }), 401

    @classmethod
    def require_auth(cls, f: Callable) -> Callable:
        """
        Decorator to require authentication for specific route

        Usage:
            @app.route('/protected')
            @AuthMiddleware.require_auth
            def protected_route():
                user = g.current_user
                return {'user_id': user.id}
        """

        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user') or g.current_user is None:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }), 401
            return f(*args, **kwargs)

        return decorated_function

    @classmethod
    def require_admin(cls, f: Callable) -> Callable:
        """
        Decorator to require admin privileges

        Usage:
            @app.route('/admin/users')
            @AuthMiddleware.require_admin
            def admin_users():
                return {'users': []}
        """

        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user') or g.current_user is None:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }), 401

            if not g.current_user.is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required',
                    'code': 'ADMIN_REQUIRED'
                }), 403

            return f(*args, **kwargs)

        return decorated_function

    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        try:
            pattern = "auth:token:*"
            cached_tokens = len(redis_client.keys(pattern))

            return {
                'cached_tokens': cached_tokens,
                'cache_ttl': self.token_cache_ttl,
                'public_endpoints': len(self.PUBLIC_ENDPOINTS),
                'public_patterns': len(self.PUBLIC_URL_PATTERNS),
                'optional_auth_endpoints': len(self.OPTIONAL_AUTH_ENDPOINTS),
            }
        except Exception as e:
            logger.error(f"❌ Error getting auth stats: {e}")
            return {}

    def add_public_endpoint(self, endpoint: str) -> None:
        """Add endpoint to public list"""
        self.PUBLIC_ENDPOINTS.add(endpoint)
        logger.info(f"➕ Added public endpoint: {endpoint}")

    def add_public_pattern(self, pattern: str) -> None:
        """Add URL pattern to public list"""
        self.PUBLIC_URL_PATTERNS.append(pattern)
        logger.info(f"➕ Added public pattern: {pattern}")

    def remove_public_endpoint(self, endpoint: str) -> None:
        """Remove endpoint from public list"""
        if endpoint in self.PUBLIC_ENDPOINTS:
            self.PUBLIC_ENDPOINTS.remove(endpoint)
            logger.info(f"➖ Removed public endpoint: {endpoint}")

    def is_public_endpoint(self, endpoint: str = None, path: str = None) -> bool:
        """Check if endpoint or path is public"""
        if endpoint and endpoint in self.PUBLIC_ENDPOINTS:
            return True

        if path and self._is_public_path(path):
            return True

        return False


# Import time module
import time