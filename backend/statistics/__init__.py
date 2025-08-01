# backend/statistics/__init__.py
"""
TeleBoost Statistics Module
Система збору та аналізу статистики
"""

# Models
from backend.statistics.models import (
    SystemMetrics,
    AnalyticsMetrics,
    UserAnalytics,
    MetricPeriod,
    MetricData
)

# Services
from backend.statistics.analytics import (
    DashboardService,
    ReportGenerator,
    MetricsExporter
)

# Routes
from backend.statistics.routes import statistics_bp

__all__ = [
    # Models
    'SystemMetrics',
    'AnalyticsMetrics',
    'UserAnalytics',
    'MetricPeriod',
    'MetricData',

    # Services
    'DashboardService',
    'ReportGenerator',
    'MetricsExporter',

    # Blueprint
    'statistics_bp',
]

__version__ = '1.0.0'
__module_name__ = 'TeleBoost Statistics System'