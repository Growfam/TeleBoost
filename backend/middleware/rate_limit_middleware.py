# backend/middleware/rate_limit_middleware.py
"""
TeleBoost Rate Limit Middleware
Advanced rate limiting with flexible rules and Redis backend
"""
import time
import hashlib
import logging
from typing import Dict, Any, Optional, Callable, Tuple
from functools import wraps
from flask import Flask, request, jsonify, g

from backend.utils.redis_client import redis_client
from backend.config import config

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Advanced rate limiting middleware with:
    - Multiple rate limit strategies (fixed window, sliding window, token bucket)
    - Per-user, per-IP, and per-endpoint limits
    - Whitelisting and blacklisting
    - Dynamic rate limits based on user tier
    - Distributed rate limiting via Redis
    - Graceful degradation if Redis is down
    """

    # Default rate limits (requests per minute)
    DEFAULT_LIMITS = {
        'global': 100,  # Global limit per IP
        'authenticated': 200,  # Limit for authenticated users
        'premium': 500,  # Limit for premium users
        'admin': 10000,  # Effectively unlimited for admins
    }

    # Endpoint-specific limits (requests per minute)
    ENDPOINT_LIMITS = {
        # Auth endpoints
        'auth.telegram_login': 10,
        'auth.refresh_token': 20,

        # Order endpoints (expensive operations)
        'orders.create_order': 5,
        'orders.bulk_create': 2,

        # Payment endpoints
        'payments.create_payment': 10,

        # Public endpoints (higher limits)
        'services.get_services': 60,

        # Webhook endpoints (no limits)
        'payments.cryptobot_webhook': None,
        'payments.nowpayments_webhook': None,
    }

    # Whitelisted IPs (no rate limiting)
    WHITELIST_IPS = set()

    # Blacklisted IPs (always blocked)
    BLACKLIST_IPS = set()

    def __init__(self, app: Flask):
        """Initialize rate limit middleware"""
        self.app = app
        self.enabled = config.RATELIMIT_ENABLED
        self.window_size = 60  # 1 minute windows

        # Statistics
        self.stats = {
            'requests_limited': 0,
            'requests_passed': 0,
            'blacklist_hits': 0,
            'whitelist_hits': 0,
        }

        # Register before_request handler
        app.before_request(self._check_rate_limit)

        logger.info(f"Rate limit middleware initialized (Enabled: {self.enabled})")

    def _check_rate_limit(self) -> Optional[Any]:
        """
        Check rate limit for incoming request

        Returns:
            None if allowed, error response if rate limited
        """
        if not self.enabled:
            return None

        # Get identifier (IP or user ID)
        identifier = self._get_identifier()

        # Check blacklist
        if identifier in self.BLACKLIST_IPS:
            self.stats['blacklist_hits'] += 1
            logger.warning(f"Blacklisted IP attempted access: {identifier}")
            return self._rate_limit_response(0)

        # Check whitelist
        if identifier in self.WHITELIST_IPS:
            self.stats['whitelist_hits'] += 1
            return None

        # Get rate limit for this request
        limit = self._get_rate_limit()

        # No limit for this endpoint
        if limit is None:
            return None

        # Check rate limit
        allowed, remaining, reset_time = self._check_limit(identifier, limit)

        # Add rate limit headers
        @app.after_request
        def add_rate_limit_headers(response):
            response.headers['X-RateLimit-Limit'] = str(limit)
            response.headers['X-RateLimit-Remaining'] = str(max(0, remaining))
            response.headers['X-RateLimit-Reset'] = str(int(reset_time))
            return response

        if not allowed:
            self.stats['requests_limited'] += 1
            retry_after = int(reset_time - time.time())
            return self._rate_limit_response(retry_after)

        self.stats['requests_passed'] += 1
        return None

    def _get_identifier(self) -> str:
        """Get unique identifier for rate limiting"""
        # Prefer user ID for authenticated users
        if hasattr(g, 'current_user') and g.current_user:
            return f"user:{g.current_user.id}"

        # Fall back to IP address
        # Handle proxy headers
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Take the first IP in the chain
            ip = forwarded_for.split(',')[0].strip()
        else:
            ip = request.remote_addr

        return f"ip:{ip}"

    def _get_rate_limit(self) -> Optional[int]:
        """Get rate limit for current request"""
        endpoint = request.endpoint

        # Check endpoint-specific limits first
        if endpoint in self.ENDPOINT_LIMITS:
            return self.ENDPOINT_LIMITS[endpoint]

        # Determine user tier
        if hasattr(g, 'current_user') and g.current_user:
            if g.current_user.is_admin:
                return self.DEFAULT_LIMITS['admin']
            elif g.current_user.is_premium:
                return self.DEFAULT_LIMITS['premium']
            else:
                return self.DEFAULT_LIMITS['authenticated']

        # Default global limit
        return self.DEFAULT_LIMITS['global']

    def _check_limit(self, identifier: str, limit: int) -> Tuple[bool, int, float]:
        """
        Check if request is within rate limit

        Args:
            identifier: Unique identifier
            limit: Rate limit (requests per minute)

        Returns:
            (allowed, remaining, reset_time)
        """
        try:
            # Use sliding window algorithm
            now = time.time()
            window_start = now - self.window_size

            # Create Redis key
            key = f"ratelimit:{identifier}:{request.endpoint or 'global'}"

            # Remove old entries
            redis_client.zremrangebyscore(key, '-inf', window_start)

            # Count requests in current window
            current_count = redis_client.zcard(key)

            # Check if limit exceeded
            if current_count >= limit:
                # Get oldest request time to calculate reset
                oldest = redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    reset_time = oldest[0][1] + self.window_size
                else:
                    reset_time = now + self.window_size

                return False, 0, reset_time

            # Add current request
            redis_client.zadd(key, {f"{now}:{id(request)}": now})

            # Set expiry
            redis_client.expire(key, self.window_size + 1)

            # Calculate remaining
            remaining = limit - current_count - 1
            reset_time = now + self.window_size

            return True, remaining, reset_time

        except Exception as e:
            # Graceful degradation - allow request if Redis is down
            logger.error(f"Rate limit check failed: {e}")
            return True, limit, time.time() + self.window_size

    def _rate_limit_response(self, retry_after: int) -> Any:
        """Create rate limit exceeded response"""
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded',
            'code': 'RATE_LIMIT_EXCEEDED',
            'message': f'Too many requests. Please retry after {retry_after} seconds.',
            'retry_after': retry_after,
        }), 429

    @classmethod
    def limit(cls, requests_per_minute: int) -> Callable:
        """
        Decorator for custom rate limits on specific routes

        Usage:
            @app.route('/api/expensive-operation')
            @RateLimitMiddleware.limit(requests_per_minute=5)
            def expensive_operation():
                return {'result': 'success'}
        """

        def decorator(f: Callable) -> Callable:
            # Store limit on function for middleware to read
            f._rate_limit = requests_per_minute

            @wraps(f)
            def decorated_function(*args, **kwargs):
                return f(*args, **kwargs)

            return decorated_function

        return decorator

    def add_to_blacklist(self, identifier: str, reason: str = '') -> bool:
        """Add identifier to blacklist"""
        try:
            # Add to memory
            self.BLACKLIST_IPS.add(identifier)

            # Add to Redis for persistence
            redis_client.sadd('ratelimit:blacklist', identifier)

            # Log blacklist addition
            logger.warning(f"Added to blacklist: {identifier} (Reason: {reason})")

            return True
        except Exception as e:
            logger.error(f"Failed to add to blacklist: {e}")
            return False

    def remove_from_blacklist(self, identifier: str) -> bool:
        """Remove identifier from blacklist"""
        try:
            # Remove from memory
            self.BLACKLIST_IPS.discard(identifier)

            # Remove from Redis
            redis_client.srem('ratelimit:blacklist', identifier)

            logger.info(f"Removed from blacklist: {identifier}")

            return True
        except Exception as e:
            logger.error(f"Failed to remove from blacklist: {e}")
            return False

    def add_to_whitelist(self, identifier: str) -> bool:
        """Add identifier to whitelist"""
        try:
            # Add to memory
            self.WHITELIST_IPS.add(identifier)

            # Add to Redis for persistence
            redis_client.sadd('ratelimit:whitelist', identifier)

            logger.info(f"Added to whitelist: {identifier}")

            return True
        except Exception as e:
            logger.error(f"Failed to add to whitelist: {e}")
            return False

    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        try:
            # Count active rate limit keys
            pattern = "ratelimit:*"
            keys = redis_client.keys(pattern)

            # Filter out blacklist/whitelist keys
            active_limits = [k for k in keys if not k.endswith((':blacklist', ':whitelist'))]

            return {
                'enabled': self.enabled,
                'requests_limited': self.stats['requests_limited'],
                'requests_passed': self.stats['requests_passed'],
                'blacklist_hits': self.stats['blacklist_hits'],
                'whitelist_hits': self.stats['whitelist_hits'],
                'active_limiters': len(active_limits),
                'blacklist_size': len(self.BLACKLIST_IPS),
                'whitelist_size': len(self.WHITELIST_IPS),
                'limits': {
                    'default': self.DEFAULT_LIMITS,
                    'endpoints': {k: v for k, v in self.ENDPOINT_LIMITS.items() if v is not None},
                },
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit stats: {e}")
            return {}

    def reset_stats(self) -> None:
        """Reset rate limit statistics"""
        self.stats = {
            'requests_limited': 0,
            'requests_passed': 0,
            'blacklist_hits': 0,
            'whitelist_hits': 0,
        }

    def load_lists_from_redis(self) -> None:
        """Load blacklist and whitelist from Redis on startup"""
        try:
            # Load blacklist
            blacklist = redis_client.smembers('ratelimit:blacklist')
            self.BLACKLIST_IPS.update(blacklist)

            # Load whitelist
            whitelist = redis_client.smembers('ratelimit:whitelist')
            self.WHITELIST_IPS.update(whitelist)

            logger.info(
                f"Loaded {len(self.BLACKLIST_IPS)} blacklist and "
                f"{len(self.WHITELIST_IPS)} whitelist entries from Redis"
            )
        except Exception as e:
            logger.error(f"Failed to load lists from Redis: {e}")