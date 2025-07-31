# backend/services/services.py
"""
TeleBoost Services Business Logic
Core service management functionality
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from backend.services.models import Service, ServiceCategory
from backend.api.nakrutochka_api import nakrutochka
from backend.supabase_client import supabase
from backend.utils.redis_client import redis_client
from backend.utils.constants import CACHE_TTL, SERVICE_TYPE

logger = logging.getLogger(__name__)


class ServiceManager:
    """Service management class"""

    def __init__(self):
        """Initialize service manager"""
        self.last_update = None
        self.update_interval = timedelta(hours=1)  # Update services every hour

    def should_update(self) -> bool:
        """Check if services should be updated from API"""
        if not self.last_update:
            return True

        return datetime.utcnow() - self.last_update > self.update_interval

    def sync_services(self, force: bool = False) -> Tuple[bool, str]:
        """
        Sync services with Nakrutochka API

        Args:
            force: Force update even if not due

        Returns:
            (success, message)
        """
        try:
            # Check if update needed
            if not force and not self.should_update():
                return True, "Services are up to date"

            logger.info("Starting service sync with Nakrutochka API")

            # Get services from API
            api_services = nakrutochka.get_services()

            if not api_services:
                return False, "No services returned from API"

            logger.info(f"Received {len(api_services)} services from API")

            # Track statistics
            created = 0
            updated = 0
            errors = 0

            # Process each service
            for api_service in api_services:
                try:
                    # Prepare service data - використовуємо id напряму
                    service_data = {
                        'id': api_service['id'],  # Тепер id, а не service_id
                        'name': api_service['name'],
                        'category': api_service.get('category', 'other'),
                        'type': api_service.get('type', SERVICE_TYPE.DEFAULT),
                        'rate': float(api_service.get('rate', 0)),
                        'min': int(api_service.get('min', 1)),
                        'max': int(api_service.get('max', 1000)),
                        'description': api_service.get('description', ''),
                        'dripfeed': api_service.get('dripfeed', False),
                        'refill': api_service.get('refill', False),
                        'cancel': api_service.get('cancel', False),
                        'is_active': api_service.get('is_active', True),
                    }

                    # Check if service exists
                    existing = Service.get_by_id(api_service['id'], use_cache=False)

                    if existing:
                        # Update existing
                        Service.create_or_update(service_data)
                        updated += 1
                    else:
                        # Create new
                        service_data['created_at'] = datetime.utcnow().isoformat()
                        Service.create_or_update(service_data)
                        created += 1

                except Exception as e:
                    logger.error(f"Error processing service {api_service.get('id')}: {e}")
                    errors += 1
                    continue

            # Clear all service caches
            self._clear_service_caches()

            # Update last sync time
            self.last_update = datetime.utcnow()

            message = (
                f"Sync completed: {created} created, {updated} updated, "
                f"{errors} errors out of {len(api_services)} total"
            )

            logger.info(message)

            return errors == 0, message

        except Exception as e:
            logger.error(f"Service sync failed: {e}")
            return False, f"Sync failed: {str(e)}"

    def _clear_service_caches(self) -> None:
        """Clear all service-related caches"""
        try:
            patterns = [
                "services:*",
                "service:*",
                "response:*services*",
            ]

            total_deleted = 0
            for pattern in patterns:
                keys = redis_client.keys(pattern)
                if keys:
                    deleted = redis_client.delete(*keys)
                    total_deleted += deleted

            logger.info(f"Cleared {total_deleted} service cache entries")

        except Exception as e:
            logger.error(f"Error clearing service caches: {e}")

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        try:
            # Get all services
            all_services = Service.get_all(is_active=None, use_cache=False)

            # Calculate statistics
            stats = {
                'total': len(all_services),
                'active': sum(1 for s in all_services if s.is_active),
                'inactive': sum(1 for s in all_services if not s.is_active),
                'by_category': {},
                'by_type': {},
                'features': {
                    'dripfeed': sum(1 for s in all_services if s.dripfeed),
                    'refill': sum(1 for s in all_services if s.refill),
                    'cancel': sum(1 for s in all_services if s.cancel),
                },
                'price_range': {
                    'min': min((s.rate for s in all_services), default=0),
                    'max': max((s.rate for s in all_services), default=0),
                    'average': sum(s.rate for s in all_services) / len(all_services) if all_services else 0,
                },
                'last_update': self.last_update.isoformat() if self.last_update else None,
            }

            # Count by category
            for service in all_services:
                category = service.category.key
                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1

                service_type = service.type
                stats['by_type'][service_type] = stats['by_type'].get(service_type, 0) + 1

            return stats

        except Exception as e:
            logger.error(f"Error getting service statistics: {e}")
            return {}


# Singleton instance
service_manager = ServiceManager()


# Helper functions
def get_all_services(category: Optional[str] = None,
                     active_only: bool = True,
                     use_cache: bool = True) -> List[Service]:
    """
    Get all services with optional filtering

    Args:
        category: Filter by category
        active_only: Only return active services
        use_cache: Use cached data

    Returns:
        List of services
    """
    try:
        # Auto-sync if needed
        if service_manager.should_update():
            service_manager.sync_services()

        return Service.get_all(
            category=category,
            is_active=active_only,
            use_cache=use_cache
        )

    except Exception as e:
        logger.error(f"Error getting services: {e}")
        return []


def get_service_by_id(service_id: int, use_cache: bool = True) -> Optional[Service]:
    """
    Get service by ID

    Args:
        service_id: Nakrutochka service ID
        use_cache: Use cached data

    Returns:
        Service instance or None
    """
    return Service.get_by_id(service_id, use_cache=use_cache)


def get_services_by_category(category: str,
                             active_only: bool = True,
                             use_cache: bool = True) -> List[Service]:
    """
    Get services by category

    Args:
        category: Category key or name
        active_only: Only return active services
        use_cache: Use cached data

    Returns:
        List of services
    """
    return get_all_services(
        category=category,
        active_only=active_only,
        use_cache=use_cache
    )


def search_services(query: str, limit: int = 50) -> List[Service]:
    """
    Search services

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        List of matching services
    """
    if not query or len(query) < 2:
        return []

    return Service.search(query, limit=limit)


def update_services_from_api(force: bool = False) -> Tuple[bool, str]:
    """
    Update services from Nakrutochka API

    Args:
        force: Force update even if not due

    Returns:
        (success, message)
    """
    return service_manager.sync_services(force=force)


def calculate_service_price(service_id: int, quantity: int) -> Optional[float]:
    """
    Calculate price for service order

    Args:
        service_id: Service ID
        quantity: Order quantity

    Returns:
        Price or None if service not found
    """
    service = Service.get_by_id(service_id)

    if not service:
        return None

    return service.calculate_price(quantity)


def get_service_categories() -> List[ServiceCategory]:
    """Get all service categories"""
    return ServiceCategory.get_all()


def get_category_services_count() -> Dict[str, int]:
    """Get service count by category"""
    try:
        # Try cache first
        cache_key = "services:category_counts"
        cached = redis_client.get(cache_key, data_type='json')

        if cached:
            return cached

        # Get counts from database
        all_services = Service.get_all(is_active=True, use_cache=True)

        counts = {}
        for service in all_services:
            category = service.category.key
            counts[category] = counts.get(category, 0) + 1

        # Cache results
        redis_client.set(cache_key, counts, ttl=CACHE_TTL['services'])

        return counts

    except Exception as e:
        logger.error(f"Error getting category counts: {e}")
        return {}