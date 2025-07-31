# backend/middleware/error_middleware.py
"""
TeleBoost Error Middleware
Centralized error handling with detailed logging and user-friendly responses
"""
import logging
import traceback
import sys
from typing import Dict, Any, Optional, Tuple
from werkzeug.exceptions import HTTPException
from flask import Flask, request, jsonify, g
from datetime import datetime

from backend.config import config
from backend.utils.constants import ERROR_MESSAGES

logger = logging.getLogger(__name__)


class ErrorMiddleware:
    """
    Comprehensive error handling middleware with:
    - Structured error responses
    - Detailed logging with context
    - User-friendly error messages
    - Development vs production modes
    - Error tracking integration ready
    - Request context preservation
    """

    # Map HTTP status codes to user-friendly messages
    STATUS_MESSAGES = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        408: "Request Timeout",
        409: "Conflict",
        410: "Gone",
        413: "Payload Too Large",
        414: "URI Too Long",
        415: "Unsupported Media Type",
        422: "Unprocessable Entity",
        429: "Too Many Requests",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
    }

    # Errors that should not be logged as errors (expected)
    EXPECTED_ERRORS = {400, 401, 403, 404, 405, 422}

    def __init__(self, app: Flask):
        """Initialize error middleware"""
        self.app = app
        self.include_traceback = config.DEBUG

        # Error statistics
        self.error_stats = {}

        # Register error handlers
        self._register_handlers(app)

        logger.info("Error middleware initialized")

    def _register_handlers(self, app: Flask) -> None:
        """Register all error handlers"""
        # Handle all HTTPExceptions
        app.register_error_handler(HTTPException, self._handle_http_exception)

        # Handle all other exceptions
        app.register_error_handler(Exception, self._handle_exception)

        # Specific handlers for common errors
        app.register_error_handler(404, self._handle_404)
        app.register_error_handler(429, self._handle_rate_limit)
        app.register_error_handler(500, self._handle_500)

    def _handle_http_exception(self, error: HTTPException) -> Tuple[Any, int]:
        """
        Handle HTTP exceptions

        Args:
            error: HTTPException instance

        Returns:
            JSON response and status code
        """
        status_code = error.code or 500

        # Build error response
        response = {
            'success': False,
            'error': self.STATUS_MESSAGES.get(status_code, 'Unknown Error'),
            'code': error.__class__.__name__.upper(),
            'status_code': status_code,
        }

        # Add error message if available
        if error.description and error.description != response['error']:
            response['message'] = error.description

        # Add request context
        response['request_id'] = getattr(request, 'request_id', 'unknown')
        response['path'] = request.path
        response['method'] = request.method

        # Log error (but not expected ones at error level)
        if status_code in self.EXPECTED_ERRORS:
            logger.info(
                f"{status_code} {response['error']}: {request.method} {request.path}"
            )
        else:
            logger.error(
                f"{status_code} {response['error']}: {request.method} {request.path}",
                extra={
                    'status_code': status_code,
                    'path': request.path,
                    'method': request.method,
                    'user_id': getattr(g, 'current_user', {}).get('id') if hasattr(g, 'current_user') else None,
                }
            )

        # Update statistics
        self._update_stats(status_code)

        return jsonify(response), status_code

    def _handle_exception(self, error: Exception) -> Tuple[Any, int]:
        """
        Handle general exceptions

        Args:
            error: Exception instance

        Returns:
            JSON response and status code
        """
        # Log full exception with traceback
        logger.error(
            f"Unhandled exception: {error}",
            exc_info=True,
            extra={
                'path': request.path,
                'method': request.method,
                'user_id': getattr(g, 'current_user', {}).get('id') if hasattr(g, 'current_user') else None,
                'request_data': request.get_json(silent=True) if request.is_json else None,
            }
        )

        # Build error response
        response = {
            'success': False,
            'error': 'Internal Server Error',
            'code': 'INTERNAL_ERROR',
            'status_code': 500,
            'request_id': getattr(request, 'request_id', 'unknown'),
            'timestamp': datetime.utcnow().isoformat(),
        }

        # Add debug information in development
        if self.include_traceback:
            response['debug'] = {
                'exception': str(error),
                'type': error.__class__.__name__,
                'traceback': traceback.format_exc().split('\n'),
                'path': request.path,
                'method': request.method,
            }
        else:
            response['message'] = 'An unexpected error occurred. Please try again later.'

        # Update statistics
        self._update_stats(500, error.__class__.__name__)

        return jsonify(response), 500

    def _handle_404(self, error: HTTPException) -> Tuple[Any, int]:
        """Handle 404 Not Found errors"""
        response = {
            'success': False,
            'error': 'Not Found',
            'code': 'NOT_FOUND',
            'status_code': 404,
            'message': f"The requested URL {request.path} was not found on the server.",
            'request_id': getattr(request, 'request_id', 'unknown'),
        }

        # Suggest similar endpoints if possible
        if hasattr(self.app, 'url_map'):
            similar = self._find_similar_routes(request.path)
            if similar:
                response['suggestions'] = similar

        logger.info(f"404 Not Found: {request.method} {request.path}")
        self._update_stats(404)

        return jsonify(response), 404

    def _handle_rate_limit(self, error: HTTPException) -> Tuple[Any, int]:
        """Handle 429 Rate Limit errors"""
        response = {
            'success': False,
            'error': 'Too Many Requests',
            'code': 'RATE_LIMIT_EXCEEDED',
            'status_code': 429,
            'message': 'You have exceeded the rate limit. Please slow down.',
            'request_id': getattr(request, 'request_id', 'unknown'),
        }

        # Add rate limit headers if available
        if hasattr(error, 'description') and error.description:
            try:
                # Parse rate limit info from description
                response['retry_after'] = int(error.description)
            except:
                pass

        logger.warning(
            f"Rate limit exceeded: {request.method} {request.path}",
            extra={
                'user_id': getattr(g, 'current_user', {}).get('id') if hasattr(g, 'current_user') else None,
                'ip': request.remote_addr,
            }
        )

        self._update_stats(429)

        return jsonify(response), 429

    def _handle_500(self, error: HTTPException) -> Tuple[Any, int]:
        """Handle 500 Internal Server errors"""
        response = {
            'success': False,
            'error': 'Internal Server Error',
            'code': 'INTERNAL_ERROR',
            'status_code': 500,
            'message': 'The server encountered an internal error and was unable to complete your request.',
            'request_id': getattr(request, 'request_id', 'unknown'),
            'timestamp': datetime.utcnow().isoformat(),
        }

        # Log critical error
        logger.critical(
            f"500 Internal Server Error: {request.method} {request.path}",
            extra={
                'user_id': getattr(g, 'current_user', {}).get('id') if hasattr(g, 'current_user') else None,
                'request_data': request.get_json(silent=True) if request.is_json else None,
            }
        )

        self._update_stats(500)

        return jsonify(response), 500

    def _find_similar_routes(self, path: str, max_suggestions: int = 3) -> list:
        """Find similar routes for 404 suggestions"""
        try:
            from difflib import get_close_matches

            # Get all registered routes
            all_routes = []
            for rule in self.app.url_map.iter_rules():
                if not rule.rule.startswith('/static'):
                    all_routes.append(rule.rule)

            # Find similar routes
            similar = get_close_matches(path, all_routes, n=max_suggestions, cutoff=0.6)

            return similar
        except:
            return []

    def _update_stats(self, status_code: int, error_type: Optional[str] = None) -> None:
        """Update error statistics"""
        key = f"{status_code}:{error_type or 'default'}"

        if key not in self.error_stats:
            self.error_stats[key] = {
                'count': 0,
                'first_seen': datetime.utcnow(),
                'last_seen': None,
            }

        self.error_stats[key]['count'] += 1
        self.error_stats[key]['last_seen'] = datetime.utcnow()

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        stats = {
            'total_errors': sum(s['count'] for s in self.error_stats.values()),
            'errors_by_type': {},
            'errors_by_status': {},
        }

        for key, data in self.error_stats.items():
            status_code, error_type = key.split(':', 1)
            status_code = int(status_code)

            # By status
            if status_code not in stats['errors_by_status']:
                stats['errors_by_status'][status_code] = 0
            stats['errors_by_status'][status_code] += data['count']

            # By type
            if error_type != 'default':
                if error_type not in stats['errors_by_type']:
                    stats['errors_by_type'][error_type] = 0
                stats['errors_by_type'][error_type] += data['count']

        return stats

    def clear_stats(self) -> None:
        """Clear error statistics"""
        self.error_stats = {}