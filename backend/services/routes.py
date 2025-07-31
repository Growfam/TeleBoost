# backend/services/routes.py
"""
TeleBoost Services Routes
API endpoints for service management
"""
import logging
from flask import Blueprint, request, jsonify, g
from typing import Optional

from backend.auth.decorators import jwt_required, optional_jwt, rate_limit
from backend.services.services import (
    get_all_services,
    get_service_by_id,
    get_services_by_category,
    search_services,
    update_services_from_api,
    get_service_categories,
    get_category_services_count,
    service_manager
)
from backend.services.validators import get_required_fields
from backend.middleware.cache_middleware import CacheMiddleware
from backend.utils.constants import SUCCESS_MESSAGES, ERROR_MESSAGES

logger = logging.getLogger(__name__)

# Create Blueprint
services_bp = Blueprint('services', __name__, url_prefix='/api/services')


@services_bp.route('/', methods=['GET'])
@optional_jwt  # Services are public but may have user-specific pricing
async def get_services():
    """
    Get all services

    Query params:
    - category: Filter by category
    - active: Show only active services (default: true)
    - search: Search query
    - page: Page number (default: 1)
    - limit: Items per page (default: 50)

    Response:
    {
        "success": true,
        "data": {
            "services": [...],
            "categories": [...],
            "total": 100,
            "page": 1,
            "pages": 2
        }
    }
    """
    try:
        # Get query parameters
        category = request.args.get('category')
        active_only = request.args.get('active', 'true').lower() == 'true'
        search_query = request.args.get('search')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))

        # Validate pagination
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 50

        # Search or filter
        if search_query:
            services = await search_services(search_query, limit=limit)
        else:
            services = await get_all_services(
                category=category,
                active_only=active_only,
                use_cache=True
            )

        # Paginate
        total = len(services)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_services = services[start_idx:end_idx]

        # Get categories with counts
        categories = get_service_categories()
        category_counts = get_category_services_count()

        # Format categories with counts
        categories_data = []
        for cat in categories:
            cat_dict = cat.to_dict()
            cat_dict['count'] = category_counts.get(cat.key, 0)
            categories_data.append(cat_dict)

        # Convert services to dict
        services_data = [s.to_dict() for s in paginated_services]

        # Apply user-specific modifications if authenticated
        if g.current_user:
            # Could apply user-specific pricing, discounts, etc.
            pass

        return jsonify({
            'success': True,
            'data': {
                'services': services_data,
                'categories': categories_data,
                'total': total,
                'page': page,
                'pages': (total + limit - 1) // limit,  # Ceiling division
                'limit': limit,
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting services: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'SERVICES_ERROR'
        }), 500


@services_bp.route('/<int:service_id>', methods=['GET'])
@optional_jwt
async def get_service(service_id: int):
    """
    Get service details

    Response:
    {
        "success": true,
        "data": {
            "service": {
                "id": "...",
                "service_id": 123,
                "name": "Instagram Followers",
                "category": {...},
                "parameters": {...},
                ...
            }
        }
    }
    """
    try:
        service = await get_service_by_id(service_id, use_cache=True)

        if not service:
            return jsonify({
                'success': False,
                'error': 'Service not found',
                'code': 'SERVICE_NOT_FOUND'
            }), 404

        # Get detailed service data
        service_data = service.to_dict(detailed=True)

        # Add required fields info
        service_data['required_fields'] = get_required_fields(service)

        # Apply user-specific modifications if authenticated
        if g.current_user:
            # Could apply user-specific pricing, discounts, etc.
            pass

        return jsonify({
            'success': True,
            'data': {
                'service': service_data
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting service {service_id}: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'SERVICE_ERROR'
        }), 500


@services_bp.route('/categories', methods=['GET'])
def get_categories():
    """
    Get all service categories

    Response:
    {
        "success": true,
        "data": {
            "categories": [
                {
                    "key": "instagram",
                    "name": "Instagram",
                    "icon": "📷",
                    "description": "...",
                    "count": 25
                }
            ]
        }
    }
    """
    try:
        categories = get_service_categories()
        category_counts = get_category_services_count()

        # Format categories with counts
        categories_data = []
        for cat in categories:
            cat_dict = cat.to_dict()
            cat_dict['count'] = category_counts.get(cat.key, 0)
            categories_data.append(cat_dict)

        return jsonify({
            'success': True,
            'data': {
                'categories': categories_data
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'CATEGORIES_ERROR'
        }), 500


@services_bp.route('/sync', methods=['POST'])
@jwt_required
@rate_limit(calls=1, period=300)  # 1 sync per 5 minutes
async def sync_services():
    """
    Sync services with Nakrutochka API (Admin only)

    Request body:
    {
        "force": true  // Force sync even if not due
    }

    Response:
    {
        "success": true,
        "message": "Sync completed: 10 created, 50 updated, 0 errors",
        "data": {
            "statistics": {...}
        }
    }
    """
    try:
        # Check admin permission
        if not g.current_user.is_admin:
            return jsonify({
                'success': False,
                'error': 'Admin access required',
                'code': 'ADMIN_REQUIRED'
            }), 403

        # Get force flag
        data = request.get_json() or {}
        force = data.get('force', False)

        # Perform sync
        success, message = await update_services_from_api(force=force)

        # Clear cache after sync
        if hasattr(request.app, 'middleware') and 'cache' in request.app.middleware:
            cache_middleware = request.app.middleware['cache']
            cache_middleware.invalidate_cache(pattern="*services*")

        # Get statistics
        statistics = service_manager.get_service_statistics()

        return jsonify({
            'success': success,
            'message': message,
            'data': {
                'statistics': statistics
            }
        }), 200 if success else 500

    except Exception as e:
        logger.error(f"Error syncing services: {e}")
        return jsonify({
            'success': False,
            'error': 'Sync failed',
            'code': 'SYNC_ERROR'
        }), 500


@services_bp.route('/statistics', methods=['GET'])
@jwt_required
def get_statistics():
    """
    Get service statistics (Admin only)

    Response:
    {
        "success": true,
        "data": {
            "total": 150,
            "active": 140,
            "inactive": 10,
            "by_category": {...},
            "by_type": {...},
            "features": {...},
            "price_range": {...},
            "last_update": "2024-01-01T00:00:00Z"
        }
    }
    """
    try:
        # Check admin permission
        if not g.current_user.is_admin:
            return jsonify({
                'success': False,
                'error': 'Admin access required',
                'code': 'ADMIN_REQUIRED'
            }), 403

        statistics = service_manager.get_service_statistics()

        return jsonify({
            'success': True,
            'data': statistics
        }), 200

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'STATISTICS_ERROR'
        }), 500


@services_bp.route('/calculate-price', methods=['POST'])
@optional_jwt
def calculate_price():
    """
    Calculate price for service order

    Request body:
    {
        "service_id": 123,
        "quantity": 1000,
        "runs": 5  // For drip-feed
    }

    Response:
    {
        "success": true,
        "data": {
            "price": 10.50,
            "currency": "USD",
            "quantity": 1000,
            "total_quantity": 5000  // For drip-feed
        }
    }
    """
    try:
        data = request.get_json()

        if not data or 'service_id' not in data:
            return jsonify({
                'success': False,
                'error': 'service_id is required',
                'code': 'MISSING_SERVICE_ID'
            }), 400

        service_id = data['service_id']
        quantity = data.get('quantity', 1)
        runs = data.get('runs', 1)

        # Get service
        service = Service.get_by_id(service_id)

        if not service:
            return jsonify({
                'success': False,
                'error': 'Service not found',
                'code': 'SERVICE_NOT_FOUND'
            }), 404

        # Calculate price
        total_quantity = quantity * runs
        price = service.calculate_price(total_quantity)

        # Apply user discount if authenticated
        if g.current_user and g.current_user.is_premium:
            # Example: 10% discount for premium users
            price = price * 0.9

        return jsonify({
            'success': True,
            'data': {
                'price': round(price, 2),
                'currency': 'USD',  # Could be from config
                'quantity': quantity,
                'total_quantity': total_quantity,
                'rate': service.rate,
            }
        }), 200

    except Exception as e:
        logger.error(f"Error calculating price: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'CALCULATION_ERROR'
        }), 500