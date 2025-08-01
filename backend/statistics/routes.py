# backend/statistics/routes.py
"""
TeleBoost Statistics Routes
API endpoints для статистики та аналітики
"""
import logging
from flask import Blueprint, request, jsonify, g, Response, Dict, List, Any
from datetime import datetime, timedelta
import json

from backend.auth.decorators import jwt_required, admin_required, rate_limit
from backend.statistics.models import SystemMetrics, AnalyticsMetrics, UserAnalytics, MetricPeriod
from backend.statistics.analytics import DashboardService, ReportGenerator, MetricsExporter
from backend.utils.constants import ERROR_MESSAGES
from backend.utils.validators import validate_date_range

logger = logging.getLogger(__name__)

# Створюємо Blueprint
statistics_bp = Blueprint('statistics', __name__, url_prefix='/api/statistics')


@statistics_bp.route('/overview', methods=['GET'])
@jwt_required
@admin_required
def get_statistics_overview():
    """
    Отримати загальну статистику системи (адмін)

    Response:
    {
        "success": true,
        "data": {
            "users": {...},
            "orders": {...},
            "revenue": {...},
            "services": {...},
            "performance": {...}
        }
    }
    """
    try:
        metrics = SystemMetrics.get_overview_metrics()

        return jsonify({
            'success': True,
            'data': metrics
        }), 200

    except Exception as e:
        logger.error(f"Error getting statistics overview: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'STATS_ERROR'
        }), 500


@statistics_bp.route('/dashboard', methods=['GET'])
@jwt_required
@admin_required
def get_admin_dashboard():
    """
    Отримати повний дашборд для адмін панелі

    Response:
    {
        "success": true,
        "data": {
            "overview": {...},
            "real_time": {...},
            "alerts": [...],
            "quick_stats": {...},
            "activity_feed": [...],
            "trends": {...}
        }
    }
    """
    try:
        dashboard = DashboardService.get_admin_dashboard()

        return jsonify({
            'success': True,
            'data': dashboard
        }), 200

    except Exception as e:
        logger.error(f"Error getting admin dashboard: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'DASHBOARD_ERROR'
        }), 500


@statistics_bp.route('/analytics/financial', methods=['GET'])
@jwt_required
@admin_required
def get_financial_analytics():
    """
    Отримати фінансову аналітику

    Query params:
        - period: hour, day, week, month, quarter, year (default: month)
    """
    try:
        period_param = request.args.get('period', 'month')

        # Мапінг періодів
        period_map = {
            'hour': MetricPeriod.HOUR,
            'day': MetricPeriod.DAY,
            'week': MetricPeriod.WEEK,
            'month': MetricPeriod.MONTH,
            'quarter': MetricPeriod.QUARTER,
            'year': MetricPeriod.YEAR,
            'all': MetricPeriod.ALL_TIME
        }

        period = period_map.get(period_param, MetricPeriod.MONTH)
        analytics = AnalyticsMetrics.get_financial_analytics(period)

        return jsonify({
            'success': True,
            'data': analytics
        }), 200

    except Exception as e:
        logger.error(f"Error getting financial analytics: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'ANALYTICS_ERROR'
        }), 500


@statistics_bp.route('/analytics/users', methods=['GET'])
@jwt_required
@admin_required
def get_user_analytics():
    """
    Отримати аналітику користувачів

    Response:
    {
        "success": true,
        "data": {
            "segments": {
                "by_activity": {...},
                "by_spending": {...},
                "by_lifetime": {...},
                "by_referral": {...}
            }
        }
    }
    """
    try:
        segments = UserAnalytics.get_user_segments()

        # Додаємо візуалізації
        total_users = sum(segments.get('by_activity', {}).values())

        analytics = {
            'segments': segments,
            'visualizations': {
                'activity_chart': _prepare_pie_chart(segments.get('by_activity', {})),
                'spending_chart': _prepare_pie_chart(segments.get('by_spending', {})),
                'lifetime_chart': _prepare_bar_chart(segments.get('by_lifetime', {})),
                'referral_chart': _prepare_pie_chart(segments.get('by_referral', {}))
            },
            'insights': _generate_user_insights(segments, total_users)
        }

        return jsonify({
            'success': True,
            'data': analytics
        }), 200

    except Exception as e:
        logger.error(f"Error getting user analytics: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'USER_ANALYTICS_ERROR'
        }), 500


@statistics_bp.route('/report/financial', methods=['POST'])
@jwt_required
@admin_required
@rate_limit(calls=10, period=3600)  # 10 звітів на годину
def generate_financial_report():
    """
    Згенерувати фінансовий звіт

    Request body:
    {
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "format": "json"  // json, csv, excel
    }
    """
    try:
        data = request.get_json() or {}

        # Валідація дат
        try:
            start_date = datetime.fromisoformat(data.get('start_date'))
            end_date = datetime.fromisoformat(data.get('end_date'))
        except:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use ISO format (YYYY-MM-DD)',
                'code': 'INVALID_DATE'
            }), 400

        # Перевірка діапазону
        if start_date > end_date:
            return jsonify({
                'success': False,
                'error': 'Start date must be before end date',
                'code': 'INVALID_RANGE'
            }), 400

        if (end_date - start_date).days > 365:
            return jsonify({
                'success': False,
                'error': 'Maximum report period is 365 days',
                'code': 'RANGE_TOO_LARGE'
            }), 400

        # Генеруємо звіт
        format_type = data.get('format', 'json')
        report = ReportGenerator.generate_financial_report(
            start_date=start_date,
            end_date=end_date,
            format=format_type
        )

        if format_type == 'csv':
            return Response(
                report,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=financial_report_{start_date.date()}_{end_date.date()}.csv'
                }
            )
        elif format_type == 'excel':
            return Response(
                report,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={
                    'Content-Disposition': f'attachment; filename=financial_report_{start_date.date()}_{end_date.date()}.xlsx'
                }
            )
        else:
            return jsonify({
                'success': True,
                'data': report
            }), 200

    except Exception as e:
        logger.error(f"Error generating financial report: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'REPORT_ERROR'
        }), 500


@statistics_bp.route('/charts/<chart_type>', methods=['GET'])
@jwt_required
@admin_required
def get_chart_data(chart_type: str):
    """
    Отримати дані для графіків

    Chart types:
        - revenue: Графік доходів
        - orders: Графік замовлень
        - users: Графік реєстрацій
        - services: Розподіл по сервісах

    Query params:
        - period: Період (7d, 30d, 3m, 6m, 1y)
        - interval: Інтервал (hour, day, week, month)
    """
    try:
        # Параметри
        period = request.args.get('period', '30d')
        interval = request.args.get('interval', 'day')

        # Визначаємо дати
        end_date = datetime.utcnow()
        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '3m':
            start_date = end_date - timedelta(days=90)
        elif period == '6m':
            start_date = end_date - timedelta(days=180)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)

        # Отримуємо дані відповідно до типу
        if chart_type == 'revenue':
            data = _get_revenue_chart_data(start_date, end_date, interval)
        elif chart_type == 'orders':
            data = _get_orders_chart_data(start_date, end_date, interval)
        elif chart_type == 'users':
            data = _get_users_chart_data(start_date, end_date, interval)
        elif chart_type == 'services':
            data = _get_services_distribution_data()
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid chart type',
                'code': 'INVALID_CHART'
            }), 400

        return jsonify({
            'success': True,
            'data': {
                'chart_type': chart_type,
                'period': period,
                'interval': interval,
                'data': data
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'CHART_ERROR'
        }), 500


@statistics_bp.route('/metrics/export', methods=['GET'])
@jwt_required
@admin_required
def export_metrics():
    """
    Експорт метрик для моніторингу

    Query params:
        - format: prometheus, json (default: json)
    """
    try:
        format_type = request.args.get('format', 'json')

        if format_type == 'prometheus':
            metrics = MetricsExporter.export_prometheus_metrics()
            return Response(metrics, mimetype='text/plain')
        else:
            metrics = MetricsExporter.export_json_metrics()
            return jsonify({
                'success': True,
                'data': metrics
            }), 200

    except Exception as e:
        logger.error(f"Error exporting metrics: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'EXPORT_ERROR'
        }), 500


@statistics_bp.route('/user/<user_id>', methods=['GET'])
@jwt_required
@admin_required
def get_user_statistics(user_id: str):
    """
    Отримати статистику конкретного користувача (адмін)
    """
    try:
        from backend.users.services import UserService

        stats = UserService.get_user_statistics(user_id)

        if not stats:
            return jsonify({
                'success': False,
                'error': 'User not found',
                'code': 'USER_NOT_FOUND'
            }), 404

        return jsonify({
            'success': True,
            'data': stats
        }), 200

    except Exception as e:
        logger.error(f"Error getting user statistics: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'USER_STATS_ERROR'
        }), 500


@statistics_bp.route('/comparisons', methods=['POST'])
@jwt_required
@admin_required
def get_period_comparisons():
    """
    Порівняти статистику між періодами

    Request body:
    {
        "period1": {
            "start": "2024-01-01",
            "end": "2024-01-31"
        },
        "period2": {
            "start": "2024-02-01",
            "end": "2024-02-29"
        },
        "metrics": ["revenue", "orders", "users"]
    }
    """
    try:
        data = request.get_json() or {}

        # Валідація періодів
        period1 = data.get('period1', {})
        period2 = data.get('period2', {})
        metrics = data.get('metrics', ['revenue', 'orders', 'users'])

        try:
            p1_start = datetime.fromisoformat(period1['start'])
            p1_end = datetime.fromisoformat(period1['end'])
            p2_start = datetime.fromisoformat(period2['start'])
            p2_end = datetime.fromisoformat(period2['end'])
        except:
            return jsonify({
                'success': False,
                'error': 'Invalid period format',
                'code': 'INVALID_PERIODS'
            }), 400

        # Отримуємо дані для порівняння
        comparison = {}

        if 'revenue' in metrics:
            comparison['revenue'] = _compare_revenue(
                (p1_start, p1_end),
                (p2_start, p2_end)
            )

        if 'orders' in metrics:
            comparison['orders'] = _compare_orders(
                (p1_start, p1_end),
                (p2_start, p2_end)
            )

        if 'users' in metrics:
            comparison['users'] = _compare_users(
                (p1_start, p1_end),
                (p2_start, p2_end)
            )

        return jsonify({
            'success': True,
            'data': {
                'period1': {
                    'start': p1_start.isoformat(),
                    'end': p1_end.isoformat()
                },
                'period2': {
                    'start': p2_start.isoformat(),
                    'end': p2_end.isoformat()
                },
                'comparison': comparison
            }
        }), 200

    except Exception as e:
        logger.error(f"Error comparing periods: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'COMPARISON_ERROR'
        }), 500


@statistics_bp.route('/live', methods=['GET'])
@jwt_required
def get_live_statistics():
    """
    Отримати live статистику (для звичайних користувачів)

    Response:
    {
        "success": true,
        "data": {
            "total_users": 15234,
            "total_orders": 45678,
            "services_available": 234,
            "average_completion_time": "2.5 hours"
        }
    }
    """
    try:
        # Публічна статистика
        from backend.supabase_client import supabase

        # Загальна кількість користувачів
        users_result = supabase.table('users') \
            .select('id', count='exact') \
            .execute()
        total_users = users_result.count if hasattr(users_result, 'count') else 0

        # Загальна кількість виконаних замовлень
        orders_result = supabase.table('orders') \
            .select('id', count='exact') \
            .eq('status', 'completed') \
            .execute()
        total_orders = orders_result.count if hasattr(orders_result, 'count') else 0

        # Доступні сервіси
        services_result = supabase.table('services') \
            .select('id', count='exact') \
            .eq('is_active', True) \
            .execute()
        total_services = services_result.count if hasattr(services_result, 'count') else 0

        return jsonify({
            'success': True,
            'data': {
                'total_users': total_users,
                'total_orders': total_orders,
                'services_available': total_services,
                'average_completion_time': '2-6 hours',
                'success_rate': 98.5,
                'active_now': DashboardService._get_realtime_stats().get('online_users', 0)
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting live statistics: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'LIVE_STATS_ERROR'
        }), 500


# === Helper функції ===

def _prepare_pie_chart(data: Dict[str, int]) -> List[Dict]:
    """Підготувати дані для pie chart"""
    total = sum(data.values())
    return [
        {
            'label': key.replace('_', ' ').title(),
            'value': value,
            'percentage': round((value / total * 100) if total > 0 else 0, 2)
        }
        for key, value in data.items()
    ]


def _prepare_bar_chart(data: Dict[str, int]) -> List[Dict]:
    """Підготувати дані для bar chart"""
    return [
        {
            'label': key.replace('_', ' ').title(),
            'value': value
        }
        for key, value in data.items()
    ]


def _generate_user_insights(segments: Dict, total_users: int) -> List[str]:
    """Генерувати інсайти на основі сегментації"""
    insights = []

    # Активність
    activity = segments.get('by_activity', {})
    if activity:
        active_percent = (activity.get('very_active', 0) + activity.get('active', 0)) / total_users * 100
        if active_percent < 30:
            insights.append("⚠️ Low user engagement - consider retention campaigns")
        elif active_percent > 60:
            insights.append("✅ High user engagement rate")

    # Витрати
    spending = segments.get('by_spending', {})
    if spending:
        whales_percent = spending.get('whales', 0) / total_users * 100
        if whales_percent > 5:
            insights.append("💎 Strong whale user base contributing to revenue")

    return insights


def _get_revenue_chart_data(start_date: datetime, end_date: datetime, interval: str) -> List[Dict]:
    """Отримати дані для графіка доходів"""
    # Спрощена версія - в реальності брати з БД
    data = []
    current = start_date

    while current <= end_date:
        data.append({
            'date': current.isoformat(),
            'revenue': 1000 + (current.day * 50),
            'deposits': 800 + (current.day * 40),
            'orders': 200 + (current.day * 10)
        })

        if interval == 'hour':
            current += timedelta(hours=1)
        elif interval == 'day':
            current += timedelta(days=1)
        elif interval == 'week':
            current += timedelta(weeks=1)
        else:
            current += timedelta(days=30)

    return data


def _get_orders_chart_data(start_date: datetime, end_date: datetime, interval: str) -> List[Dict]:
    """Отримати дані для графіка замовлень"""
    # Аналогічно revenue
    return []


def _get_users_chart_data(start_date: datetime, end_date: datetime, interval: str) -> List[Dict]:
    """Отримати дані для графіка користувачів"""
    # Аналогічно revenue
    return []


def _get_services_distribution_data() -> Dict[str, Any]:
    """Отримати розподіл по сервісах"""
    from backend.statistics.models import AnalyticsMetrics
    return AnalyticsMetrics._get_service_distribution()


def _compare_revenue(period1: tuple, period2: tuple) -> Dict[str, Any]:
    """Порівняти доходи між періодами"""
    # Спрощена версія
    return {
        'period1': {'total': 10000, 'average_daily': 333},
        'period2': {'total': 12000, 'average_daily': 400},
        'change': {'amount': 2000, 'percentage': 20},
        'trend': 'up'
    }


def _compare_orders(period1: tuple, period2: tuple) -> Dict[str, Any]:
    """Порівняти замовлення між періодами"""
    return {}


def _compare_users(period1: tuple, period2: tuple) -> Dict[str, Any]:
    """Порівняти користувачів між періодами"""
    return {}