# backend/middleware/cache_middleware.py
"""
TeleBoost Cache Middleware
Intelligent response caching with ETags and conditional requests
"""
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable, Set
from flask import Flask, request, make_response, Response, g

from backend.utils.redis_client import redis_client
from backend.config import config

logger = logging.getLogger(__name__)


class CacheMiddleware:
    """
    Advanced caching middleware with:
    - ETag support for conditional requests
    - Vary header support
    - Cache invalidation strategies
    - User-specific and public caches
    - Automatic cache key generation
    """

    # Endpoints to cache with TTL in seconds
    CACHE_CONFIG = {
        # Public caches (same for all users)
        'services.get_services': {
            'ttl': 3600,  # 1 hour
            'public': True,
            'vary': ['Accept-Language'],
        },
        'services.get_service': {
            'ttl': 3600,  # 1 hour
            'public': True,
            'vary': [],
        },
        'api_status': {
            'ttl': 60,  # 1 minute
            'public': True,
            'vary': [],
        },

        # User-specific caches
        'users.get_balance': {
            'ttl': 30,  # 30 seconds
            'public': False,
            'vary': [],
        },
        'users.get_transactions': {
            'ttl': 60,  # 1 minute
            'public': False,
            'vary': ['page', 'limit'],
        },
        'orders.get_orders': {
            'ttl': 60,  # 1 minute
            'public': False,
            'vary': ['status', 'page', 'limit'],
        },
        'referrals.referral_stats': {
            'ttl': 300,  # 5 minutes
            'public': False,
            'vary': [],
        },
    }

    # Methods that should never be cached
    NEVER_CACHE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

    def __init__(self, app: Flask):
        """Initialize cache middleware"""
        self.app = app
        self.cache_prefix = 'response:'
        self.etag_prefix = 'etag:'

        # Register handlers
        app.before_request(self._before_request)
        app.after_request(self._after_request)

        logger.info("Cache middleware initialized")

    def _before_request(self) -> Optional[Response]:
        """
        Check cache before processing request

        Returns:
            Cached response if available and valid, None otherwise
        """
        # Skip caching for non-cacheable methods
        if request.method in self.NEVER_CACHE_METHODS:
            return None

        # Check if endpoint is cacheable
        cache_config = self.CACHE_CONFIG.get(request.endpoint)
        if not cache_config:
            return None

        # Generate cache key
        cache_key = self._generate_cache_key(cache_config)
        if not cache_key:
            return None

        # Check for conditional request headers
        if_none_match = request.headers.get('If-None-Match')
        if_modified_since = request.headers.get('If-Modified-Since')

        # Try to get cached response
        cached_data = redis_client.get(cache_key, data_type='json')

        if cached_data:
            # Check if cache is still valid
            if time.time() > cached_data.get('expires_at', 0):
                # Cache expired, delete it
                redis_client.delete(cache_key)
                return None

            # Handle conditional requests
            if if_none_match and if_none_match == cached_data.get('etag'):
                # Return 304 Not Modified
                response = make_response('', 304)
                response.headers['ETag'] = cached_data['etag']
                response.headers['Cache-Control'] = cached_data.get('cache_control', '')

                # Log cache hit
                logger.debug(f"Cache hit (304) for {request.endpoint}")
                return response

            # Return cached response
            response = make_response(
                cached_data['body'],
                cached_data['status_code']
            )

            # Restore headers
            for header, value in cached_data.get('headers', {}).items():
                response.headers[header] = value

            # Add cache headers
            response.headers['X-Cache'] = 'HIT'
            response.headers['X-Cache-Key'] = cache_key

            # Log cache hit
            logger.debug(f"Cache hit for {request.endpoint}")

            return response

        # Store cache key for after_request
        g.cache_key = cache_key
        g.cache_config = cache_config

        return None

    def _after_request(self, response: Response) -> Response:
        """
        Cache response after processing

        Args:
            response: Flask response object

        Returns:
            Modified response with cache headers
        """
        # Only cache successful GET requests
        if request.method != 'GET' or response.status_code != 200:
            return response

        # Check if we should cache this response
        if not hasattr(g, 'cache_key') or not hasattr(g, 'cache_config'):
            return response

        cache_key = g.cache_key
        cache_config = g.cache_config

        # Don't cache if response has no-cache directive
        if 'no-cache' in response.headers.get('Cache-Control', ''):
            return response

        # Generate ETag
        etag = self._generate_etag(response)
        response.headers['ETag'] = etag

        # Set cache headers
        max_age = cache_config['ttl']
        if cache_config['public']:
            cache_control = f'public, max-age={max_age}'
        else:
            cache_control = f'private, max-age={max_age}'

        response.headers['Cache-Control'] = cache_control
        response.headers['X-Cache'] = 'MISS'

        # Prepare data for caching
        cache_data = {
            'body': response.get_data(as_text=True),
            'status_code': response.status_code,
            'headers': {
                'Content-Type': response.content_type,
                'ETag': etag,
                'Cache-Control': cache_control,
            },
            'etag': etag,
            'cache_control': cache_control,
            'created_at': time.time(),
            'expires_at': time.time() + cache_config['ttl'],
        }

        # Add Vary headers if configured
        if cache_config.get('vary'):
            vary_header = ', '.join(cache_config['vary'])
            response.headers['Vary'] = vary_header
            cache_data['headers']['Vary'] = vary_header

        # Cache the response
        redis_client.set(cache_key, cache_data, ttl=cache_config['ttl'])

        logger.debug(f"Cached response for {request.endpoint} with key {cache_key}")

        return response

    def _generate_cache_key(self, cache_config: Dict[str, Any]) -> Optional[str]:
        """Generate cache key based on request and configuration"""
        try:
            parts = [
                self.cache_prefix,
                request.endpoint,
            ]

            # Add user ID for private caches
            if not cache_config['public']:
                if hasattr(g, 'current_user') and g.current_user:
                    parts.append(f"user:{g.current_user.id}")
                else:
                    # Can't cache user-specific response without user
                    return None

            # Add vary parameters
            for param in cache_config.get('vary', []):
                if param in request.args:
                    parts.append(f"{param}:{request.args.get(param)}")
                elif param in request.headers:
                    parts.append(f"{param}:{request.headers.get(param)}")

            # Add query parameters for cache key
            if request.args:
                # Sort query params for consistent keys
                sorted_params = sorted(request.args.items())
                query_hash = hashlib.md5(
                    json.dumps(sorted_params).encode()
                ).hexdigest()[:8]
                parts.append(f"query:{query_hash}")

            return ':'.join(parts)

        except Exception as e:
            logger.error(f"Error generating cache key: {e}")
            return None

    def _generate_etag(self, response: Response) -> str:
        """Generate ETag for response"""
        # Create hash of response content
        content = response.get_data(as_text=True)
        etag_data = f"{content}:{response.status_code}:{response.content_type}"

        etag_hash = hashlib.sha256(etag_data.encode()).hexdigest()[:16]
        return f'W/"{etag_hash}"'  # Weak ETag

    def invalidate_cache(self, pattern: Optional[str] = None,
                         user_id: Optional[str] = None,
                         endpoint: Optional[str] = None) -> int:
        """
        Invalidate cached responses

        Args:
            pattern: Redis key pattern to match
            user_id: Invalidate all caches for specific user
            endpoint: Invalidate all caches for specific endpoint

        Returns:
            Number of keys deleted
        """
        try:
            if pattern:
                keys = redis_client.keys(pattern)
            elif user_id:
                pattern = f"{self.cache_prefix}*user:{user_id}*"
                keys = redis_client.keys(pattern)
            elif endpoint:
                pattern = f"{self.cache_prefix}{endpoint}*"
                keys = redis_client.keys(pattern)
            else:
                # Clear all response cache
                pattern = f"{self.cache_prefix}*"
                keys = redis_client.keys(pattern)

            if keys:
                deleted = redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            pattern = f"{self.cache_prefix}*"
            keys = redis_client.keys(pattern)

            public_count = 0
            private_count = 0

            for key in keys:
                if 'user:' in key:
                    private_count += 1
                else:
                    public_count += 1

            return {
                'total_cached': len(keys),
                'public_cached': public_count,
                'private_cached': private_count,
                'cache_endpoints': len(self.CACHE_CONFIG),
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}