# backend/main.py
"""
TeleBoost Main Application
Головний файл Flask додатку з інтеграцією всіх систем
"""
import os
import sys
import logging
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from datetime import datetime
from werkzeug.exceptions import HTTPException

from backend.config import config
from backend.supabase_client import supabase
from backend.utils.redis_client import redis_client
from backend.middleware import init_middleware

# Налаштування логування
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def create_app():
    """Створення та налаштування Flask додатку"""

    # Ініціалізація Flask
    app = Flask(__name__)
    app.config.from_object(config)

    # Встановлюємо секретний ключ
    app.secret_key = config.SECRET_KEY

    # CORS налаштування
    CORS(app,
         origins=config.CORS_ORIGINS,
         supports_credentials=True,
         allow_headers=[
             'Content-Type',
             'Authorization',
             'X-Requested-With',
             'X-Telegram-Init-Data',
             'X-Request-ID',
             'X-Client-Version'
         ],
         expose_headers=[
             'X-Request-ID',
             'X-RateLimit-Limit',
             'X-RateLimit-Remaining',
             'X-RateLimit-Reset',
             'X-Response-Time',
             'X-Cache',
             'X-Server-Memory'
         ])

    # Ініціалізація всіх middleware
    init_middleware(app)

    # Завантаження rate limit списків
    if hasattr(app, 'middleware') and 'rate_limit' in app.middleware:
        app.middleware['rate_limit'].load_lists_from_redis()

    # Реєстрація blueprints
    register_blueprints(app)

    # Реєстрація базових маршрутів
    register_base_routes(app)

    logger.info("✅ Flask app created successfully")

    return app


def register_blueprints(app):
    """Реєстрація всіх blueprints"""

    # Auth routes - готові
    from backend.auth.routes import auth_bp
    app.register_blueprint(auth_bp)
    logger.info("✅ Auth blueprint registered")

    # Services routes - готові
    from backend.services.routes import services_bp
    app.register_blueprint(services_bp)
    logger.info("✅ Services blueprint registered")

    # API routes - готові
    from backend.api.routes import api_bp
    app.register_blueprint(api_bp)
    logger.info("✅ API blueprint registered")

    # Referrals routes - НОВІ
    try:
        from backend.referrals.routes import referrals_bp
        app.register_blueprint(referrals_bp)
        logger.info("✅ Referrals blueprint registered")
    except ImportError:
        logger.warning("⚠️ Referrals module not found, using stub endpoints")
        # Створюємо заглушки якщо модуль ще не створено
        from flask import Blueprint
        from backend.middleware.auth_middleware import AuthMiddleware

        referrals_bp = Blueprint('referrals', __name__, url_prefix='/api/referrals')

        @referrals_bp.route('/stats')
        @AuthMiddleware.require_auth
        def referral_stats():
            stats = supabase.get_referral_stats(g.current_user.id)
            return jsonify({
                'success': True,
                'data': stats
            })

        @referrals_bp.route('/link')
        @AuthMiddleware.require_auth
        def referral_link():
            bot_url = f"https://t.me/{config.BOT_USERNAME.replace('@', '')}"
            ref_link = f"{bot_url}?start=ref_{g.current_user.referral_code}"

            return jsonify({
                'success': True,
                'data': {
                    'link': ref_link,
                    'code': g.current_user.referral_code,
                    'earnings': g.current_user.referral_earnings,
                    'rates': {
                        'level1': config.REFERRAL_BONUS_PERCENT,
                        'level2': config.REFERRAL_BONUS_LEVEL2_PERCENT
                    }
                }
            })

        app.register_blueprint(referrals_bp)
        logger.info("✅ Referrals blueprint registered (stub)")

    # Створюємо тимчасові заглушки для інших blueprints
    from flask import Blueprint
    from backend.middleware.auth_middleware import AuthMiddleware

    # === Users Blueprint ===
    users_bp = Blueprint('users', __name__, url_prefix='/api/users')

    @users_bp.route('/balance')
    @AuthMiddleware.require_auth
    def get_balance():
        return jsonify({
            'success': True,
            'data': {
                'balance': g.current_user.balance,
                'currency': 'USD',
                'total_deposited': g.current_user.total_deposited,
                'total_withdrawn': g.current_user.total_withdrawn,
                'total_spent': g.current_user.total_spent
            }
        })

    @users_bp.route('/transactions')
    @AuthMiddleware.require_auth
    def get_transactions():
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))

        transactions = supabase.get_user_transactions(
            g.current_user.id,
            limit=limit,
            offset=(page - 1) * limit
        )

        return jsonify({
            'success': True,
            'data': {
                'transactions': transactions,
                'page': page,
                'limit': limit
            }
        })

    app.register_blueprint(users_bp)
    logger.info("✅ Users blueprint registered")

    # === Orders Blueprint ===
    orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')

    @orders_bp.route('/', methods=['GET'])
    @AuthMiddleware.require_auth
    def get_orders():
        return jsonify({
            'success': True,
            'data': {
                'orders': [],
                'total': 0
            }
        })

    @orders_bp.route('/', methods=['POST'])
    @AuthMiddleware.require_auth
    def create_order():
        return jsonify({
            'success': False,
            'error': 'Orders not implemented yet',
            'code': 'NOT_IMPLEMENTED'
        }), 501

    app.register_blueprint(orders_bp)
    logger.info("✅ Orders blueprint registered")

    # === Payments Blueprint ===
    payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')

    @payments_bp.route('/create', methods=['POST'])
    @AuthMiddleware.require_auth
    def create_payment():
        return jsonify({
            'success': False,
            'error': 'Payments not implemented yet',
            'code': 'NOT_IMPLEMENTED'
        }), 501

    @payments_bp.route('/webhooks/cryptobot', methods=['POST'])
    def cryptobot_webhook():
        logger.info("CryptoBot webhook received")
        return jsonify({'status': 'ok'})

    @payments_bp.route('/webhooks/nowpayments', methods=['POST'])
    def nowpayments_webhook():
        logger.info("NOWPayments webhook received")
        return jsonify({'status': 'ok'})

    app.register_blueprint(payments_bp)
    logger.info("✅ Payments blueprint registered")

    # === Statistics Blueprint ===
    statistics_bp = Blueprint('statistics', __name__, url_prefix='/api/statistics')

    @statistics_bp.route('/overview')
    @AuthMiddleware.require_admin
    def statistics_overview():
        return jsonify({
            'success': True,
            'data': {
                'users': {'total': 0, 'active': 0},
                'orders': {'total': 0, 'today': 0},
                'revenue': {'total': 0, 'today': 0}
            }
        })

    app.register_blueprint(statistics_bp)
    logger.info("✅ Statistics blueprint registered")

    logger.info("✅ All blueprints registered successfully")


def register_base_routes(app):
    """Реєстрація базових маршрутів"""

    @app.route('/')
    def index():
        """Головна сторінка API"""
        return jsonify({
            'name': 'TeleBoost API',
            'version': '1.0.0',
            'status': 'online',
            'environment': config.ENV,
            'documentation': '/api/docs',
            'health': '/health',
            'endpoints': {
                'auth': {
                    'login': 'POST /api/auth/telegram',
                    'refresh': 'POST /api/auth/refresh',
                    'logout': 'POST /api/auth/logout',
                    'profile': 'GET /api/auth/me',
                    'verify': 'GET /api/auth/verify'
                },
                'users': {
                    'balance': 'GET /api/users/balance',
                    'transactions': 'GET /api/users/transactions',
                    'deposit': 'POST /api/users/deposit',
                    'withdraw': 'POST /api/users/withdraw'
                },
                'services': {
                    'list': 'GET /api/services',
                    'details': 'GET /api/services/{id}',
                    'categories': 'GET /api/services/categories',
                    'calculate': 'POST /api/services/calculate-price',
                    'sync': 'POST /api/services/sync'
                },
                'orders': {
                    'list': 'GET /api/orders',
                    'create': 'POST /api/orders',
                    'details': 'GET /api/orders/{id}',
                    'cancel': 'POST /api/orders/{id}/cancel'
                },
                'payments': {
                    'create': 'POST /api/payments/create',
                    'status': 'GET /api/payments/{id}',
                    'methods': 'GET /api/payments/methods'
                },
                'referrals': {
                    'stats': 'GET /api/referrals/stats',
                    'link': 'GET /api/referrals/link',
                    'list': 'GET /api/referrals/list',
                    'tree': 'GET /api/referrals/tree',
                    'earnings': 'GET /api/referrals/earnings',
                    'promo': 'GET /api/referrals/promo-materials'
                },
                'api': {
                    'health': 'GET /api/health',
                    'external_balance': 'GET /api/external-balance',
                    'test_connection': 'POST /api/test-connection',
                    'supported_services': 'GET /api/supported-services',
                    'system_info': 'GET /api/system-info'
                }
            }
        })

    @app.route('/health')
    def health_check():
        """Перевірка здоров'я сервісу"""
        start = datetime.utcnow()

        # Перевіряємо компоненти
        checks = {
            'api': True,
            'database': False,
            'redis': False,
            'middleware': {},
            'timestamp': start.isoformat()
        }

        # Перевірка БД
        try:
            if supabase and supabase.client:
                if supabase.test_connection():
                    checks['database'] = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")

        # Перевірка Redis
        try:
            if redis_client and redis_client.ping():
                checks['redis'] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")

        # Перевірка middleware
        if hasattr(app, 'middleware'):
            for name, middleware in app.middleware.items():
                checks['middleware'][name] = True

        # Визначаємо загальний статус
        is_healthy = checks['database']  # Redis опціональний

        # Час відповіді
        duration = (datetime.utcnow() - start).total_seconds()

        return jsonify({
            'status': 'healthy' if is_healthy else 'degraded',
            'checks': checks,
            'response_time': f"{duration:.3f}s"
        }), 200 if is_healthy else 503

    @app.route('/api/config')
    def get_public_config():
        """Отримати публічну конфігурацію"""
        return jsonify({
            'success': True,
            'data': config.to_dict()
        })

    @app.route('/api/status')
    def api_status():
        """Статус API з детальною статистикою"""
        # Збираємо статистику middleware
        middleware_stats = {}

        if hasattr(app, 'middleware'):
            # Performance stats
            if 'performance' in app.middleware:
                middleware_stats['performance'] = app.middleware['performance'].get_system_metrics()

            # Cache stats
            if 'cache' in app.middleware:
                middleware_stats['cache'] = app.middleware['cache'].get_cache_stats()

            # Rate limit stats
            if 'rate_limit' in app.middleware:
                middleware_stats['rate_limit'] = app.middleware['rate_limit'].get_rate_limit_stats()

            # Compression stats
            if 'compression' in app.middleware:
                middleware_stats['compression'] = app.middleware['compression'].get_compression_stats()

            # Error stats
            if 'error' in app.middleware:
                middleware_stats['errors'] = app.middleware['error'].get_error_stats()

        return jsonify({
            'success': True,
            'data': {
                'version': '1.0.0',
                'environment': config.ENV,
                'debug': config.DEBUG,
                'bot_username': config.BOT_USERNAME,
                'features': {
                    'auth': True,
                    'services': True,
                    'orders': False,  # Поки не реалізовано
                    'payments': False,  # Поки не реалізовано
                    'referrals': True,
                    'middleware': {
                        'auth': True,
                        'cache': True,
                        'compression': True,
                        'error_handling': True,
                        'performance': True,
                        'rate_limiting': True
                    }
                },
                'referral_system': {
                    'enabled': True,
                    'levels': 2,
                    'rates': {
                        'level1': config.REFERRAL_BONUS_PERCENT,
                        'level2': config.REFERRAL_BONUS_LEVEL2_PERCENT
                    }
                },
                'middleware': middleware_stats
            }
        })

    @app.route('/api/ping')
    def ping():
        """Простий ping endpoint"""
        return jsonify({
            'success': True,
            'message': 'pong',
            'timestamp': datetime.utcnow().isoformat()
        })


def init_services():
    """Ініціалізація сервісів при старті"""
    try:
        logger.info("🚀 Initializing services...")

        # Перевірка конфігурації
        try:
            config.validate()
            logger.info("✅ Configuration validated")
        except ValueError as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            raise

        # Перевірка Supabase
        if not supabase or not supabase.client:
            logger.error("❌ Supabase client not initialized")
            raise ConnectionError("Cannot initialize Supabase client")

        if supabase.test_connection():
            logger.info("✅ Supabase connection successful")
        else:
            logger.error("❌ Supabase connection test failed")
            raise ConnectionError("Cannot connect to Supabase")

        # Перевірка Redis (опціонально)
        if redis_client:
            if redis_client.ping():
                logger.info("✅ Redis connection successful")
            else:
                logger.warning("⚠️ Redis is not available, caching will be disabled")
        else:
            logger.warning("⚠️ Redis client not initialized")

        # Перевірка Nakrutochka API
        try:
            from backend.api.nakrutochka_api import nakrutochka
            balance = nakrutochka.get_balance()
            if balance.get('success'):
                logger.info(
                    f"✅ Nakrutochka API connected (Balance: {balance.get('balance')} {balance.get('currency')})")
            else:
                logger.warning("⚠️ Nakrutochka API connection failed")
        except Exception as e:
            logger.warning(f"⚠️ Nakrutochka API check failed: {e}")

        logger.info("✅ All services initialized successfully")

        # Виводимо інформацію про конфігурацію
        logger.info("=" * 50)
        logger.info("CONFIGURATION SUMMARY:")
        logger.info(f"Environment: {config.ENV}")
        logger.info(f"Backend URL: {config.BACKEND_URL}")
        logger.info(f"Bot Username: @{config.BOT_USERNAME}")
        logger.info(f"JWT Configured: {'✅' if config.JWT_SECRET != config.SECRET_KEY else '⚠️ Using default'}")
        logger.info(f"Database: {'✅ Connected' if supabase.test_connection() else '❌ Not connected'}")
        logger.info(f"Redis: {'✅ Connected' if redis_client and redis_client.ping() else '⚠️ Not available'}")
        logger.info(f"Middleware: ✅ All systems initialized")
        logger.info(
            f"Referral System: ✅ Two-level (L1: {config.REFERRAL_BONUS_PERCENT}%, L2: {config.REFERRAL_BONUS_LEVEL2_PERCENT}%)")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise


# Створюємо додаток
app = create_app()

# Для production (Gunicorn) потрібно ініціалізувати сервіси тут
if __name__ != '__main__':
    try:
        init_services()
    except Exception as e:
        logger.error(f"❌ Failed to initialize services for production: {e}")
        # В production продовжуємо працювати навіть якщо щось не так
        # але логуємо помилку

# Для розробки
if __name__ == '__main__':
    """Запуск додатку для розробки"""
    try:
        # Ініціалізація сервісів
        init_services()

        # Інформація про запуск
        logger.info("=" * 50)
        logger.info(f"🚀 Starting TeleBoost API")
        logger.info(f"📍 URL: http://{config.HOST}:{config.PORT}")
        logger.info(f"🌍 Environment: {config.ENV}")
        logger.info(f"🐛 Debug Mode: {config.DEBUG}")
        logger.info(f"🔧 Features:")
        logger.info(f"   - Middleware: ✅ All systems active")
        logger.info(f"   - Services: ✅ API integration ready")
        logger.info(f"   - Auth: ✅ JWT + Telegram Web App")
        logger.info(f"   - Cache: ✅ Redis caching enabled")
        logger.info(f"   - Performance: ✅ Monitoring active")
        logger.info(f"   - Referrals: ✅ Two-level system (7% + 2.5%)")
        logger.info("=" * 50)

        # Запуск Flask сервера
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG,
            use_reloader=config.DEBUG
        )

    except KeyboardInterrupt:
        logger.info("\n⏹️ Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        exit(1)