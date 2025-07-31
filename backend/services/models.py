# backend/services/models.py
"""
TeleBoost Service Models
Database models and data structures for services
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from backend.supabase_client import supabase
from backend.utils.redis_client import redis_client
from backend.utils.constants import CACHE_KEYS, SERVICE_TYPE

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service availability status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"


class ServiceCategory:
    """Service category model"""

    # Predefined categories with icons
    CATEGORIES = {
        'instagram': {
            'name': 'Instagram',
            'icon': '📷',
            'description': 'Instagram followers, likes, views, comments',
            'order': 1
        },
        'telegram': {
            'name': 'Telegram',
            'icon': '✈️',
            'description': 'Telegram members, views, reactions',
            'order': 2
        },
        'youtube': {
            'name': 'YouTube',
            'icon': '📺',
            'description': 'YouTube views, likes, subscribers',
            'order': 3
        },
        'tiktok': {
            'name': 'TikTok',
            'icon': '🎵',
            'description': 'TikTok followers, likes, views',
            'order': 4
        },
        'twitter': {
            'name': 'Twitter',
            'icon': '🐦',
            'description': 'Twitter followers, likes, retweets',
            'order': 5
        },
        'facebook': {
            'name': 'Facebook',
            'icon': '👤',
            'description': 'Facebook likes, followers, shares',
            'order': 6
        },
        'other': {
            'name': 'Other',
            'icon': '🌐',
            'description': 'Other social media services',
            'order': 99
        }
    }

    def __init__(self, key: str):
        """Initialize category"""
        self.key = key.lower()
        category_data = self.CATEGORIES.get(self.key, self.CATEGORIES['other'])

        self.name = category_data['name']
        self.icon = category_data['icon']
        self.description = category_data['description']
        self.order = category_data['order']

    @classmethod
    def get_all(cls) -> List['ServiceCategory']:
        """Get all categories sorted by order"""
        categories = []
        for key in cls.CATEGORIES:
            categories.append(cls(key))

        return sorted(categories, key=lambda c: c.order)

    @classmethod
    def normalize_category(cls, category: str) -> str:
        """Normalize category name to key"""
        category_lower = category.lower()

        # Direct match
        if category_lower in cls.CATEGORIES:
            return category_lower

        # Partial match
        for key in cls.CATEGORIES:
            if key in category_lower or category_lower in key:
                return key

        # Check names
        for key, data in cls.CATEGORIES.items():
            if data['name'].lower() == category_lower:
                return key

        return 'other'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'key': self.key,
            'name': self.name,
            'icon': self.icon,
            'description': self.description,
            'order': self.order
        }


class Service:
    """Service model"""

    def __init__(self, data: Dict[str, Any]):
        """Initialize from database data"""
        # IDs
        self.id = data.get('id')  # Internal UUID
        self.service_id = data.get('service_id')  # Nakrutochka ID

        # Basic info
        self.name = data.get('name', '')
        self.category = ServiceCategory(data.get('category', 'other'))
        self.type = data.get('type', SERVICE_TYPE.DEFAULT)

        # Pricing
        self.rate = float(data.get('rate', 0))  # Price per 1000
        self.min = int(data.get('min', 1))
        self.max = int(data.get('max', 1000))

        # Features
        self.description = data.get('description', '')
        self.dripfeed = bool(data.get('dripfeed', False))
        self.refill = bool(data.get('refill', False))
        self.cancel = bool(data.get('cancel', False))

        # Status
        self.is_active = bool(data.get('is_active', True))
        self.status = ServiceStatus(data.get('status', ServiceStatus.ACTIVE))

        # Metadata
        self.position = int(data.get('position', 999))
        self.tags = data.get('tags', [])
        self.metadata = data.get('metadata', {})

        # Timestamps
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')

    @classmethod
    def get_by_id(cls, service_id: int, use_cache: bool = True) -> Optional['Service']:
        """
        Get service by Nakrutochka ID

        Args:
            service_id: Nakrutochka service ID
            use_cache: Whether to use cache

        Returns:
            Service instance or None
        """
        try:
            # Try cache first
            if use_cache:
                cache_key = CACHE_KEYS.format(CACHE_KEYS.SERVICE, service_id=service_id)
                cached = redis_client.get(cache_key, data_type='json')

                if cached:
                    return cls(cached)

            # Get from database
            result = supabase.table('services') \
                .select('*') \
                .eq('service_id', service_id) \
                .single() \
                .execute()

            if result.data:
                service = cls(result.data)

                # Cache it
                if use_cache:
                    cache_key = CACHE_KEYS.format(CACHE_KEYS.SERVICE, service_id=service_id)
                    redis_client.set(cache_key, result.data, ttl=3600)  # 1 hour

                return service

            return None

        except Exception as e:
            logger.error(f"Error getting service {service_id}: {e}")
            return None

    @classmethod
    def get_all(cls, category: Optional[str] = None,
                is_active: bool = True,
                use_cache: bool = True) -> List['Service']:
        """
        Get all services

        Args:
            category: Filter by category
            is_active: Only active services
            use_cache: Whether to use cache

        Returns:
            List of Service instances
        """
        try:
            # Build cache key
            cache_key = f"services:list"
            if category:
                cache_key += f":category:{category}"
            if is_active:
                cache_key += ":active"

            # Try cache first
            if use_cache:
                cached = redis_client.get(cache_key, data_type='json')
                if cached:
                    return [cls(data) for data in cached]

            # Build query
            query = supabase.table('services').select('*')

            if is_active:
                query = query.eq('is_active', True)

            if category:
                normalized_category = ServiceCategory.normalize_category(category)
                query = query.eq('category', normalized_category)

            # Order by category and position
            query = query.order('category').order('position')

            result = query.execute()

            if result.data:
                services = [cls(data) for data in result.data]

                # Cache results
                if use_cache:
                    redis_client.set(cache_key, result.data, ttl=3600)  # 1 hour

                return services

            return []

        except Exception as e:
            logger.error(f"Error getting services: {e}")
            return []

    @classmethod
    def search(cls, query: str, limit: int = 50) -> List['Service']:
        """
        Search services by name or description

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching services
        """
        try:
            # Simple search using ILIKE
            result = supabase.table('services') \
                .select('*') \
                .or_(f"name.ilike.%{query}%,description.ilike.%{query}%") \
                .eq('is_active', True) \
                .limit(limit) \
                .execute()

            if result.data:
                return [cls(data) for data in result.data]

            return []

        except Exception as e:
            logger.error(f"Error searching services: {e}")
            return []

    @classmethod
    def create_or_update(cls, service_data: Dict[str, Any]) -> Optional['Service']:
        """
        Create or update service

        Args:
            service_data: Service data from API

        Returns:
            Service instance or None
        """
        try:
            # Normalize category
            if 'category' in service_data:
                service_data['category'] = ServiceCategory.normalize_category(
                    service_data['category']
                )

            # Add timestamps
            service_data['updated_at'] = datetime.utcnow().isoformat()

            # Upsert (insert or update)
            result = supabase.table('services') \
                .upsert(service_data, on_conflict='service_id') \
                .execute()

            if result.data:
                # Clear cache
                cache_patterns = [
                    "services:list*",
                    f"service:{service_data.get('service_id')}*"
                ]
                for pattern in cache_patterns:
                    keys = redis_client.keys(pattern)
                    if keys:
                        redis_client.delete(*keys)

                return cls(result.data[0])

            return None

        except Exception as e:
            logger.error(f"Error creating/updating service: {e}")
            return None

    def calculate_price(self, quantity: int) -> float:
        """
        Calculate price for given quantity

        Args:
            quantity: Order quantity

        Returns:
            Price in currency
        """
        # Rate is per 1000
        price = (quantity / 1000) * self.rate

        # Round to 2 decimal places
        return round(price, 2)

    def validate_quantity(self, quantity: int) -> tuple[bool, Optional[str]]:
        """
        Validate order quantity

        Args:
            quantity: Order quantity

        Returns:
            (is_valid, error_message)
        """
        if quantity < self.min:
            return False, f"Minimum quantity is {self.min}"

        if quantity > self.max:
            return False, f"Maximum quantity is {self.max}"

        return True, None

    def get_parameters(self) -> Dict[str, Any]:
        """Get service parameters based on type"""
        params = {
            'min': self.min,
            'max': self.max,
            'rate': self.rate,
            'type': self.type,
        }

        # Add type-specific parameters
        if self.type == SERVICE_TYPE.DRIP_FEED:
            params['dripfeed'] = True
            params['runs_min'] = 1
            params['runs_max'] = 100
            params['interval_min'] = 1
            params['interval_max'] = 60 * 24  # 24 hours in minutes

        elif self.type == SERVICE_TYPE.CUSTOM_COMMENTS:
            params['comments_required'] = True
            params['comments_min'] = 1
            params['comments_max'] = self.max

        elif self.type == SERVICE_TYPE.POLL:
            params['answer_required'] = True
            params['answer_min'] = 1
            params['answer_max'] = 10

        elif self.type == SERVICE_TYPE.SUBSCRIPTIONS:
            params['username_required'] = True
            params['posts_min'] = 0
            params['posts_max'] = 1000
            params['delay_min'] = 0
            params['delay_max'] = 3600  # seconds

        return params

    def to_dict(self, detailed: bool = False) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'service_id': self.service_id,
            'name': self.name,
            'category': self.category.to_dict(),
            'type': self.type,
            'rate': self.rate,
            'min': self.min,
            'max': self.max,
            'description': self.description,
            'dripfeed': self.dripfeed,
            'refill': self.refill,
            'cancel': self.cancel,
            'is_active': self.is_active,
            'status': self.status,
        }

        if detailed:
            data.update({
                'position': self.position,
                'tags': self.tags,
                'metadata': self.metadata,
                'parameters': self.get_parameters(),
                'created_at': self.created_at,
                'updated_at': self.updated_at,
            })

        return data