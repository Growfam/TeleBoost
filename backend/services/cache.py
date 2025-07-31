# backend/services/cache.py
"""
TeleBoost Services Cache
Кешування сервісів з Nakrutochka API
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime

from backend.api.nakrutochka_api import nakrutochka
from backend.supabase_client import supabase
from backend.utils.redis_client import redis_client
from backend.utils.constants import CACHE_PREFIX, CACHE_TTL

logger = logging.getLogger(__name__)


async def cache_services() -> bool:
    """
    Fetch services from Nakrutochka API and cache them

    Returns:
        bool: Success status
    """
    try:
        logger.info("🔄 Fetching services from Nakrutochka...")

        # Get services from API
        services = nakrutochka.get_services()

        if not services:
            logger.warning("⚠️ No services returned from Nakrutochka")
            return False

        logger.info(f"✅ Fetched {len(services)} services")

        # Process and save each service
        for service in services:
            try:
                # Check if service exists
                existing = await supabase.client.table('services') \
                    .select('id') \
                    .eq('service_id', service['id']) \
                    .execute()

                service_data = {
                    'service_id': service['id'],
                    'name': service['name'],
                    'category': service['category'],
                    'type': service['type'],
                    'rate': service['rate'],
                    'min': service['min'],
                    'max': service['max'],
                    'description': service.get('description', ''),
                    'dripfeed': service.get('dripfeed', False),
                    'refill': service.get('refill', False),
                    'cancel': service.get('cancel', False),
                    'is_active': service.get('is_active', True),
                    'updated_at': datetime.utcnow().isoformat()
                }

                if existing.data:
                    # Update existing service
                    await supabase.client.table('services') \
                        .update(service_data) \
                        .eq('service_id', service['id']) \
                        .execute()
                else:
                    # Insert new service
                    service_data['created_at'] = datetime.utcnow().isoformat()
                    await supabase.client.table('services') \
                        .insert(service_data) \
                        .execute()

            except Exception as e:
                logger.error(f"Error saving service {service['id']}: {e}")
                continue

        # Cache all services in Redis
        cache_key = f"{CACHE_PREFIX['services']}:all"
        redis_client.set(cache_key, services, ttl=CACHE_TTL['services'])

        # Cache services by category
        categories = {}
        for service in services:
            category = service['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(service)

        for category, category_services in categories.items():
            cache_key = f"{CACHE_PREFIX['services']}:category:{category}"
            redis_client.set(cache_key, category_services, ttl=CACHE_TTL['services'])

        logger.info("✅ Services cached successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Error caching services: {e}")
        return False


async def get_cached_services(category: str = None) -> List[Dict]:
    """
    Get services from cache or database

    Args:
        category: Optional category filter

    Returns:
        List[Dict]: List of services
    """
    try:
        # Try cache first
        if category:
            cache_key = f"{CACHE_PREFIX['services']}:category:{category}"
        else:
            cache_key = f"{CACHE_PREFIX['services']}:all"

        cached = redis_client.get(cache_key)
        if cached:
            return cached

        # Fallback to database
        query = supabase.client.table('services').select('*').eq('is_active', True)

        if category:
            query = query.eq('category', category)

        response = query.order('category').order('position').execute()
        services = response.data or []

        # Cache the results
        redis_client.set(cache_key, services, ttl=CACHE_TTL['services'])

        return services

    except Exception as e:
        logger.error(f"Error getting cached services: {e}")
        return []


async def get_service_by_id(service_id: int) -> Optional[Dict]:
    """
    Get service by ID from cache or database

    Args:
        service_id: Nakrutochka service ID

    Returns:
        Optional[Dict]: Service data
    """
    try:
        # Try cache first
        cache_key = f"{CACHE_PREFIX['services']}:id:{service_id}"
        cached = redis_client.get(cache_key)

        if cached:
            return cached

        # Fallback to database
        response = await supabase.client.table('services') \
            .select('*') \
            .eq('service_id', service_id) \
            .single() \
            .execute()

        service = response.data

        if service:
            # Cache the result
            redis_client.set(cache_key, service, ttl=CACHE_TTL['services'])

        return service

    except Exception as e:
        logger.error(f"Error getting service {service_id}: {e}")
        return None


def clear_services_cache():
    """Clear all services cache"""
    try:
        pattern = f"{CACHE_PREFIX['services']}:*"
        deleted = redis_client.clear_pattern(pattern)
        logger.info(f"🗑️ Cleared {deleted} service cache keys")
        return True
    except Exception as e:
        logger.error(f"Error clearing services cache: {e}")
        return False