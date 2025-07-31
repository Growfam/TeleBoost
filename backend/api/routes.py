# backend/api/routes.py
"""
TeleBoost API Routes
General API endpoints and utilities
"""
import logging
from flask import Blueprint, request, jsonify, g
from datetime import datetime

from backend.auth.decorators import jwt_required, optional_jwt
from backend.api.nakrutochka_api import nakrutochka
from backend.config import config
from backend.utils.constants import SUCCESS_MESSAGES, ERROR_MESSAGES

logger = logging.getLogger(__name__)

# Create Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    API health check with external service status

    Response:
    {
        "success": true,
        "data": {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "services": {
                "nakrutochka": {
                    "status": "operational",
                    "response_time": 0.123
                }
            }
        }
    }
    """
    try:
        services_status = {}

        # Check Nakrutochka API
        try:
            start_time = datetime.utcnow()
            balance_result = nakrutochka.get_balance()
            response_time = (datetime.utcnow() - start_time).total_seconds()

            services_status['nakrutochka'] = {
                'status': 'operational' if balance_result.get('success') else 'degraded',
                'response_time': round(response_time, 3)
            }
        except Exception as e:
            logger.error(f"Nakrutochka health check failed: {e}")
            services_status['nakrutochka'] = {
                'status': 'unavailable',
                'error': str(e)
            }

        # Overall status
        all_operational = all(
            s.get('status') == 'operational'
            for s in services_status.values()
        )

        return jsonify({
            'success': True,
            'data': {
                'status': 'healthy' if all_operational else 'degraded',
                'timestamp': datetime.utcnow().isoformat(),
                'services': services_status
            }
        }), 200

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'success': False,
            'error': 'Health check failed',
            'code': 'HEALTH_CHECK_ERROR'
        }), 500


@api_bp.route('/external-balance', methods=['GET'])
@jwt_required
def get_external_balance():
    """
    Get Nakrutochka account balance (Admin only)

    Response:
    {
        "success": true,
        "data": {
            "balance": 1234.56,
            "currency": "USD"
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

        # Get balance from Nakrutochka
        result = nakrutochka.get_balance()

        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to get balance'),
                'code': 'EXTERNAL_API_ERROR'
            }), 500

        return jsonify({
            'success': True,
            'data': {
                'balance': result.get('balance', 0),
                'currency': result.get('currency', 'USD')
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting external balance: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'BALANCE_ERROR'
        }), 500


@api_bp.route('/test-connection', methods=['POST'])
@jwt_required
def test_api_connection():
    """
    Test connection to external API (Admin only)

    Request body:
    {
        "api": "nakrutochka"  // API to test
    }

    Response:
    {
        "success": true,
        "data": {
            "api": "nakrutochka",
            "connected": true,
            "response_time": 0.123,
            "details": {...}
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

        data = request.get_json() or {}
        api_name = data.get('api', 'nakrutochka')

        if api_name != 'nakrutochka':
            return jsonify({
                'success': False,
                'error': 'Unknown API',
                'code': 'UNKNOWN_API'
            }), 400

        # Test Nakrutochka connection
        start_time = datetime.utcnow()

        try:
            # Try to get services (lightweight call)
            services = nakrutochka.get_services()
            response_time = (datetime.utcnow() - start_time).total_seconds()

            connected = len(services) > 0

            details = {
                'services_count': len(services),
                'api_url': config.NAKRUTOCHKA_API_URL,
            }

        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds()
            connected = False
            details = {
                'error': str(e)
            }

        return jsonify({
            'success': True,
            'data': {
                'api': api_name,
                'connected': connected,
                'response_time': round(response_time, 3),
                'details': details
            }
        }), 200

    except Exception as e:
        logger.error(f"Error testing API connection: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'TEST_ERROR'
        }), 500


@api_bp.route('/supported-services', methods=['GET'])
def get_supported_services():
    """
    Get list of supported service types and platforms

    Response:
    {
        "success": true,
        "data": {
            "platforms": [
                {
                    "key": "instagram",
                    "name": "Instagram",
                    "icon": "📷",
                    "supported": true
                }
            ],
            "service_types": [
                {
                    "key": "default",
                    "name": "Regular Order",
                    "description": "Standard service order"
                }
            ]
        }
    }
    """
    try:
        from backend.services.models import ServiceCategory
        from backend.utils.constants import SERVICE_TYPE

        # Get all platforms
        platforms = []
        for category in ServiceCategory.get_all():
            platforms.append({
                'key': category.key,
                'name': category.name,
                'icon': category.icon,
                'supported': True
            })

        # Get service types
        service_types = [
            {
                'key': SERVICE_TYPE.DEFAULT,
                'name': 'Regular Order',
                'description': 'Standard service order with quantity'
            },
            {
                'key': SERVICE_TYPE.DRIP_FEED,
                'name': 'Drip-feed',
                'description': 'Gradual delivery over time'
            },
            {
                'key': SERVICE_TYPE.CUSTOM_COMMENTS,
                'name': 'Custom Comments',
                'description': 'Service with custom comment list'
            },
            {
                'key': SERVICE_TYPE.POLL,
                'name': 'Poll Votes',
                'description': 'Voting in polls'
            },
            {
                'key': SERVICE_TYPE.SUBSCRIPTIONS,
                'name': 'Subscriptions',
                'description': 'Auto-order for new posts'
            }
        ]

        return jsonify({
            'success': True,
            'data': {
                'platforms': platforms,
                'service_types': service_types
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting supported services: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'SERVICES_ERROR'
        }), 500


@api_bp.route('/system-info', methods=['GET'])
@jwt_required
def get_system_info():
    """
    Get system information (Admin only)

    Response:
    {
        "success": true,
        "data": {
            "version": "1.0.0",
            "environment": "production",
            "features": {...},
            "limits": {...},
            "external_apis": {...}
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

        from backend.utils.constants import LIMITS, FEES

        system_info = {
            'version': '1.0.0',
            'environment': config.ENV,
            'debug': config.DEBUG,
            'features': {
                'payments': {
                    'cryptobot': bool(config.CRYPTOBOT_TOKEN),
                    'nowpayments': bool(config.NOWPAYMENTS_API_KEY),
                },
                'middleware': {
                    'compression': config.MIDDLEWARE_COMPRESSION_ENABLED,
                    'cache': config.MIDDLEWARE_CACHE_ENABLED,
                    'performance': config.MIDDLEWARE_PERFORMANCE_ENABLED,
                    'rate_limit': config.RATELIMIT_ENABLED,
                },
                'referrals': {
                    'enabled': True,
                    'bonus_percent': config.REFERRAL_BONUS_PERCENT,
                    'user_bonus': config.REFERRAL_USER_BONUS,
                }
            },
            'limits': LIMITS,
            'fees': FEES,
            'external_apis': {
                'nakrutochka': {
                    'url': config.NAKRUTOCHKA_API_URL,
                    'configured': bool(config.NAKRUTOCHKA_API_KEY),
                }
            }
        }

        return jsonify({
            'success': True,
            'data': system_info
        }), 200

    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'SYSTEM_INFO_ERROR'
        }), 500