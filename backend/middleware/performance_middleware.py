# backend/middleware/performance_middleware.py
"""
TeleBoost Performance Middleware
Advanced performance monitoring and profiling
"""
import time
import psutil
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict, deque
from flask import Flask, request, g, Response

from backend.utils.redis_client import redis_client
from backend.config import config

logger = logging.getLogger(__name__)


class PerformanceMiddleware:
    """
    Performance monitoring middleware with:
    - Request/response timing
    - Database query tracking
    - Memory usage monitoring
    - Slow request detection
    - Endpoint performance statistics
    - Resource usage alerts
    """

    # Slow request threshold (seconds)
    SLOW_REQUEST_THRESHOLD = 1.0

    # Very slow request threshold (seconds)
    VERY_SLOW_REQUEST_THRESHOLD = 3.0

    # Max history items per endpoint
    MAX_HISTORY = 1000

    def __init__(self, app: Flask):
        """Initialize performance middleware"""
        self.app = app

        # Performance data storage
        self.endpoint_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'min_time': float('inf'),
            'max_time': 0,
            'errors': 0,
            'slow_requests': 0,
            'history': deque(maxlen=self.MAX_HISTORY),
        })

        # System metrics
        self.system_metrics = {
            'start_time': time.time(),
            'requests_total': 0,
            'requests_active': 0,
            'peak_memory': 0,
            'peak_cpu': 0,
        }

        # Database query tracking
        self.db_queries = defaultdict(list)

        # Register handlers
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_request(self._teardown_request)

        logger.info("Performance middleware initialized")

    def _before_request(self) -> None:
        """Start performance tracking for request"""
        # Record start time
        g.start_time = time.time()
        g.start_memory = self._get_memory_usage()

        # Initialize query tracking
        g.db_queries = []
        g.cache_hits = 0
        g.cache_misses = 0

        # Increment active requests
        self.system_metrics['requests_active'] += 1
        self.system_metrics['requests_total'] += 1

        # Log request start in debug mode
        if config.DEBUG:
            logger.debug(
                f"Request started: {request.method} {request.path} "
                f"[Active: {self.system_metrics['requests_active']}]"
            )

    def _after_request(self, response: Response) -> Response:
        """Complete performance tracking and add headers"""
        if not hasattr(g, 'start_time'):
            return response

        # Calculate request duration
        duration = time.time() - g.start_time

        # Add performance headers
        response.headers['X-Response-Time'] = f"{duration:.3f}s"
        response.headers['X-Server-Memory'] = f"{self._get_memory_usage():.1f}MB"

        # Update endpoint statistics
        endpoint = request.endpoint or 'unknown'
        stats = self.endpoint_stats[endpoint]

        stats['count'] += 1
        stats['total_time'] += duration
        stats['min_time'] = min(stats['min_time'], duration)
        stats['max_time'] = max(stats['max_time'], duration)

        # Check for slow requests
        if duration > self.SLOW_REQUEST_THRESHOLD:
            stats['slow_requests'] += 1

            # Log slow request
            log_level = logging.WARNING
            if duration > self.VERY_SLOW_REQUEST_THRESHOLD:
                log_level = logging.ERROR

            logger.log(
                log_level,
                f"Slow request detected: {request.method} {request.path} "
                f"took {duration:.3f}s",
                extra={
                    'duration': duration,
                    'endpoint': endpoint,
                    'user_id': getattr(g, 'current_user', {}).get('id') if hasattr(g, 'current_user') else None,
                    'db_queries': len(getattr(g, 'db_queries', [])),
                }
            )

        # Track errors
        if response.status_code >= 400:
            stats['errors'] += 1

        # Add to history
        stats['history'].append({
            'timestamp': time.time(),
            'duration': duration,
            'status_code': response.status_code,
            'method': request.method,
            'memory_delta': self._get_memory_usage() - g.start_memory,
        })

        # Update system metrics
        current_memory = self._get_memory_usage()
        self.system_metrics['peak_memory'] = max(
            self.system_metrics['peak_memory'],
            current_memory
        )

        # Store metrics in Redis for distributed monitoring
        if endpoint != 'unknown':
            self._store_metrics(endpoint, duration, response.status_code)

        return response

    def _teardown_request(self, exception: Optional[Exception] = None) -> None:
        """Clean up after request"""
        # Decrement active requests
        self.system_metrics['requests_active'] = max(
            0,
            self.system_metrics['requests_active'] - 1
        )

        # Log exception if occurred
        if exception:
            logger.error(
                f"Request failed with exception: {exception}",
                extra={
                    'endpoint': request.endpoint,
                    'duration': time.time() - getattr(g, 'start_time', 0),
                }
            )

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except:
            return 0.0

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return psutil.cpu_percent(interval=0.1)
        except:
            return 0.0

    def _store_metrics(self, endpoint: str, duration: float, status_code: int) -> None:
        """Store metrics in Redis for distributed monitoring"""
        try:
            # Create metric key
            timestamp = int(time.time())
            minute_bucket = timestamp - (timestamp % 60)

            key = f"metrics:{endpoint}:{minute_bucket}"

            # Store metric
            metric = {
                'duration': duration,
                'status_code': status_code,
                'timestamp': timestamp,
            }

            # Add to sorted set
            redis_client.zadd(key, {json.dumps(metric): timestamp})

            # Expire after 1 hour
            redis_client.expire(key, 3600)

        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")

    def get_endpoint_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics for endpoint(s)

        Args:
            endpoint: Specific endpoint or None for all

        Returns:
            Performance statistics
        """
        if endpoint:
            stats = self.endpoint_stats.get(endpoint)
            if not stats:
                return {}

            return self._calculate_stats(stats)

        # Return stats for all endpoints
        all_stats = {}
        for ep, stats in self.endpoint_stats.items():
            all_stats[ep] = self._calculate_stats(stats)

        return all_stats

    def _calculate_stats(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate aggregate statistics"""
        if stats['count'] == 0:
            return {
                'count': 0,
                'average_time': 0,
                'min_time': 0,
                'max_time': 0,
                'error_rate': 0,
                'slow_request_rate': 0,
            }

        return {
            'count': stats['count'],
            'average_time': stats['total_time'] / stats['count'],
            'min_time': stats['min_time'],
            'max_time': stats['max_time'],
            'error_rate': stats['errors'] / stats['count'],
            'slow_request_rate': stats['slow_requests'] / stats['count'],
            'recent_performance': self._get_recent_performance(stats['history']),
        }

    def _get_recent_performance(self, history: deque, window: int = 60) -> Dict[str, Any]:
        """Get performance for recent time window (seconds)"""
        now = time.time()
        recent = [h for h in history if now - h['timestamp'] <= window]

        if not recent:
            return {}

        durations = [h['duration'] for h in recent]

        return {
            'requests': len(recent),
            'average_time': sum(durations) / len(durations),
            'max_time': max(durations),
            'errors': sum(1 for h in recent if h['status_code'] >= 400),
        }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics"""
        uptime = time.time() - self.system_metrics['start_time']

        return {
            'uptime_seconds': uptime,
            'uptime_readable': str(timedelta(seconds=int(uptime))),
            'requests_total': self.system_metrics['requests_total'],
            'requests_active': self.system_metrics['requests_active'],
            'requests_per_second': self.system_metrics['requests_total'] / uptime if uptime > 0 else 0,
            'memory_current_mb': self._get_memory_usage(),
            'memory_peak_mb': self.system_metrics['peak_memory'],
            'cpu_percent': self._get_cpu_usage(),
            'endpoint_count': len(self.endpoint_stats),
        }

    def get_slow_requests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest recent requests"""
        all_requests = []

        for endpoint, stats in self.endpoint_stats.items():
            for item in stats['history']:
                if item['duration'] > self.SLOW_REQUEST_THRESHOLD:
                    all_requests.append({
                        'endpoint': endpoint,
                        'duration': item['duration'],
                        'timestamp': item['timestamp'],
                        'status_code': item['status_code'],
                        'method': item['method'],
                    })

        # Sort by duration and return top N
        all_requests.sort(key=lambda x: x['duration'], reverse=True)
        return all_requests[:limit]

    def reset_stats(self) -> None:
        """Reset all performance statistics"""
        self.endpoint_stats.clear()
        self.system_metrics['requests_total'] = 0
        self.system_metrics['peak_memory'] = self._get_memory_usage()
        self.system_metrics['peak_cpu'] = self._get_cpu_usage()

        logger.info("Performance statistics reset")