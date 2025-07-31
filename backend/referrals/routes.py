# backend/referrals/routes.py
"""
TeleBoost Referrals Routes
API endpoints для реферальної системи
"""
import logging
from flask import Blueprint, request, jsonify, g
from datetime import datetime

from backend.auth.decorators import jwt_required
from backend.referrals.services import (
    get_user_referrals,
    get_referral_stats,
    get_referral_tree,
    get_referral_earnings,
    REFERRAL_RATES
)
from backend.config import config
from backend.utils.formatters import format_price, format_percentage
from backend.utils.constants import SUCCESS_MESSAGES, ERROR_MESSAGES

logger = logging.getLogger(__name__)

# Створюємо Blueprint
referrals_bp = Blueprint('referrals', __name__, url_prefix='/api/referrals')


@referrals_bp.route('/stats')
@jwt_required
def referral_stats():
    """
    Отримати статистику рефералів

    Response:
    {
        "success": true,
        "data": {
            "total_referrals": 10,
            "active_referrals": 5,
            "level1_referrals": 8,
            "level2_referrals": 2,
            "total_earned": 1500.50,
            "level1_earned": 1200.00,
            "level2_earned": 300.50,
            "this_month_earned": 500.00,
            "rates": {
                "level1": 7.0,
                "level2": 2.5
            }
        }
    }
    """
    try:
        stats = get_referral_stats(g.current_user.id)

        return jsonify({
            'success': True,
            'data': stats
        }), 200

    except Exception as e:
        logger.error(f"Error getting referral stats: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'STATS_ERROR'
        }), 500


@referrals_bp.route('/link')
@jwt_required
def referral_link():
    """
    Отримати реферальне посилання

    Response:
    {
        "success": true,
        "data": {
            "link": "https://t.me/TeleeBoost_bot?start=ref_TB12345678",
            "code": "TB12345678",
            "qr_code": "data:image/png;base64,...",
            "earnings": 1500.50,
            "rates": {
                "level1": 7.0,
                "level2": 2.5
            }
        }
    }
    """
    try:
        # Формуємо посилання
        bot_url = f"https://t.me/{config.BOT_USERNAME.replace('@', '')}"
        ref_link = f"{bot_url}?start=ref_{g.current_user.referral_code}"

        # Можна згенерувати QR код
        qr_code = None  # TODO: Implement QR code generation

        return jsonify({
            'success': True,
            'data': {
                'link': ref_link,
                'code': g.current_user.referral_code,
                'qr_code': qr_code,
                'earnings': g.current_user.referral_earnings,
                'rates': {
                    'level1': REFERRAL_RATES[1] * 100,
                    'level2': REFERRAL_RATES[2] * 100
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting referral link: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'LINK_ERROR'
        }), 500


@referrals_bp.route('/list')
@jwt_required
def referral_list():
    """
    Отримати список рефералів

    Query params:
    - level: Фільтр по рівню (1, 2)
    - active: Тільки активні (true/false)
    - page: Сторінка (default: 1)
    - limit: Елементів на сторінку (default: 20)

    Response:
    {
        "success": true,
        "data": {
            "referrals": [
                {
                    "user_id": "...",
                    "telegram_id": "123456789",
                    "username": "user123",
                    "display_name": "@user123",
                    "level": 1,
                    "total_deposits": 1000.00,
                    "total_bonuses": 70.00,
                    "is_active": true,
                    "joined_at": "2024-01-01T00:00:00Z"
                }
            ],
            "total": 10,
            "page": 1,
            "pages": 1
        }
    }
    """
    try:
        # Параметри
        level = request.args.get('level', type=int)
        active_only = request.args.get('active', 'false').lower() == 'true'
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))

        # Валідація
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 20

        # Отримуємо рефералів
        all_referrals = get_user_referrals(g.current_user.id, level=level)

        # Фільтруємо активних якщо потрібно
        if active_only:
            all_referrals = [ref for ref in all_referrals if ref['is_active']]

        # Пагінація
        total = len(all_referrals)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated = all_referrals[start_idx:end_idx]

        return jsonify({
            'success': True,
            'data': {
                'referrals': paginated,
                'total': total,
                'page': page,
                'pages': (total + limit - 1) // limit
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting referral list: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'LIST_ERROR'
        }), 500


@referrals_bp.route('/tree')
@jwt_required
def referral_tree():
    """
    Отримати дерево рефералів (2 рівні)

    Response:
    {
        "success": true,
        "data": {
            "level1": [...],
            "level2": [...],
            "summary": {
                "total": 10,
                "active": 5,
                "total_deposits": 5000.00,
                "total_earned": 375.00
            }
        }
    }
    """
    try:
        tree = get_referral_tree(g.current_user.id)

        # Рахуємо загальну статистику
        summary = {
            'total': len(tree['level1']) + len(tree['level2']),
            'active': 0,
            'total_deposits': 0,
            'total_earned': 0
        }

        for level in ['level1', 'level2']:
            for ref in tree[level]:
                if ref['is_active']:
                    summary['active'] += 1
                summary['total_deposits'] += ref['deposits']
                summary['total_earned'] += ref['generated_bonus']

        return jsonify({
            'success': True,
            'data': {
                'level1': tree['level1'],
                'level2': tree['level2'],
                'summary': summary
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting referral tree: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'TREE_ERROR'
        }), 500


@referrals_bp.route('/earnings')
@jwt_required
def referral_earnings():
    """
    Отримати заробіток з рефералів

    Query params:
    - period: Період (today, week, month, all)

    Response:
    {
        "success": true,
        "data": {
            "total": 1500.50,
            "level1": 1200.00,
            "level2": 300.50,
            "period": "month",
            "chart_data": [...]
        }
    }
    """
    try:
        period = request.args.get('period', 'all')

        if period not in ['today', 'week', 'month', 'all']:
            period = 'all'

        earnings = get_referral_earnings(g.current_user.id, period)

        # TODO: Можна додати дані для графіка
        chart_data = []

        return jsonify({
            'success': True,
            'data': {
                'total': earnings['total'],
                'level1': earnings['level1'],
                'level2': earnings['level2'],
                'period': period,
                'chart_data': chart_data
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting referral earnings: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'EARNINGS_ERROR'
        }), 500


@referrals_bp.route('/promo-materials')
@jwt_required
def promo_materials():
    """
    Отримати промо-матеріали

    Response:
    {
        "success": true,
        "data": {
            "banners": [...],
            "texts": {...},
            "social_posts": {...}
        }
    }
    """
    try:
        # Формуємо посилання
        bot_url = f"https://t.me/{config.BOT_USERNAME.replace('@', '')}"
        ref_link = f"{bot_url}?start=ref_{g.current_user.referral_code}"

        materials = {
            'banners': [
                {
                    'size': '1200x630',
                    'url': '/assets/banners/referral_banner_1200x630.png',
                    'format': 'Facebook/Twitter'
                },
                {
                    'size': '1080x1080',
                    'url': '/assets/banners/referral_banner_1080x1080.png',
                    'format': 'Instagram'
                },
                {
                    'size': '1080x1920',
                    'url': '/assets/banners/referral_banner_1080x1920.png',
                    'format': 'Instagram Stories'
                }
            ],
            'texts': {
                'short': f"🚀 Boost your social media with TeleBoost! Get {REFERRAL_RATES[1] * 100}% from your referrals' deposits. Join now: {ref_link}",
                'medium': f"📈 Looking for quality social media growth? TeleBoost offers the best services for Instagram, TikTok, YouTube and more! \n\n💰 Earn {REFERRAL_RATES[1] * 100}% from level 1 and {REFERRAL_RATES[2] * 100}% from level 2 referrals. \n\n🔗 Join now: {ref_link}",
                'long': f"🎯 TeleBoost - Your Ultimate Social Media Growth Partner!\n\n✅ Instagram followers, likes, views\n✅ TikTok followers and engagement\n✅ YouTube subscribers and views\n✅ Telegram members and views\n\n💎 Why choose TeleBoost?\n• Fast delivery\n• High quality\n• 24/7 support\n• Best prices\n\n💰 Referral Program:\n• Level 1: {REFERRAL_RATES[1] * 100}% from deposits\n• Level 2: {REFERRAL_RATES[2] * 100}% from deposits\n• Instant payouts\n• No limits\n\n🚀 Start earning today!\n{ref_link}"
            },
            'social_posts': {
                'telegram': {
                    'text': f"🚀 Boost your social media with @{config.BOT_USERNAME.replace('@', '')}!\n\n💰 Earn {REFERRAL_RATES[1] * 100}% commission\n📈 Quality services\n⚡ Fast delivery\n\nJoin now: {ref_link}",
                    'buttons': [
                        {'text': '🚀 Start Now', 'url': ref_link}
                    ]
                },
                'instagram': {
                    'caption': f"Ready to grow your social media? 📈\n\n@teleboost offers:\n✓ Real followers\n✓ Quality engagement\n✓ Fast delivery\n✓ {REFERRAL_RATES[1] * 100}% referral bonus\n\nLink in bio 👆",
                    'hashtags': '#socialmediagrowth #instagramgrowth #tiktokgrowth #teleboost'
                }
            }
        }

        return jsonify({
            'success': True,
            'data': materials
        }), 200

    except Exception as e:
        logger.error(f"Error getting promo materials: {e}")
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['INTERNAL_ERROR'],
            'code': 'MATERIALS_ERROR'
        }), 500