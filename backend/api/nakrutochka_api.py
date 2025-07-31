import os
import json
import logging
import requests
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode
from datetime import datetime

from backend.utils.constants import OrderStatus, ServiceType

logger = logging.getLogger(__name__)


class NakrutochkaAPI:
    """Client for Nakrutochka API v2"""

    def __init__(self, api_key: str = None):
        self.api_url = 'https://nakrutochka.com/api/v2'
        self.api_key = api_key or os.getenv('NAKRUTOCHKA_API_KEY')

        if not self.api_key:
            raise ValueError("Nakrutochka API key is required")

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TeleBoost/1.0',
            'Accept': 'application/json'
        })

        logger.info("Nakrutochka API client initialized")

    def _make_request(self, action: str, data: Dict = None) -> Union[Dict, List]:
        """Make API request"""
        try:
            payload = {
                'key': self.api_key,
                'action': action
            }

            if data:
                payload.update(data)

            # Convert to form data
            form_data = urlencode(payload)

            response = self.session.post(
                self.api_url,
                data=form_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )

            # Log request for debugging
            logger.debug(f"API Request: {action} - Status: {response.status_code}")

            # Parse response
            try:
                result = response.json()
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response: {response.text}")
                return {'error': 'Invalid API response'}

            # Check for API errors
            if isinstance(result, dict) and 'error' in result:
                logger.error(f"API Error: {result['error']}")
                return result

            return result

        except requests.exceptions.Timeout:
            logger.error("API request timeout")
            return {'error': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {'error': str(e)}

    def get_services(self) -> List[Dict]:
        """Get all available services"""
        logger.info("Fetching services from Nakrutochka")

        result = self._make_request('services')

        if isinstance(result, dict) and 'error' in result:
            logger.error(f"Failed to fetch services: {result['error']}")
            return []

        if not isinstance(result, list):
            logger.error("Invalid services response format")
            return []

        # Process and enhance service data
        services = []
        for service in result:
            try:
                # Determine service type
                service_type = ServiceType.DEFAULT
                if 'drip' in service.get('type', '').lower():
                    service_type = ServiceType.DRIP_FEED
                elif 'custom' in service.get('type', '').lower():
                    service_type = ServiceType.CUSTOM_COMMENTS
                elif 'subscriptions' in service.get('type', '').lower():
                    service_type = ServiceType.SUBSCRIPTION
                elif 'poll' in service.get('type', '').lower():
                    service_type = ServiceType.POLL

                # Clean and standardize service data
                processed_service = {
                    'id': int(service.get('service', 0)),
                    'name': service.get('name', ''),
                    'category': service.get('category', ''),
                    'type': service_type,
                    'rate': float(service.get('rate', 0)),
                    'min': int(service.get('min', 1)),
                    'max': int(service.get('max', 1000)),
                    'description': service.get('description', ''),
                    'dripfeed': bool(service.get('dripfeed', False)),
                    'refill': bool(service.get('refill', False)),
                    'cancel': bool(service.get('cancel', False)),
                    'is_active': True  # Assume all returned services are active
                }

                services.append(processed_service)

            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing service: {e}")
                continue

        logger.info(f"Fetched {len(services)} services")
        return services

    def create_order(self, service_id: int, link: str, quantity: int = None, **kwargs) -> Dict:
        """Create new order"""
        logger.info(f"Creating order: service={service_id}, link={link}, quantity={quantity}")

        data = {
            'service': service_id,
            'link': link
        }

        # Add quantity if provided
        if quantity:
            data['quantity'] = quantity

        # Add optional parameters
        optional_params = [
            'runs', 'interval',  # Drip-feed
            'comments',  # Custom comments
            'username', 'min', 'max', 'posts', 'old_posts', 'delay', 'expiry',  # Subscriptions
            'answer_number',  # Poll
            'groups',  # Groups
            'mentions_hashtags', 'mentions_usernames', 'mentions_media_urls'  # Mentions
        ]

        for param in optional_params:
            if param in kwargs and kwargs[param] is not None:
                data[param] = kwargs[param]

        result = self._make_request('add', data)

        if isinstance(result, dict):
            if 'error' in result:
                logger.error(f"Order creation failed: {result['error']}")
                return {
                    'success': False,
                    'error': result['error']
                }

            if 'order' in result:
                logger.info(f"Order created successfully: {result['order']}")
                return {
                    'success': True,
                    'order_id': result['order'],
                    'currency': result.get('currency', 'USD')
                }

        return {
            'success': False,
            'error': 'Invalid response format'
        }

    def get_order_status(self, order_id: Union[int, str]) -> Dict:
        """Get single order status"""
        logger.info(f"Getting status for order: {order_id}")

        result = self._make_request('status', {'order': order_id})

        if isinstance(result, dict):
            if 'error' in result:
                logger.error(f"Failed to get order status: {result['error']}")
                return {
                    'success': False,
                    'error': result['error']
                }

            # Map Nakrutochka status to our status
            status_map = {
                'Pending': OrderStatus.PENDING,
                'In progress': OrderStatus.IN_PROGRESS,
                'Processing': OrderStatus.PROCESSING,
                'Completed': OrderStatus.COMPLETED,
                'Partial': OrderStatus.PARTIAL,
                'Canceled': OrderStatus.CANCELLED,
                'Cancelled': OrderStatus.CANCELLED,
                'Failed': OrderStatus.FAILED
            }

            external_status = result.get('status', '')
            internal_status = status_map.get(external_status, OrderStatus.PROCESSING)

            return {
                'success': True,
                'status': internal_status,
                'external_status': external_status,
                'charge': float(result.get('charge', 0)),
                'start_count': int(result.get('start_count', 0)),
                'remains': int(result.get('remains', 0)),
                'currency': result.get('currency', 'USD')
            }

        return {
            'success': False,
            'error': 'Invalid response format'
        }

    def get_multiple_order_status(self, order_ids: List[Union[int, str]]) -> Dict:
        """Get status for multiple orders"""
        logger.info(f"Getting status for {len(order_ids)} orders")

        # Convert list to comma-separated string
        orders_str = ','.join(map(str, order_ids))

        result = self._make_request('status', {'orders': orders_str})

        if isinstance(result, dict) and 'error' not in result:
            return {
                'success': True,
                'orders': result
            }

        return {
            'success': False,
            'error': result.get('error', 'Invalid response format') if isinstance(result, dict) else 'Invalid response'
        }

    def refill_order(self, order_id: Union[int, str]) -> Dict:
        """Request refill for an order"""
        logger.info(f"Requesting refill for order: {order_id}")

        result = self._make_request('refill', {'order': order_id})

        if isinstance(result, dict):
            if 'error' in result:
                return {
                    'success': False,
                    'error': result['error']
                }

            if 'refill' in result:
                return {
                    'success': True,
                    'refill_id': result['refill']
                }

        return {
            'success': False,
            'error': 'Invalid response format'
        }

    def get_refill_status(self, refill_id: Union[int, str]) -> Dict:
        """Get refill status"""
        logger.info(f"Getting refill status: {refill_id}")

        result = self._make_request('refill_status', {'refill': refill_id})

        if isinstance(result, dict):
            if 'error' in result:
                return {
                    'success': False,
                    'error': result['error']
                }

            return {
                'success': True,
                'status': result.get('status', 'Unknown')
            }

        return {
            'success': False,
            'error': 'Invalid response format'
        }

    def cancel_orders(self, order_ids: List[Union[int, str]]) -> Dict:
        """Cancel multiple orders"""
        logger.info(f"Cancelling {len(order_ids)} orders")

        # Convert list to comma-separated string
        orders_str = ','.join(map(str, order_ids))

        result = self._make_request('cancel', {'orders': orders_str})

        if isinstance(result, dict):
            return {
                'success': 'error' not in result,
                'result': result
            }

        return {
            'success': False,
            'error': 'Invalid response format'
        }

    def get_balance(self) -> Dict:
        """Get account balance"""
        logger.info("Getting Nakrutochka account balance")

        result = self._make_request('balance')

        if isinstance(result, dict):
            if 'error' in result:
                return {
                    'success': False,
                    'error': result['error']
                }

            # Extract balance and currency
            if 'balance' in result:
                return {
                    'success': True,
                    'balance': float(result['balance']),
                    'currency': result.get('currency', 'USD')
                }

        return {
            'success': False,
            'error': 'Invalid response format'
        }

    def calculate_order_cost(self, service_id: int, quantity: int) -> float:
        """Calculate order cost based on service rate"""
        # This would typically use cached service data
        # For now, return a simple calculation
        # In production, you'd look up the service rate from cache

        # Example calculation (you'd get actual rate from cached services)
        rate_per_1000 = 1.0  # This should come from service data
        cost = (quantity / 1000) * rate_per_1000

        return round(cost, 2)


# Create singleton instance
nakrutochka = NakrutochkaAPI()

# Export for convenience
__all__ = ['nakrutochka', 'NakrutochkaAPI']