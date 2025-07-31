# backend/services/__init__.py
"""
TeleBoost Services Package
Core business logic for service management
"""

from backend.services.models import Service, ServiceCategory
from backend.services.services import (
    ServiceManager,
    get_all_services,
    get_service_by_id,
    get_services_by_category,
    search_services,
    update_services_from_api,
    calculate_service_price,
)
from backend.services.validators import (
    validate_service_order,
    validate_service_parameters,
    check_service_limits,
)

__all__ = [
    # Models
    'Service',
    'ServiceCategory',

    # Service Manager
    'ServiceManager',

    # Functions
    'get_all_services',
    'get_service_by_id',
    'get_services_by_category',
    'search_services',
    'update_services_from_api',
    'calculate_service_price',

    # Validators
    'validate_service_order',
    'validate_service_parameters',
    'check_service_limits',
]