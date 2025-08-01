# backend/statistics/models.py
"""
TeleBoost Statistics Models
Моделі для збору та зберігання статистики
"""
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from backend.supabase_client import supabase
from backend.utils.redis_client import redis_client, cache_get, cache_set
from backend.utils.constants import (
    ORDER_STATUS, PAYMENT_STATUS, TRANSACTION_TYPE,
    CACHE_TTL, SERVICE_TYPE
)

logger = logging.getLogger(__name__)


class MetricPeriod(Enum):
    """Періоди для метрик"""
    HOUR = 'hour'
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    QUARTER = 'quarter'
    YEAR = 'year'
    ALL_TIME = 'all_time'


@dataclass
class MetricData:
    """Дані метрики"""
    value: float
    previous_value: Optional[float] = None
    change_percent: Optional[float] = None
    trend: Optional[str] = None  # up, down, stable

    def calculate_change(self):
        """Розрахувати зміну у відсотках"""
        if self.previous_value and self.previous_value > 0:
            change = ((self.value - self.previous_value) / self.previous_value) * 100
            self.change_percent = round(change, 2)

            if change > 0:
                self.trend = 'up'
            elif change < 0:
                self.trend = 'down'
            else:
                self.trend = 'stable'


class SystemMetrics:
    """Системні метрики"""

    @staticmethod
    def get_overview_metrics() -> Dict[str, Any]:
        """Отримати загальні метрики системи"""
        try:
            # Кешуємо на 5 хвилин
            cache_key = "metrics:system_overview"
            cached = cache_get(cache_key, data_type='json')
            if cached:
                return cached

            metrics = {
                'users': SystemMetrics._get_user_metrics(),
                'orders': SystemMetrics._get_order_metrics(),
                'revenue': SystemMetrics._get_revenue_metrics(),
                'services': SystemMetrics._get_service_metrics(),
                'performance': SystemMetrics._get_performance_metrics(),
                'timestamp': datetime.utcnow().isoformat()
            }

            # Кешуємо
            cache_set(cache_key, metrics, ttl=300)

            return metrics

        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}

    @staticmethod
    def _get_user_metrics() -> Dict[str, Any]:
        """Метрики користувачів"""
        try:
            # Загальна кількість
            total_result = supabase.table('users').select('id', count='exact').execute()
            total_users = total_result.count if hasattr(total_result, 'count') else 0

            # Активні (за останні 7 днів)
            week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            active_result = supabase.table('users') \
                .select('id', count='exact') \
                .gte('last_login', week_ago) \
                .execute()
            active_users = active_result.count if hasattr(active_result, 'count') else 0

            # Нові сьогодні
            today = datetime.utcnow().date().isoformat()
            new_today_result = supabase.table('users') \
                .select('id', count='exact') \
                .gte('created_at', today) \
                .execute()
            new_today = new_today_result.count if hasattr(new_today_result, 'count') else 0

            # VIP користувачі
            vip_result = supabase.table('users') \
                .select('id', count='exact') \
                .eq('role', 'vip') \
                .gte('vip_expires_at', datetime.utcnow().isoformat()) \
                .execute()
            vip_users = vip_result.count if hasattr(vip_result, 'count') else 0

            return {
                'total': total_users,
                'active': active_users,
                'new_today': new_today,
                'vip': vip_users,
                'active_rate': round((active_users / total_users * 100) if total_users > 0 else 0, 2),
                'growth_rate': SystemMetrics._calculate_growth_rate('users')
            }

        except Exception as e:
            logger.error(f"Error getting user metrics: {e}")
            return {}

    @staticmethod
    def _get_order_metrics() -> Dict[str, Any]:
        """Метрики замовлень"""
        try:
            # Всього замовлень
            total_result = supabase.table('orders').select('id', count='exact').execute()
            total_orders = total_result.count if hasattr(total_result, 'count') else 0

            # По статусах
            statuses = {}
            for status in ORDER_STATUS.all():
                result = supabase.table('orders') \
                    .select('id', count='exact') \
                    .eq('status', status) \
                    .execute()
                statuses[status] = result.count if hasattr(result, 'count') else 0

            # Сьогодні
            today = datetime.utcnow().date().isoformat()
            today_result = supabase.table('orders') \
                .select('charge') \
                .gte('created_at', today) \
                .execute()
            today_orders = len(today_result.data or [])
            today_volume = sum(float(o['charge']) for o in (today_result.data or []))

            # Середній чек
            avg_result = supabase.client.rpc('calculate_average_order_value').execute()
            avg_order_value = float(avg_result.data) if avg_result.data else 0

            return {
                'total': total_orders,
                'statuses': statuses,
                'today_count': today_orders,
                'today_volume': round(today_volume, 2),
                'average_value': round(avg_order_value, 2),
                'completion_rate': round(
                    (statuses.get('completed', 0) / total_orders * 100) if total_orders > 0 else 0,
                    2
                ),
                'active_orders': statuses.get('pending', 0) + statuses.get('processing', 0) + statuses.get(
                    'in_progress', 0)
            }

        except Exception as e:
            logger.error(f"Error getting order metrics: {e}")
            return {}

    @staticmethod
    def _get_revenue_metrics() -> Dict[str, Any]:
        """Фінансові метрики"""
        try:
            # Загальний дохід (всі депозити)
            deposits_result = supabase.table('transactions') \
                .select('amount') \
                .eq('type', TRANSACTION_TYPE.DEPOSIT) \
                .execute()
            total_deposits = sum(float(t['amount']) for t in (deposits_result.data or []))

            # Дохід від замовлень (з націнкою)
            orders_result = supabase.table('orders') \
                .select('charge') \
                .eq('status', 'completed') \
                .execute()
            total_orders_revenue = sum(float(o['charge']) for o in (orders_result.data or []))

            # Приблизний прибуток (30% націнка)
            estimated_profit = total_orders_revenue * 0.30

            # Виведення
            withdrawals_result = supabase.table('transactions') \
                .select('amount') \
                .eq('type', TRANSACTION_TYPE.WITHDRAWAL) \
                .execute()
            total_withdrawals = sum(abs(float(t['amount'])) for t in (withdrawals_result.data or []))

            # Реферальні виплати
            referral_result = supabase.table('transactions') \
                .select('amount') \
                .eq('type', TRANSACTION_TYPE.REFERRAL_BONUS) \
                .execute()
            total_referral_payouts = sum(float(t['amount']) for t in (referral_result.data or []))

            # Дохід сьогодні
            today = datetime.utcnow().date().isoformat()
            today_deposits_result = supabase.table('transactions') \
                .select('amount') \
                .eq('type', TRANSACTION_TYPE.DEPOSIT) \
                .gte('created_at', today) \
                .execute()
            today_revenue = sum(float(t['amount']) for t in (today_deposits_result.data or []))

            # Баланси користувачів
            balances_result = supabase.table('users').select('balance').execute()
            total_user_balances = sum(float(u['balance']) for u in (balances_result.data or []))

            return {
                'total_deposits': round(total_deposits, 2),
                'total_orders_revenue': round(total_orders_revenue, 2),
                'estimated_profit': round(estimated_profit, 2),
                'total_withdrawals': round(total_withdrawals, 2),
                'total_referral_payouts': round(total_referral_payouts, 2),
                'today_revenue': round(today_revenue, 2),
                'total_user_balances': round(total_user_balances, 2),
                'net_revenue': round(total_deposits - total_withdrawals, 2),
                'profit_margin': 30.0  # 30% націнка
            }

        except Exception as e:
            logger.error(f"Error getting revenue metrics: {e}")
            return {}

    @staticmethod
    def _get_service_metrics() -> Dict[str, Any]:
        """Метрики по сервісах"""
        try:
            # Активні сервіси
            services_result = supabase.table('services') \
                .select('id, category') \
                .eq('is_active', True) \
                .execute()
            total_services = len(services_result.data or [])

            # По категоріях
            categories = {}
            for service in (services_result.data or []):
                cat = service.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1

            # Топ сервіси по замовленнях
            top_services_result = supabase.client.rpc('get_top_services', {
                'limit_count': 10
            }).execute()

            top_services = []
            if top_services_result.data:
                for item in top_services_result.data:
                    top_services.append({
                        'service_id': item['service_id'],
                        'name': item['service_name'],
                        'orders_count': item['orders_count'],
                        'revenue': round(float(item['total_revenue']), 2)
                    })

            return {
                'total_active': total_services,
                'by_category': categories,
                'top_services': top_services
            }

        except Exception as e:
            logger.error(f"Error getting service metrics: {e}")
            return {}

    @staticmethod
    def _get_performance_metrics() -> Dict[str, Any]:
        """Метрики продуктивності"""
        try:
            # З Redis якщо доступний
            if redis_client.ping():
                info = redis_client.client.info()
                cache_metrics = {
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory_mb': round(info.get('used_memory', 0) / 1024 / 1024, 2),
                    'hits': info.get('keyspace_hits', 0),
                    'misses': info.get('keyspace_misses', 0),
                    'hit_rate': round(
                        (info.get('keyspace_hits', 0) /
                         (info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1)) * 100),
                        2
                    ) if info.get('keyspace_hits', 0) > 0 else 0
                }
            else:
                cache_metrics = {'status': 'unavailable'}

            # Середній час відповіді (з логів або моніторингу)
            avg_response_time = 150  # ms - заглушка

            return {
                'cache': cache_metrics,
                'avg_response_time_ms': avg_response_time,
                'uptime_percent': 99.9,  # заглушка
                'api_calls_today': SystemMetrics._get_api_calls_count()
            }

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}

    @staticmethod
    def _calculate_growth_rate(entity: str) -> float:
        """Розрахувати темп росту"""
        try:
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)

            # Отримуємо кількість за вчора та сьогодні
            if entity == 'users':
                yesterday_result = supabase.table('users') \
                    .select('id', count='exact') \
                    .lt('created_at', today.isoformat()) \
                    .gte('created_at', yesterday.isoformat()) \
                    .execute()
                yesterday_count = yesterday_result.count if hasattr(yesterday_result, 'count') else 0

                today_result = supabase.table('users') \
                    .select('id', count='exact') \
                    .gte('created_at', today.isoformat()) \
                    .execute()
                today_count = today_result.count if hasattr(today_result, 'count') else 0

                if yesterday_count > 0:
                    return round(((today_count - yesterday_count) / yesterday_count) * 100, 2)

            return 0.0

        except:
            return 0.0

    @staticmethod
    def _get_api_calls_count() -> int:
        """Отримати кількість API викликів"""
        # Заглушка - в реальності брати з логів або моніторингу
        return 45678


class AnalyticsMetrics:
    """Аналітичні метрики"""

    @staticmethod
    def get_financial_analytics(period: MetricPeriod = MetricPeriod.MONTH) -> Dict[str, Any]:
        """Отримати фінансову аналітику"""
        try:
            cache_key = f"analytics:financial:{period.value}"
            cached = cache_get(cache_key, data_type='json')
            if cached:
                return cached

            # Визначаємо період
            end_date = datetime.utcnow()
            if period == MetricPeriod.HOUR:
                start_date = end_date - timedelta(hours=24)
                interval = 'hour'
            elif period == MetricPeriod.DAY:
                start_date = end_date - timedelta(days=30)
                interval = 'day'
            elif period == MetricPeriod.WEEK:
                start_date = end_date - timedelta(weeks=12)
                interval = 'week'
            elif period == MetricPeriod.MONTH:
                start_date = end_date - timedelta(days=365)
                interval = 'month'
            else:
                start_date = None
                interval = 'month'

            # Отримуємо дані
            analytics = {
                'revenue_chart': AnalyticsMetrics._get_revenue_chart(start_date, end_date, interval),
                'orders_chart': AnalyticsMetrics._get_orders_chart(start_date, end_date, interval),
                'users_chart': AnalyticsMetrics._get_users_chart(start_date, end_date, interval),
                'top_spenders': AnalyticsMetrics._get_top_spenders(10),
                'service_distribution': AnalyticsMetrics._get_service_distribution(),
                'payment_methods': AnalyticsMetrics._get_payment_methods_stats(),
                'referral_stats': AnalyticsMetrics._get_referral_analytics(),
                'projections': AnalyticsMetrics._calculate_projections()
            }

            # Кешуємо
            ttl = 3600 if period in [MetricPeriod.HOUR, MetricPeriod.DAY] else 21600
            cache_set(cache_key, analytics, ttl=ttl)

            return analytics

        except Exception as e:
            logger.error(f"Error getting financial analytics: {e}")
            return {}

    @staticmethod
    def _get_revenue_chart(start_date: Optional[datetime],
                           end_date: datetime,
                           interval: str) -> List[Dict]:
        """Графік доходів"""
        try:
            # Запит для отримання доходів по періодах
            query = """
                SELECT 
                    date_trunc(%s, created_at) as period,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
                FROM transactions
                WHERE type IN ('deposit', 'order', 'withdrawal', 'referral_bonus')
            """

            params = [interval]

            if start_date:
                query += " AND created_at >= %s"
                params.append(start_date.isoformat())

            query += " GROUP BY period ORDER BY period"

            # В реальності використовувати supabase.client.rpc()
            # Заглушка даних
            data = []
            current = start_date or (end_date - timedelta(days=30))

            while current <= end_date:
                data.append({
                    'date': current.isoformat(),
                    'revenue': 1000 + (current.day * 50),
                    'expenses': 200 + (current.day * 10),
                    'profit': 800 + (current.day * 40)
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

        except Exception as e:
            logger.error(f"Error getting revenue chart: {e}")
            return []

    @staticmethod
    def _get_orders_chart(start_date: Optional[datetime],
                          end_date: datetime,
                          interval: str) -> List[Dict]:
        """Графік замовлень"""
        # Аналогічно revenue_chart
        return []

    @staticmethod
    def _get_users_chart(start_date: Optional[datetime],
                         end_date: datetime,
                         interval: str) -> List[Dict]:
        """Графік реєстрацій користувачів"""
        # Аналогічно revenue_chart
        return []

    @staticmethod
    def _get_top_spenders(limit: int = 10) -> List[Dict]:
        """Топ користувачів по витратах"""
        try:
            result = supabase.client.rpc('get_top_spenders', {
                'limit_count': limit
            }).execute()

            if result.data:
                return [
                    {
                        'user_id': item['user_id'],
                        'username': item['username'],
                        'total_spent': round(float(item['total_spent']), 2),
                        'orders_count': item['orders_count'],
                        'avg_order_value': round(float(item['avg_order_value']), 2)
                    }
                    for item in result.data
                ]

            return []

        except Exception as e:
            logger.error(f"Error getting top spenders: {e}")
            return []

    @staticmethod
    def _get_service_distribution() -> Dict[str, Any]:
        """Розподіл по категоріях сервісів"""
        try:
            result = supabase.table('orders') \
                .select('service_id, charge, metadata') \
                .execute()

            distribution = {}
            total_revenue = 0

            for order in (result.data or []):
                category = order.get('metadata', {}).get('service_category', 'other')
                revenue = float(order['charge'])

                if category not in distribution:
                    distribution[category] = {
                        'count': 0,
                        'revenue': 0
                    }

                distribution[category]['count'] += 1
                distribution[category]['revenue'] += revenue
                total_revenue += revenue

            # Розраховуємо відсотки
            for category, data in distribution.items():
                data['percentage'] = round((data['revenue'] / total_revenue * 100) if total_revenue > 0 else 0, 2)
                data['revenue'] = round(data['revenue'], 2)

            return distribution

        except Exception as e:
            logger.error(f"Error getting service distribution: {e}")
            return {}

    @staticmethod
    def _get_payment_methods_stats() -> Dict[str, Any]:
        """Статистика по методах оплати"""
        try:
            result = supabase.table('payments') \
                .select('provider, amount, status') \
                .eq('type', 'deposit') \
                .eq('status', 'finished') \
                .execute()

            stats = {}
            total_amount = 0

            for payment in (result.data or []):
                provider = payment['provider']
                amount = float(payment['amount'])

                if provider not in stats:
                    stats[provider] = {
                        'count': 0,
                        'total_amount': 0
                    }

                stats[provider]['count'] += 1
                stats[provider]['total_amount'] += amount
                total_amount += amount

            # Розраховуємо відсотки
            for provider, data in stats.items():
                data['percentage'] = round((data['total_amount'] / total_amount * 100) if total_amount > 0 else 0, 2)
                data['total_amount'] = round(data['total_amount'], 2)
                data['avg_amount'] = round(data['total_amount'] / data['count'], 2)

            return stats

        except Exception as e:
            logger.error(f"Error getting payment methods stats: {e}")
            return {}

    @staticmethod
    def _get_referral_analytics() -> Dict[str, Any]:
        """Аналітика реферальної системи"""
        try:
            # Загальна статистика
            referrals_result = supabase.table('referrals') \
                .select('*') \
                .execute()

            total_referrals = len(referrals_result.data or [])
            active_referrals = len([r for r in (referrals_result.data or []) if r.get('is_active')])

            # Бонуси
            bonuses_result = supabase.table('transactions') \
                .select('amount') \
                .eq('type', TRANSACTION_TYPE.REFERRAL_BONUS) \
                .execute()

            total_bonuses = sum(float(t['amount']) for t in (bonuses_result.data or []))

            # Топ реферери
            top_referrers_result = supabase.client.rpc('get_top_referrers', {
                'limit_count': 10
            }).execute()

            return {
                'total_referrals': total_referrals,
                'active_referrals': active_referrals,
                'total_bonuses_paid': round(total_bonuses, 2),
                'conversion_rate': round((active_referrals / total_referrals * 100) if total_referrals > 0 else 0, 2),
                'avg_bonus_per_referral': round(total_bonuses / active_referrals if active_referrals > 0 else 0, 2),
                'top_referrers': top_referrers_result.data or []
            }

        except Exception as e:
            logger.error(f"Error getting referral analytics: {e}")
            return {}

    @staticmethod
    def _calculate_projections() -> Dict[str, Any]:
        """Прогнози на основі трендів"""
        try:
            # Отримуємо дані за останні 30 днів
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            # Доходи
            revenue_result = supabase.table('transactions') \
                .select('amount, created_at') \
                .eq('type', TRANSACTION_TYPE.DEPOSIT) \
                .gte('created_at', thirty_days_ago.isoformat()) \
                .execute()

            daily_revenues = {}
            for t in (revenue_result.data or []):
                date = datetime.fromisoformat(t['created_at'].replace('Z', '+00:00')).date()
                daily_revenues[date] = daily_revenues.get(date, 0) + float(t['amount'])

            # Розраховуємо середній дохід
            avg_daily_revenue = sum(daily_revenues.values()) / len(daily_revenues) if daily_revenues else 0

            # Прогнози
            projections = {
                'next_day': round(avg_daily_revenue * 1.05, 2),  # +5% оптимізм
                'next_week': round(avg_daily_revenue * 7 * 1.05, 2),
                'next_month': round(avg_daily_revenue * 30 * 1.05, 2),
                'growth_trend': 'positive' if avg_daily_revenue > 0 else 'neutral'
            }

            return projections

        except Exception as e:
            logger.error(f"Error calculating projections: {e}")
            return {}


class UserAnalytics:
    """Аналітика користувачів"""

    @staticmethod
    def get_user_segments() -> Dict[str, Any]:
        """Сегментація користувачів"""
        try:
            # Кешуємо на годину
            cache_key = "analytics:user_segments"
            cached = cache_get(cache_key, data_type='json')
            if cached:
                return cached

            segments = {
                'by_activity': UserAnalytics._segment_by_activity(),
                'by_spending': UserAnalytics._segment_by_spending(),
                'by_lifetime': UserAnalytics._segment_by_lifetime(),
                'by_referral': UserAnalytics._segment_by_referral()
            }

            cache_set(cache_key, segments, ttl=3600)

            return segments

        except Exception as e:
            logger.error(f"Error getting user segments: {e}")
            return {}

    @staticmethod
    def _segment_by_activity() -> Dict[str, int]:
        """Сегментація по активності"""
        try:
            now = datetime.utcnow()

            # Дуже активні (заходили сьогодні)
            very_active = supabase.table('users') \
                .select('id', count='exact') \
                .gte('last_login', now.date().isoformat()) \
                .execute()

            # Активні (останні 7 днів)
            active = supabase.table('users') \
                .select('id', count='exact') \
                .gte('last_login', (now - timedelta(days=7)).isoformat()) \
                .lt('last_login', now.date().isoformat()) \
                .execute()

            # Сплячі (7-30 днів)
            dormant = supabase.table('users') \
                .select('id', count='exact') \
                .gte('last_login', (now - timedelta(days=30)).isoformat()) \
                .lt('last_login', (now - timedelta(days=7)).isoformat()) \
                .execute()

            # Неактивні (більше 30 днів)
            inactive = supabase.table('users') \
                .select('id', count='exact') \
                .lt('last_login', (now - timedelta(days=30)).isoformat()) \
                .execute()

            return {
                'very_active': very_active.count if hasattr(very_active, 'count') else 0,
                'active': active.count if hasattr(active, 'count') else 0,
                'dormant': dormant.count if hasattr(dormant, 'count') else 0,
                'inactive': inactive.count if hasattr(inactive, 'count') else 0
            }

        except Exception as e:
            logger.error(f"Error segmenting by activity: {e}")
            return {}

    @staticmethod
    def _segment_by_spending() -> Dict[str, int]:
        """Сегментація по витратах"""
        try:
            # Кити (>$1000)
            whales = supabase.table('users') \
                .select('id', count='exact') \
                .gt('total_spent', 1000) \
                .execute()

            # Дельфіни ($100-$1000)
            dolphins = supabase.table('users') \
                .select('id', count='exact') \
                .gte('total_spent', 100) \
                .lte('total_spent', 1000) \
                .execute()

            # Риби ($10-$100)
            fish = supabase.table('users') \
                .select('id', count='exact') \
                .gte('total_spent', 10) \
                .lt('total_spent', 100) \
                .execute()

            # Планктон (<$10)
            plankton = supabase.table('users') \
                .select('id', count='exact') \
                .lt('total_spent', 10) \
                .execute()

            return {
                'whales': whales.count if hasattr(whales, 'count') else 0,
                'dolphins': dolphins.count if hasattr(dolphins, 'count') else 0,
                'fish': fish.count if hasattr(fish, 'count') else 0,
                'plankton': plankton.count if hasattr(plankton, 'count') else 0
            }

        except Exception as e:
            logger.error(f"Error segmenting by spending: {e}")
            return {}

    @staticmethod
    def _segment_by_lifetime() -> Dict[str, int]:
        """Сегментація по часу життя"""
        try:
            now = datetime.utcnow()

            segments = {
                'new': 0,  # < 7 днів
                'regular': 0,  # 7-30 днів
                'loyal': 0,  # 30-180 днів
                'veteran': 0  # > 180 днів
            }

            users_result = supabase.table('users').select('created_at').execute()

            for user in (users_result.data or []):
                created = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
                days_since = (now - created).days

                if days_since < 7:
                    segments['new'] += 1
                elif days_since < 30:
                    segments['regular'] += 1
                elif days_since < 180:
                    segments['loyal'] += 1
                else:
                    segments['veteran'] += 1

            return segments

        except Exception as e:
            logger.error(f"Error segmenting by lifetime: {e}")
            return {}

    @staticmethod
    def _segment_by_referral() -> Dict[str, int]:
        """Сегментація по рефералах"""
        try:
            # З рефералами
            with_referrals = supabase.table('users') \
                .select('id', count='exact') \
                .gt('referral_earnings', 0) \
                .execute()

            # Без рефералів
            without_referrals = supabase.table('users') \
                .select('id', count='exact') \
                .eq('referral_earnings', 0) \
                .execute()

            return {
                'with_referrals': with_referrals.count if hasattr(with_referrals, 'count') else 0,
                'without_referrals': without_referrals.count if hasattr(without_referrals, 'count') else 0
            }

        except Exception as e:
            logger.error(f"Error segmenting by referral: {e}")
            return {}