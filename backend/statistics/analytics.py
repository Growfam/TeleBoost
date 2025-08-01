# backend/statistics/analytics.py
"""
TeleBoost Analytics Services
Сервіси для збору та обробки аналітики
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import pandas as pd
import numpy as np

from backend.statistics.models import SystemMetrics, AnalyticsMetrics, UserAnalytics, MetricPeriod
from backend.supabase_client import supabase
from backend.utils.redis_client import redis_client, cache_get, cache_set
from backend.utils.constants import ORDER_STATUS, TRANSACTION_TYPE, SERVICE_TYPE
from backend.utils.formatters import format_price, format_datetime

logger = logging.getLogger(__name__)


class DashboardService:
    """Сервіс для адмін дашборду"""

    @staticmethod
    def get_admin_dashboard() -> Dict[str, Any]:
        """Отримати повну статистику для адмін панелі"""
        try:
            # Кешуємо на 2 хвилини
            cache_key = "dashboard:admin:overview"
            cached = cache_get(cache_key, data_type='json')
            if cached:
                return cached

            dashboard = {
                'overview': SystemMetrics.get_overview_metrics(),
                'real_time': DashboardService._get_realtime_stats(),
                'alerts': DashboardService._get_system_alerts(),
                'quick_stats': DashboardService._get_quick_stats(),
                'activity_feed': DashboardService._get_activity_feed(),
                'trends': DashboardService._get_trends(),
                'last_updated': datetime.utcnow().isoformat()
            }

            cache_set(cache_key, dashboard, ttl=120)

            return dashboard

        except Exception as e:
            logger.error(f"Error getting admin dashboard: {e}")
            return {}

    @staticmethod
    def _get_realtime_stats() -> Dict[str, Any]:
        """Статистика в реальному часі"""
        try:
            # Онлайн користувачі (активні за останні 5 хвилин)
            five_min_ago = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
            online_result = supabase.table('user_activities') \
                .select('user_id', count='exact') \
                .gte('created_at', five_min_ago) \
                .execute()
            online_users = online_result.count if hasattr(online_result, 'count') else 0

            # Активні замовлення
            active_orders_result = supabase.table('orders') \
                .select('id, charge') \
                .in_('status', ['pending', 'processing', 'in_progress']) \
                .execute()
            active_orders = active_orders_result.data or []

            # Останні транзакції
            recent_transactions = supabase.table('transactions') \
                .select('*') \
                .order('created_at', desc=True) \
                .limit(10) \
                .execute()

            return {
                'online_users': online_users,
                'active_orders_count': len(active_orders),
                'active_orders_value': round(sum(float(o['charge']) for o in active_orders), 2),
                'recent_transactions': [
                    {
                        'id': t['id'][:8],
                        'type': t['type'],
                        'amount': float(t['amount']),
                        'time_ago': DashboardService._time_ago(t['created_at'])
                    }
                    for t in (recent_transactions.data or [])[:5]
                ]
            }

        except Exception as e:
            logger.error(f"Error getting realtime stats: {e}")
            return {}

    @staticmethod
    def _get_system_alerts() -> List[Dict]:
        """Системні попередження"""
        alerts = []

        try:
            # Перевірка балансу Nakrutochka
            from backend.api.nakrutochka_api import nakrutochka
            balance_result = nakrutochka.get_balance()
            if balance_result.get('success'):
                balance = balance_result.get('balance', 0)
                if balance < 100:
                    alerts.append({
                        'type': 'critical',
                        'title': 'Low Nakrutochka Balance',
                        'message': f'Balance is ${balance:.2f}. Please top up.',
                        'timestamp': datetime.utcnow().isoformat()
                    })

            # Перевірка failed orders
            failed_today = supabase.table('orders') \
                .select('id', count='exact') \
                .eq('status', ORDER_STATUS.FAILED) \
                .gte('created_at', datetime.utcnow().date().isoformat()) \
                .execute()
            failed_count = failed_today.count if hasattr(failed_today, 'count') else 0

            if failed_count > 10:
                alerts.append({
                    'type': 'warning',
                    'title': 'High Failed Orders Rate',
                    'message': f'{failed_count} orders failed today',
                    'timestamp': datetime.utcnow().isoformat()
                })

            # Перевірка Redis
            if not redis_client.ping():
                alerts.append({
                    'type': 'error',
                    'title': 'Redis Connection Lost',
                    'message': 'Cache system is unavailable',
                    'timestamp': datetime.utcnow().isoformat()
                })

        except Exception as e:
            logger.error(f"Error getting system alerts: {e}")

        return alerts

    @staticmethod
    def _get_quick_stats() -> Dict[str, Any]:
        """Швидкі статистики за періоди"""
        try:
            now = datetime.utcnow()
            today = now.date()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            # Доходи
            revenue_today = DashboardService._get_revenue_for_period(today.isoformat(), now.isoformat())
            revenue_week = DashboardService._get_revenue_for_period(week_ago.isoformat(), now.isoformat())
            revenue_month = DashboardService._get_revenue_for_period(month_ago.isoformat(), now.isoformat())

            # Замовлення
            orders_today = DashboardService._get_orders_count_for_period(today.isoformat(), now.isoformat())
            orders_week = DashboardService._get_orders_count_for_period(week_ago.isoformat(), now.isoformat())
            orders_month = DashboardService._get_orders_count_for_period(month_ago.isoformat(), now.isoformat())

            # Нові користувачі
            users_today = DashboardService._get_new_users_for_period(today.isoformat(), now.isoformat())
            users_week = DashboardService._get_new_users_for_period(week_ago.isoformat(), now.isoformat())
            users_month = DashboardService._get_new_users_for_period(month_ago.isoformat(), now.isoformat())

            # Порівняння з вчора
            yesterday = (today - timedelta(days=1))
            revenue_yesterday = DashboardService._get_revenue_for_period(
                yesterday.isoformat(),
                today.isoformat()
            )

            return {
                'revenue': {
                    'today': revenue_today,
                    'week': revenue_week,
                    'month': revenue_month,
                    'today_vs_yesterday': DashboardService._calculate_change(revenue_today, revenue_yesterday)
                },
                'orders': {
                    'today': orders_today,
                    'week': orders_week,
                    'month': orders_month,
                    'avg_today': round(revenue_today / orders_today if orders_today > 0 else 0, 2)
                },
                'users': {
                    'today': users_today,
                    'week': users_week,
                    'month': users_month,
                    'conversion_rate': 15.5  # Можна розрахувати реальну конверсію
                }
            }

        except Exception as e:
            logger.error(f"Error getting quick stats: {e}")
            return {}

    @staticmethod
    def _get_activity_feed() -> List[Dict]:
        """Стрічка активності"""
        try:
            activities = []

            # Останні замовлення
            recent_orders = supabase.table('orders') \
                .select('*, users!user_id(username, telegram_id)') \
                .order('created_at', desc=True) \
                .limit(5) \
                .execute()

            for order in (recent_orders.data or []):
                user = order.get('users', {})
                activities.append({
                    'type': 'order',
                    'message': f"{user.get('username', 'User')} created order #{order['id'][:8]}",
                    'amount': float(order['charge']),
                    'time': DashboardService._time_ago(order['created_at'])
                })

            # Останні депозити
            recent_deposits = supabase.table('transactions') \
                .select('*, users!user_id(username)') \
                .eq('type', TRANSACTION_TYPE.DEPOSIT) \
                .order('created_at', desc=True) \
                .limit(5) \
                .execute()

            for deposit in (recent_deposits.data or []):
                user = deposit.get('users', {})
                activities.append({
                    'type': 'deposit',
                    'message': f"{user.get('username', 'User')} deposited",
                    'amount': float(deposit['amount']),
                    'time': DashboardService._time_ago(deposit['created_at'])
                })

            # Сортуємо по часу
            activities.sort(key=lambda x: x['time'], reverse=False)

            return activities[:10]

        except Exception as e:
            logger.error(f"Error getting activity feed: {e}")
            return []

    @staticmethod
    def _get_trends() -> Dict[str, Any]:
        """Тренди та порівняння"""
        try:
            # Порівняння з минулим тижнем
            now = datetime.utcnow()
            this_week_start = now - timedelta(days=now.weekday())
            last_week_start = this_week_start - timedelta(days=7)
            last_week_end = this_week_start

            # Доходи
            this_week_revenue = DashboardService._get_revenue_for_period(
                this_week_start.isoformat(),
                now.isoformat()
            )
            last_week_revenue = DashboardService._get_revenue_for_period(
                last_week_start.isoformat(),
                last_week_end.isoformat()
            )

            revenue_change = DashboardService._calculate_change(this_week_revenue, last_week_revenue)

            # Найкращий день (використовуємо RPC функцію)
            daily_stats = supabase.client.rpc('get_daily_statistics', {
                'start_date': this_week_start.date().isoformat(),
                'end_date': now.date().isoformat()
            }).execute()

            best_day = 'Monday'
            if daily_stats.data:
                best_day_data = max(daily_stats.data, key=lambda x: x['total_revenue'])
                best_day = datetime.fromisoformat(best_day_data['date']).strftime('%A')

            return {
                'revenue': {
                    'current': this_week_revenue,
                    'previous': last_week_revenue,
                    'change': revenue_change,
                    'trend': 'up' if revenue_change > 0 else 'down' if revenue_change < 0 else 'stable'
                },
                'best_day': best_day,
                'peak_hours': [14, 15, 20, 21],  # Можна розрахувати з user_activities
                'growth_rate': revenue_change
            }

        except Exception as e:
            logger.error(f"Error getting trends: {e}")
            return {}

    @staticmethod
    def _get_revenue_for_period(start: str, end: str) -> float:
        """Отримати дохід за період"""
        try:
            result = supabase.table('transactions') \
                .select('amount') \
                .eq('type', TRANSACTION_TYPE.DEPOSIT) \
                .gte('created_at', start) \
                .lte('created_at', end) \
                .execute()

            return sum(float(t['amount']) for t in (result.data or []))

        except:
            return 0.0

    @staticmethod
    def _get_orders_count_for_period(start: str, end: str) -> int:
        """Отримати кількість замовлень за період"""
        try:
            result = supabase.table('orders') \
                .select('id', count='exact') \
                .gte('created_at', start) \
                .lte('created_at', end) \
                .execute()

            return result.count if hasattr(result, 'count') else 0

        except:
            return 0

    @staticmethod
    def _get_new_users_for_period(start: str, end: str) -> int:
        """Отримати кількість нових користувачів за період"""
        try:
            result = supabase.table('users') \
                .select('id', count='exact') \
                .gte('created_at', start) \
                .lte('created_at', end) \
                .execute()

            return result.count if hasattr(result, 'count') else 0

        except:
            return 0

    @staticmethod
    def _calculate_change(current: float, previous: float) -> float:
        """Розрахувати зміну у відсотках"""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 2)

    @staticmethod
    def _time_ago(timestamp: str) -> str:
        """Конвертувати timestamp в 'X хвилин тому'"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            delta = datetime.utcnow() - dt.replace(tzinfo=None)

            if delta.days > 0:
                return f"{delta.days}d ago"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600}h ago"
            elif delta.seconds > 60:
                return f"{delta.seconds // 60}m ago"
            else:
                return "just now"

        except:
            return "unknown"


class ReportGenerator:
    """Генератор звітів"""

    @staticmethod
    def generate_financial_report(start_date: datetime, end_date: datetime,
                                  format: str = 'json') -> Dict[str, Any]:
        """Генерувати фінансовий звіт"""
        try:
            logger.info(f"Generating financial report from {start_date} to {end_date}")

            report = {
                'metadata': {
                    'title': 'Financial Report',
                    'period': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat()
                    },
                    'generated_at': datetime.utcnow().isoformat(),
                    'currency': 'USD'
                },
                'summary': ReportGenerator._get_financial_summary(start_date, end_date),
                'revenue_breakdown': ReportGenerator._get_revenue_breakdown(start_date, end_date),
                'expense_breakdown': ReportGenerator._get_expense_breakdown(start_date, end_date),
                'daily_data': ReportGenerator._get_daily_financial_data(start_date, end_date),
                'top_performers': ReportGenerator._get_top_performers(start_date, end_date),
                'service_performance': ReportGenerator._get_service_performance(start_date, end_date),
                'projections': ReportGenerator._calculate_financial_projections(start_date, end_date)
            }

            if format == 'csv':
                return ReportGenerator._convert_to_csv(report)
            elif format == 'excel':
                return ReportGenerator._convert_to_excel(report)
            else:
                return report

        except Exception as e:
            logger.error(f"Error generating financial report: {e}")
            return {}

    @staticmethod
    def _get_financial_summary(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Фінансове резюме"""
        try:
            # Доходи
            deposits = supabase.table('transactions') \
                .select('amount') \
                .eq('type', TRANSACTION_TYPE.DEPOSIT) \
                .gte('created_at', start_date.isoformat()) \
                .lte('created_at', end_date.isoformat()) \
                .execute()
            total_deposits = sum(float(t['amount']) for t in (deposits.data or []))

            # Витрати
            withdrawals = supabase.table('transactions') \
                .select('amount') \
                .eq('type', TRANSACTION_TYPE.WITHDRAWAL) \
                .gte('created_at', start_date.isoformat()) \
                .lte('created_at', end_date.isoformat()) \
                .execute()
            total_withdrawals = sum(abs(float(t['amount'])) for t in (withdrawals.data or []))

            # Замовлення
            orders = supabase.table('orders') \
                .select('charge') \
                .eq('status', ORDER_STATUS.COMPLETED) \
                .gte('created_at', start_date.isoformat()) \
                .lte('created_at', end_date.isoformat()) \
                .execute()
            total_order_revenue = sum(float(o['charge']) for o in (orders.data or []))

            # Прибуток (30% від замовлень)
            estimated_profit = total_order_revenue * 0.30

            # Реферальні виплати
            referral_bonuses = supabase.table('transactions') \
                .select('amount') \
                .eq('type', TRANSACTION_TYPE.REFERRAL_BONUS) \
                .gte('created_at', start_date.isoformat()) \
                .lte('created_at', end_date.isoformat()) \
                .execute()
            total_referral_payouts = sum(float(t['amount']) for t in (referral_bonuses.data or []))

            net_profit = estimated_profit - total_referral_payouts

            # Середня вартість замовлення (використовуємо RPC функцію)
            avg_order_result = supabase.client.rpc('calculate_average_order_value').execute()
            avg_order_value = float(avg_order_result.data) if avg_order_result.data else 0

            return {
                'total_revenue': round(total_deposits, 2),
                'total_order_revenue': round(total_order_revenue, 2),
                'total_withdrawals': round(total_withdrawals, 2),
                'total_referral_payouts': round(total_referral_payouts, 2),
                'gross_profit': round(estimated_profit, 2),
                'net_profit': round(net_profit, 2),
                'profit_margin': round((net_profit / total_order_revenue * 100) if total_order_revenue > 0 else 0, 2),
                'average_order_value': round(avg_order_value, 2)
            }

        except Exception as e:
            logger.error(f"Error getting financial summary: {e}")
            return {}

    @staticmethod
    def _get_revenue_breakdown(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Розбивка доходів"""
        try:
            # По типах транзакцій
            breakdown = {}

            for trans_type in [TRANSACTION_TYPE.DEPOSIT, TRANSACTION_TYPE.REFERRAL_BONUS]:
                result = supabase.table('transactions') \
                    .select('amount') \
                    .eq('type', trans_type) \
                    .gte('created_at', start_date.isoformat()) \
                    .lte('created_at', end_date.isoformat()) \
                    .execute()

                total = sum(float(t['amount']) for t in (result.data or []) if t['amount'] > 0)
                breakdown[trans_type] = round(total, 2)

            # По платіжних системах
            payment_systems = {}
            payments_result = supabase.table('payments') \
                .select('provider, amount') \
                .eq('type', 'deposit') \
                .eq('status', 'finished') \
                .gte('created_at', start_date.isoformat()) \
                .lte('created_at', end_date.isoformat()) \
                .execute()

            for payment in (payments_result.data or []):
                provider = payment['provider']
                amount = float(payment['amount'])
                payment_systems[provider] = payment_systems.get(provider, 0) + amount

            return {
                'by_type': breakdown,
                'by_payment_system': {k: round(v, 2) for k, v in payment_systems.items()},
                'total': round(sum(breakdown.values()), 2)
            }

        except Exception as e:
            logger.error(f"Error getting revenue breakdown: {e}")
            return {}

    @staticmethod
    def _get_expense_breakdown(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Розбивка витрат"""
        try:
            breakdown = {
                'withdrawals': 0,
                'refunds': 0,
                'referral_bonuses': 0,
                'service_costs': 0  # 70% від вартості замовлень
            }

            # Виведення
            withdrawals = supabase.table('transactions') \
                .select('amount') \
                .eq('type', TRANSACTION_TYPE.WITHDRAWAL) \
                .gte('created_at', start_date.isoformat()) \
                .lte('created_at', end_date.isoformat()) \
                .execute()
            breakdown['withdrawals'] = sum(abs(float(t['amount'])) for t in (withdrawals.data or []))

            # Повернення
            refunds = supabase.table('transactions') \
                .select('amount') \
                .eq('type', TRANSACTION_TYPE.REFUND) \
                .gte('created_at', start_date.isoformat()) \
                .lte('created_at', end_date.isoformat()) \
                .execute()
            breakdown['refunds'] = sum(float(t['amount']) for t in (refunds.data or []))

            # Реферальні бонуси
            referrals = supabase.table('transactions') \
                .select('amount') \
                .eq('type', TRANSACTION_TYPE.REFERRAL_BONUS) \
                .gte('created_at', start_date.isoformat()) \
                .lte('created_at', end_date.isoformat()) \
                .execute()
            breakdown['referral_bonuses'] = sum(float(t['amount']) for t in (referrals.data or []))

            # Вартість сервісів (70% від замовлень)
            orders = supabase.table('orders') \
                .select('charge') \
                .eq('status', ORDER_STATUS.COMPLETED) \
                .gte('created_at', start_date.isoformat()) \
                .lte('created_at', end_date.isoformat()) \
                .execute()
            total_orders = sum(float(o['charge']) for o in (orders.data or []))
            breakdown['service_costs'] = total_orders * 0.70

            return {
                'breakdown': {k: round(v, 2) for k, v in breakdown.items()},
                'total': round(sum(breakdown.values()), 2)
            }

        except Exception as e:
            logger.error(f"Error getting expense breakdown: {e}")
            return {}

    @staticmethod
    def _get_daily_financial_data(start_date: datetime, end_date: datetime) -> List[Dict]:
        """Щоденні фінансові дані"""
        try:
            # Використовуємо RPC функцію get_daily_statistics
            result = supabase.client.rpc('get_daily_statistics', {
                'start_date': start_date.date().isoformat(),
                'end_date': end_date.date().isoformat()
            }).execute()

            if not result.data:
                return []

            daily_data = []
            for row in result.data:
                daily_data.append({
                    'date': row['date'],
                    'revenue': round(float(row['total_revenue']), 2),
                    'orders_count': row['completed_orders'],
                    'orders_value': round(float(row['total_revenue']), 2),
                    'average_order': round(
                        float(row['total_revenue']) / row['completed_orders']
                        if row['completed_orders'] > 0 else 0,
                        2
                    ),
                    'deposits': round(float(row['total_deposits']), 2),
                    'withdrawals': round(float(row['total_withdrawals']), 2),
                    'new_users': row['new_users']
                })

            return daily_data

        except Exception as e:
            logger.error(f"Error getting daily financial data: {e}")
            return []

    @staticmethod
    def _get_top_performers(start_date: datetime, end_date: datetime) -> Dict[str, List]:
        """Топ користувачів та сервісів"""
        try:
            # Топ користувачів по витратах (використовуємо RPC функцію)
            top_users_result = supabase.client.rpc('get_top_spenders_for_period', {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'limit_count': 10
            }).execute()

            top_users = []
            if top_users_result.data:
                for user in top_users_result.data:
                    top_users.append({
                        'user_id': user['user_id'],
                        'username': user.get('username', 'Unknown'),
                        'total_spent': round(float(user['total_spent']), 2),
                        'orders_count': user['orders_count']
                    })

            # Топ сервісів (використовуємо RPC функцію)
            top_services_result = supabase.client.rpc('get_top_services_for_period', {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'limit_count': 10
            }).execute()

            top_services = []
            if top_services_result.data:
                for service in top_services_result.data:
                    top_services.append({
                        'service_id': service['service_id'],
                        'name': service.get('service_name', 'Unknown Service'),
                        'orders_count': service['orders_count'],
                        'revenue': round(float(service['total_revenue']), 2)
                    })

            return {
                'users': top_users,
                'services': top_services
            }

        except Exception as e:
            logger.error(f"Error getting top performers: {e}")
            return {'users': [], 'services': []}

    @staticmethod
    def _get_service_performance(start_date: datetime, end_date: datetime) -> List[Dict]:
        """Продуктивність сервісів"""
        try:
            # Групуємо замовлення по категоріях
            orders_result = supabase.table('orders') \
                .select('service_id, charge, status, metadata') \
                .gte('created_at', start_date.isoformat()) \
                .lte('created_at', end_date.isoformat()) \
                .execute()

            categories = {}

            for order in (orders_result.data or []):
                category = order.get('metadata', {}).get('service_category', 'other')

                if category not in categories:
                    categories[category] = {
                        'total_orders': 0,
                        'completed_orders': 0,
                        'revenue': 0,
                        'failed_orders': 0
                    }

                categories[category]['total_orders'] += 1
                categories[category]['revenue'] += float(order['charge'])

                if order['status'] == ORDER_STATUS.COMPLETED:
                    categories[category]['completed_orders'] += 1
                elif order['status'] == ORDER_STATUS.FAILED:
                    categories[category]['failed_orders'] += 1

            # Форматуємо результат
            performance = []
            for category, data in categories.items():
                performance.append({
                    'category': category,
                    'orders_count': data['total_orders'],
                    'completion_rate': round(
                        (data['completed_orders'] / data['total_orders'] * 100)
                        if data['total_orders'] > 0 else 0,
                        2
                    ),
                    'failure_rate': round(
                        (data['failed_orders'] / data['total_orders'] * 100)
                        if data['total_orders'] > 0 else 0,
                        2
                    ),
                    'revenue': round(data['revenue'], 2),
                    'average_order': round(
                        data['revenue'] / data['total_orders']
                        if data['total_orders'] > 0 else 0,
                        2
                    )
                })

            return sorted(performance, key=lambda x: x['revenue'], reverse=True)

        except Exception as e:
            logger.error(f"Error getting service performance: {e}")
            return []

    @staticmethod
    def _calculate_financial_projections(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Розрахунок прогнозів"""
        try:
            # Отримуємо щоденні дані через RPC функцію
            daily_result = supabase.client.rpc('get_daily_statistics', {
                'start_date': start_date.date().isoformat(),
                'end_date': end_date.date().isoformat()
            }).execute()

            if not daily_result.data:
                return {}

            # Конвертуємо в pandas для аналізу
            df = pd.DataFrame(daily_result.data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')

            # Розраховуємо тренди
            revenue_trend = np.polyfit(range(len(df)), df['total_revenue'].astype(float), 1)[0]
            orders_trend = np.polyfit(range(len(df)), df['completed_orders'].astype(float), 1)[0]

            # Середні значення
            avg_daily_revenue = float(df['total_revenue'].astype(float).mean())
            avg_daily_orders = float(df['completed_orders'].astype(float).mean())

            # Прогнози
            days_ahead = 30
            projected_revenue = avg_daily_revenue + (revenue_trend * days_ahead)
            projected_orders = avg_daily_orders + (orders_trend * days_ahead)

            return {
                'current_trends': {
                    'revenue_trend': 'growing' if revenue_trend > 0 else 'declining',
                    'orders_trend': 'growing' if orders_trend > 0 else 'declining',
                    'daily_growth_rate': round(revenue_trend, 2)
                },
                'averages': {
                    'daily_revenue': round(avg_daily_revenue, 2),
                    'daily_orders': round(avg_daily_orders, 2),
                    'revenue_per_order': round(avg_daily_revenue / avg_daily_orders if avg_daily_orders > 0 else 0, 2)
                },
                'projections_30_days': {
                    'expected_revenue': round(projected_revenue * 30, 2),
                    'expected_orders': round(projected_orders * 30),
                    'confidence': 'medium' if len(df) > 14 else 'low'
                }
            }

        except Exception as e:
            logger.error(f"Error calculating projections: {e}")
            return {}

    @staticmethod
    def _convert_to_csv(report: Dict) -> str:
        """Конвертувати звіт в CSV"""
        csv_lines = []
        csv_lines.append("TeleBoost Financial Report")
        csv_lines.append(f"Period: {report['metadata']['period']['start']} to {report['metadata']['period']['end']}")
        csv_lines.append("")

        # Summary
        csv_lines.append("FINANCIAL SUMMARY")
        for key, value in report['summary'].items():
            csv_lines.append(f"{key.replace('_', ' ').title()},{value}")
        csv_lines.append("")

        # Revenue Breakdown
        csv_lines.append("REVENUE BREAKDOWN")
        csv_lines.append("Type,Amount")
        for key, value in report['revenue_breakdown']['by_type'].items():
            csv_lines.append(f"{key},{value}")
        csv_lines.append("")

        # Daily Data
        csv_lines.append("DAILY PERFORMANCE")
        csv_lines.append("Date,Revenue,Orders,Deposits,Withdrawals")
        for day in report['daily_data']:
            csv_lines.append(f"{day['date']},{day['revenue']},{day['orders_count']},{day['deposits']},{day['withdrawals']}")

        return "\n".join(csv_lines)

    @staticmethod
    def _convert_to_excel(report: Dict) -> bytes:
        """Конвертувати звіт в Excel"""
        # Потребує openpyxl або xlsxwriter
        # Тимчасово повертаємо заглушку
        return b"Excel file content - install openpyxl to generate real Excel files"


class MetricsExporter:
    """Експорт метрик для моніторингу"""

    @staticmethod
    def export_prometheus_metrics() -> str:
        """Експорт метрик в форматі Prometheus"""
        try:
            metrics = SystemMetrics.get_overview_metrics()

            prometheus_metrics = []

            # Users metrics
            if 'users' in metrics:
                prometheus_metrics.append(f'teleboost_users_total {metrics["users"]["total"]}')
                prometheus_metrics.append(f'teleboost_users_active {metrics["users"]["active"]}')
                prometheus_metrics.append(f'teleboost_users_vip {metrics["users"]["vip"]}')

            # Orders metrics
            if 'orders' in metrics:
                prometheus_metrics.append(f'teleboost_orders_total {metrics["orders"]["total"]}')
                prometheus_metrics.append(f'teleboost_orders_active {metrics["orders"]["active_orders"]}')
                prometheus_metrics.append(f'teleboost_orders_today {metrics["orders"]["today_count"]}')

            # Revenue metrics
            if 'revenue' in metrics:
                prometheus_metrics.append(f'teleboost_revenue_total {metrics["revenue"]["total_deposits"]}')
                prometheus_metrics.append(f'teleboost_revenue_today {metrics["revenue"]["today_revenue"]}')
                prometheus_metrics.append(f'teleboost_profit_estimated {metrics["revenue"]["estimated_profit"]}')

            # Performance metrics
            if 'performance' in metrics and 'cache' in metrics['performance']:
                cache = metrics['performance']['cache']
                prometheus_metrics.append(f'teleboost_cache_hit_rate {cache.get("hit_rate", 0)}')
                prometheus_metrics.append(f'teleboost_cache_memory_mb {cache.get("used_memory_mb", 0)}')

            return '\n'.join(prometheus_metrics)

        except Exception as e:
            logger.error(f"Error exporting Prometheus metrics: {e}")
            return ""

    @staticmethod
    def export_json_metrics() -> Dict[str, Any]:
        """Експорт метрик в JSON форматі"""
        try:
            return {
                'system': SystemMetrics.get_overview_metrics(),
                'analytics': AnalyticsMetrics.get_financial_analytics(MetricPeriod.DAY),
                'users': UserAnalytics.get_user_segments(),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error exporting JSON metrics: {e}")
            return {}