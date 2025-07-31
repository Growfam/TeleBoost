# backend/api/error_handlers.py
"""
TeleBoost API Error Handlers
Centralized error handling for external API calls
"""
import logging
import time
from typing import Any, Callable, Optional, Dict, Type
from functools import wraps
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base API error class"""

    def __init__(self, message: str, code: Optional[str] = None,
                 status_code: Optional[int] = None,
                 response_data: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.response_data = response_data or {}

    def __str__(self):
        parts = [self.message]
        if self.code:
            parts.append(f"Code: {self.code}")
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        return " | ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        return {
            'error': self.message,
            'code': self.code,
            'status_code': self.status_code,
            'details': self.response_data,
        }


class RateLimitError(APIError):
    """Rate limit exceeded error"""

    def __init__(self, message: str = "Rate limit exceeded",
                 retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, code='RATE_LIMIT', status_code=429, **kwargs)
        self.retry_after = retry_after


class AuthenticationError(APIError):
    """Authentication failed error"""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, code='AUTH_ERROR', status_code=401, **kwargs)


class ServiceUnavailableError(APIError):
    """Service temporarily unavailable error"""

    def __init__(self, message: str = "Service temporarily unavailable", **kwargs):
        super().__init__(message, code='SERVICE_UNAVAILABLE', status_code=503, **kwargs)


class ValidationError(APIError):
    """Request validation error"""

    def __init__(self, message: str = "Validation failed", **kwargs):
        super().__init__(message, code='VALIDATION_ERROR', status_code=400, **kwargs)


def handle_api_error(response: requests.Response) -> None:
    """
    Handle API response and raise appropriate error

    Args:
        response: Requests response object

    Raises:
        APIError: Appropriate error based on response
    """
    try:
        error_data = response.json()
    except:
        error_data = {'error': response.text or 'Unknown error'}

    status_code = response.status_code
    error_message = error_data.get('error', 'API request failed')

    # Map status codes to specific errors
    if status_code == 429:
        retry_after = None

        # Try to get retry-after from headers
        if 'Retry-After' in response.headers:
            try:
                retry_after = int(response.headers['Retry-After'])
            except:
                pass

        raise RateLimitError(
            message=error_message,
            retry_after=retry_after,
            response_data=error_data
        )

    elif status_code == 401:
        raise AuthenticationError(
            message=error_message,
            response_data=error_data
        )

    elif status_code == 503:
        raise ServiceUnavailableError(
            message=error_message,
            response_data=error_data
        )

    elif status_code == 400:
        raise ValidationError(
            message=error_message,
            response_data=error_data
        )

    else:
        # Generic API error
        raise APIError(
            message=error_message,
            code=error_data.get('code', 'API_ERROR'),
            status_code=status_code,
            response_data=error_data
        )


def retry_on_error(
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (RequestException, APIError),
        retry_on_status: tuple = (429, 502, 503, 504)
):
    """
    Decorator to retry function on specific errors

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Backoff multiplier for each retry
        exceptions: Tuple of exceptions to catch
        retry_on_status: Tuple of status codes to retry on

    Usage:
        @retry_on_error(max_retries=3, delay=1.0)
        def api_call():
            return requests.get('https://api.example.com')
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # Check if result is a response object with retryable status
                    if hasattr(result, 'status_code') and result.status_code in retry_on_status:
                        if attempt < max_retries:
                            logger.warning(
                                f"API call returned status {result.status_code}, "
                                f"retrying in {current_delay}s (attempt {attempt + 1}/{max_retries})"
                            )
                            time.sleep(current_delay)
                            current_delay *= backoff
                            continue

                    return result

                except exceptions as e:
                    last_exception = e

                    # Check if it's a rate limit error with retry_after
                    if isinstance(e, RateLimitError) and e.retry_after:
                        wait_time = e.retry_after
                    else:
                        wait_time = current_delay

                    if attempt < max_retries:
                        logger.warning(
                            f"API call failed with {type(e).__name__}: {str(e)}, "
                            f"retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"API call failed after {max_retries} retries: {str(e)}"
                        )

            # Re-raise the last exception
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def handle_connection_error(func: Callable) -> Callable:
    """
    Decorator to handle connection errors gracefully

    Usage:
        @handle_connection_error
        def api_call():
            return requests.get('https://api.example.com')
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise ServiceUnavailableError(
                "Unable to connect to external service. Please try again later."
            )
        except Timeout as e:
            logger.error(f"Request timeout: {e}")
            raise ServiceUnavailableError(
                "Request timed out. Please try again later."
            )
        except RequestException as e:
            logger.error(f"Request error: {e}")
            raise APIError(f"Request failed: {str(e)}")

    return wrapper


def validate_api_response(required_fields: list) -> Callable:
    """
    Decorator to validate API response contains required fields

    Args:
        required_fields: List of required field names

    Usage:
        @validate_api_response(['id', 'status'])
        def get_order_status():
            return api.get_status(order_id)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            if not isinstance(result, dict):
                raise ValidationError(
                    f"Invalid response format: expected dict, got {type(result).__name__}"
                )

            missing_fields = []
            for field in required_fields:
                if field not in result:
                    missing_fields.append(field)

            if missing_fields:
                raise ValidationError(
                    f"Missing required fields in response: {', '.join(missing_fields)}"
                )

            return result

        return wrapper

    return decorator


def log_api_calls(service_name: str) -> Callable:
    """
    Decorator to log API calls with timing

    Args:
        service_name: Name of the API service

    Usage:
        @log_api_calls('Nakrutochka')
        def create_order():
            return api.order(...)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            logger.info(f"[{service_name}] Calling {func.__name__}")

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(
                    f"[{service_name}] {func.__name__} completed in {duration:.3f}s"
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                logger.error(
                    f"[{service_name}] {func.__name__} failed after {duration:.3f}s: {e}"
                )

                raise

        return wrapper

    return decorator