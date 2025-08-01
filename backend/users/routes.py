# backend/users/routes.py
"""
TeleBoost User Routes
API endpoints для роботи з користувачами
"""
import logging
from flask import Blueprint, request, jsonify, g, send_file, Response
from datetime import datetime
import io

from backend.auth.decorators import jwt_required, admin_required, rate_limit, validate_request
from backend.users.services import UserService, UserTransactionService
from backend.users.models import UserProfile, UserSettings, UserActivity, UserNotification
from backend.payments.services import get_payment_limits
from backend.utils.constants import ERROR_MESSAGES, SUCCESS_MESSAGES, LIMITS
from backend.utils.validators import validate_amount, validate_crypto_address

logger = logging.getLogger(__name__)

# Створюємо Blueprint
users_bp = Blueprint('users', __name__, url_prefix='/api/users')


@users_bp.route('/profile', methods=['GET'])
@jwt_required
def get_user_profile():
    """
    Отримати повний профіль користувача

    Response:
    {
        "success": true,
        "data": {
            "user": {...},
            "stats": {...},
            "limits": {...}
        }
    }
    """
    try:
        user_id = g.current_user.id

        # Отримуємо профіль
        profile = UserService.get_user_profile(user_id)
        if not profile:
            return jsonify({
                'success': False,
                'error': 'User not found',
                'code': 'USER_NOT_FOUND'
            }), 404

        # Логуємо активність
        activity = UserActivity(user_id)
        activity.log_action('view_profile')

        return jsonify({
            'success': True,
            'data': {
                'user': profile.to_public_dict(),
                'role': profile.get_role_display(),
                'is_vip': profile.is_vip(),
                'trust_score': profile.trust_score,
                'limits': profile.get_limits(),
                'stats': {
                    'total_orders': profile.total_orders,
                    'successful_orders': profile.successful_orders,
                    'success_rate': round(
                        (profile.successful_orders / profile.total_orders * 100) if profile.total_orders > 0 else 0, 2)
                },
                'unread_notifications': UserNotification.get_unread_count(user_id)
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'PROFILE_ERROR'
        }), 500


@users_bp.route('/balance', methods=['GET'])
@jwt_required
def get_balance():
    """
    Отримати детальну інформацію про баланс

    Response:
    {
        "success": true,
        "data": {
            "balance": 100.50,
            "available_balance": 80.50,
            "frozen_amount": 20.00,
            "pending_withdrawals": 0,
            "currency": "USD",
            "limits": {...}
        }
    }
    """
    try:
        balance_info = UserService.get_user_balance_info(g.current_user.id)

        if not balance_info:
            return jsonify({
                'success': False,
                'error': 'Failed to get balance',
                'code': 'BALANCE_ERROR'
            }), 500

        return jsonify({
            'success': True,
            'data': balance_info
        }), 200

    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'BALANCE_ERROR'
        }), 500


@users_bp.route('/transactions', methods=['GET'])
@jwt_required
def get_transactions():
    """
    Отримати історію транзакцій

    Query params:
        - type: Тип транзакції (deposit, withdrawal, order, referral_bonus)
        - page: Номер сторінки
        - limit: Кількість на сторінці
        - export: Експорт в CSV (true/false)
    """
    try:
        user_id = g.current_user.id

        # Перевірка на експорт
        if request.args.get('export') == 'true':
            return export_transactions()

        # Параметри
        transaction_type = request.args.get('type')
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = (page - 1) * limit

        # Отримуємо транзакції
        transactions = UserService.get_user_transactions(
            user_id=user_id,
            transaction_type=transaction_type,
            limit=limit,
            offset=offset
        )

        # Отримуємо загальну кількість
        from backend.supabase_client import supabase
        query = supabase.table('transactions').select('id', count='exact').eq('user_id', user_id)
        if transaction_type:
            query = query.eq('type', transaction_type)
        result = query.execute()
        total = result.count if hasattr(result, 'count') else 0

        # Отримуємо зведення
        summary = UserTransactionService.get_transaction_summary(user_id, period_days=30)

        return jsonify({
            'success': True,
            'data': {
                'transactions': transactions,
                'summary': summary,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit if limit > 0 else 0
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'TRANSACTIONS_ERROR'
        }), 500


@users_bp.route('/transactions/export', methods=['GET'])
@jwt_required
def export_transactions():
    """Експорт транзакцій в CSV"""
    try:
        user_id = g.current_user.id

        # Параметри дат
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if start_date:
            start_date = datetime.fromisoformat(start_date)
        if end_date:
            end_date = datetime.fromisoformat(end_date)

        # Експортуємо
        csv_data = UserTransactionService.export_transactions(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )

        if not csv_data:
            return jsonify({
                'success': False,
                'error': 'No transactions to export',
                'code': 'NO_DATA'
            }), 404

        # Відправляємо файл
        output = io.StringIO(csv_data)
        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=transactions_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )

    except Exception as e:
        logger.error(f"Error exporting transactions: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'EXPORT_ERROR'
        }), 500


@users_bp.route('/statistics', methods=['GET'])
@jwt_required
def get_statistics():
    """Отримати статистику користувача"""
    try:
        stats = UserService.get_user_statistics(g.current_user.id)

        if not stats:
            return jsonify({
                'success': False,
                'error': 'Failed to get statistics',
                'code': 'STATS_ERROR'
            }), 500

        return jsonify({
            'success': True,
            'data': stats
        }), 200

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'STATS_ERROR'
        }), 500


@users_bp.route('/withdraw', methods=['POST'])
@jwt_required
@rate_limit(calls=5, period=86400)  # 5 запитів на день
@validate_request({
    'amount': {'type': 'float', 'required': True, 'min': 0},
    'address': {'type': 'string', 'required': True, 'min_length': 10},
    'network': {'type': 'string', 'required': True}
})
def create_withdrawal():
    """
    Створити запит на виведення коштів

    Request body:
    {
        "amount": 100.00,
        "address": "TRX...",
        "network": "TRC20"
    }
    """
    try:
        data = request.get_json()
        user_id = g.current_user.id

        # Валідація адреси
        if not validate_crypto_address(data['address'], data['network']):
            return jsonify({
                'success': False,
                'error': 'Invalid crypto address',
                'code': 'INVALID_ADDRESS'
            }), 400

        # Створюємо запит
        success, error = UserService.create_withdrawal(
            user_id=user_id,
            amount=data['amount'],
            method='manual',  # або інший метод
            address=data['address'],
            network=data['network']
        )

        if not success:
            return jsonify({
                'success': False,
                'error': error,
                'code': 'WITHDRAWAL_FAILED'
            }), 400

        # Логуємо активність
        activity = UserActivity(user_id)
        activity.log_action('create_withdrawal', {
            'amount': data['amount'],
            'network': data['network']
        })

        return jsonify({
            'success': True,
            'message': 'Withdrawal request created successfully',
            'data': {
                'amount': data['amount'],
                'status': 'pending',
                'estimated_time': '24-48 hours'
            }
        }), 201

    except Exception as e:
        logger.error(f"Error creating withdrawal: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'WITHDRAWAL_ERROR'
        }), 500


@users_bp.route('/settings', methods=['GET', 'PUT'])
@jwt_required
def user_settings():
    """Отримати або оновити налаштування користувача"""
    try:
        user_id = g.current_user.id

        if request.method == 'GET':
            # Отримуємо налаштування
            settings = UserSettings.get_for_user(user_id)

            return jsonify({
                'success': True,
                'data': settings.to_dict()
            }), 200

        else:  # PUT
            # Оновлюємо налаштування
            data = request.get_json()
            settings = UserSettings.get_for_user(user_id)

            if settings.update(data):
                # Логуємо активність
                activity = UserActivity(user_id)
                activity.log_action('update_settings', data)

                return jsonify({
                    'success': True,
                    'message': 'Settings updated successfully',
                    'data': settings.to_dict()
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to update settings',
                    'code': 'UPDATE_FAILED'
                }), 500

    except Exception as e:
        logger.error(f"Error with settings: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'SETTINGS_ERROR'
        }), 500


@users_bp.route('/notifications', methods=['GET'])
@jwt_required
def get_notifications():
    """Отримати сповіщення користувача"""
    try:
        user_id = g.current_user.id

        # Параметри
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        unread_only = request.args.get('unread_only', 'false') == 'true'

        # Запит до БД
        from backend.supabase_client import supabase
        query = supabase.table('user_notifications') \
            .select('*') \
            .eq('user_id', user_id)

        if unread_only:
            query = query.eq('is_read', False)

        result = query.order('created_at', desc=True) \
            .range((page - 1) * limit, page * limit - 1) \
            .execute()

        notifications = []
        for n in (result.data or []):
            notification = UserNotification(n)
            notifications.append({
                'id': notification.id,
                'type': notification.type,
                'title': notification.title,
                'message': notification.message,
                'is_read': notification.is_read,
                'created_at': notification.created_at,
                'data': notification.data
            })

        return jsonify({
            'success': True,
            'data': {
                'notifications': notifications,
                'unread_count': UserNotification.get_unread_count(user_id)
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'NOTIFICATIONS_ERROR'
        }), 500


@users_bp.route('/notifications/<notification_id>/read', methods=['POST'])
@jwt_required
def mark_notification_read(notification_id: str):
    """Позначити сповіщення як прочитане"""
    try:
        # Отримуємо сповіщення
        from backend.supabase_client import supabase
        result = supabase.table('user_notifications') \
            .select('*') \
            .eq('id', notification_id) \
            .eq('user_id', g.current_user.id) \
            .single() \
            .execute()

        if not result.data:
            return jsonify({
                'success': False,
                'error': 'Notification not found',
                'code': 'NOT_FOUND'
            }), 404

        notification = UserNotification(result.data)

        if notification.mark_as_read():
            return jsonify({
                'success': True,
                'message': 'Notification marked as read'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update notification',
                'code': 'UPDATE_FAILED'
            }), 500

    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'NOTIFICATION_ERROR'
        }), 500


@users_bp.route('/activity', methods=['GET'])
@jwt_required
def get_activity():
    """Отримати історію активності"""
    try:
        activity = UserActivity(g.current_user.id)

        # Останні активності
        recent_activities = activity.get_recent_activities(limit=50)

        # Історія входів
        login_history = activity.get_login_history(days=30)

        return jsonify({
            'success': True,
            'data': {
                'recent_activities': recent_activities,
                'login_history': login_history
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting activity: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'ACTIVITY_ERROR'
        }), 500


# === Admin Routes ===

@users_bp.route('/admin/list', methods=['GET'])
@jwt_required
@admin_required
def admin_list_users():
    """
    Список користувачів для адмінів

    Query params:
        - search: Пошуковий запит
        - role: Фільтр по ролі
        - is_active: Фільтр по статусу
        - page: Номер сторінки
        - limit: Кількість на сторінці
    """
    try:
        # Параметри
        search = request.args.get('search')
        filters = {
            'role': request.args.get('role'),
            'is_active': request.args.get('is_active') == 'true' if request.args.get('is_active') else None,
            'is_admin': request.args.get('is_admin') == 'true' if request.args.get('is_admin') else None,
            'min_balance': float(request.args.get('min_balance')) if request.args.get('min_balance') else None,
        }

        # Видаляємо None значення
        filters = {k: v for k, v in filters.items() if v is not None}

        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = (page - 1) * limit

        # Пошук
        users, total = UserService.search_users(
            query=search,
            filters=filters,
            limit=limit,
            offset=offset
        )

        # Формуємо відповідь
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': user.username,
                'display_name': user.get_display_name(),
                'role': user.role,
                'is_vip': user.is_vip(),
                'is_admin': user.is_admin,
                'is_active': user.is_active,
                'balance': user.balance,
                'total_deposited': user.total_deposited,
                'total_orders': user.total_orders,
                'trust_score': user.trust_score,
                'created_at': user.created_at,
                'last_login': user.last_login
            })

        return jsonify({
            'success': True,
            'data': {
                'users': users_data,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit if limit > 0 else 0
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'LIST_ERROR'
        }), 500


@users_bp.route('/admin/<user_id>/ban', methods=['POST'])
@jwt_required
@admin_required
@validate_request({
    'reason': {'type': 'string', 'required': True, 'min_length': 5}
})
def admin_ban_user(user_id: str):
    """Заблокувати користувача"""
    try:
        data = request.get_json()

        success = UserService.ban_user(
            user_id=user_id,
            reason=data['reason'],
            admin_id=g.current_user.id
        )

        if success:
            return jsonify({
                'success': True,
                'message': 'User banned successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to ban user',
                'code': 'BAN_FAILED'
            }), 500

    except Exception as e:
        logger.error(f"Error banning user: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'BAN_ERROR'
        }), 500


@users_bp.route('/admin/<user_id>/update-balance', methods=['POST'])
@jwt_required
@admin_required
@validate_request({
    'amount': {'type': 'float', 'required': True},
    'operation': {'type': 'string', 'required': True},
    'reason': {'type': 'string', 'required': True}
})
def admin_update_balance(user_id: str):
    """Адмін оновлення балансу"""
    try:
        data = request.get_json()

        from backend.supabase_client import supabase

        # Оновлюємо баланс
        success = supabase.update_user_balance(
            user_id=user_id,
            amount=abs(data['amount']),
            operation=data['operation']
        )

        if success:
            # Створюємо транзакцію
            transaction_type = 'admin_add' if data['operation'] == 'add' else 'admin_deduct'
            amount = data['amount'] if data['operation'] == 'add' else -abs(data['amount'])

            supabase.create_transaction({
                'user_id': user_id,
                'type': transaction_type,
                'amount': amount,
                'description': f"Admin adjustment: {data['reason']}",
                'metadata': {
                    'admin_id': g.current_user.id,
                    'reason': data['reason']
                }
            })

            # Логуємо
            supabase.table('admin_actions').insert({
                'admin_id': g.current_user.id,
                'action': 'update_balance',
                'target_user_id': user_id,
                'details': data,
                'created_at': datetime.utcnow().isoformat()
            }).execute()

            return jsonify({
                'success': True,
                'message': 'Balance updated successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update balance',
                'code': 'UPDATE_FAILED'
            }), 500

    except Exception as e:
        logger.error(f"Error updating balance: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'BALANCE_UPDATE_ERROR'
        }), 500