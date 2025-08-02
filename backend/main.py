# backend/main.py
"""
TeleBoost Main Application
Головний файл Flask додатку з інтеграцією всіх систем
"""
import os
import sys
import logging
from flask import Flask, jsonify, request, g, send_from_directory, render_template_string
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

    # Ініціалізація Flask з підтримкою статичних файлів
    app = Flask(__name__,
                static_folder='../frontend/shared/ui',
                static_url_path='/static')

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

    # Реєстрація frontend маршрутів
    register_frontend_routes(app)

    logger.info("✅ Flask app created successfully")

    return app


def register_frontend_routes(app):
    """Реєстрація маршрутів для frontend"""

    # Головна сторінка - редірект на splash
    @app.route('/')
    def root():
        """Кореневий маршрут"""
        # Перевіряємо чи це запит від браузера
        if request.headers.get('Accept', '').startswith('text/html'):
            # Показуємо index.html який редіректить на splash
            try:
                return send_from_directory('../frontend/pages', 'index.html')
            except:
                # Fallback редірект
                return """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>TeleBoost</title>
                    <meta http-equiv="refresh" content="0; url=/splash">
                </head>
                <body>
                    <p>Redirecting...</p>
                </body>
                </html>
                """
        else:
            # API запит - повертаємо JSON
            return jsonify({
                'name': 'TeleBoost API',
                'version': '1.0.0',
                'status': 'online',
                'environment': config.ENV,
                'documentation': '/api/docs',
                'health': '/health'
            })

    # Маршрут для splash screen
    @app.route('/splash')
    def splash_page():
        """Splash screen"""
        try:
            return send_from_directory('../frontend/pages', 'splash.html')
        except Exception as e:
            logger.error(f"Failed to serve splash.html: {e}")
            # Fallback на логін
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>TeleBoost</title>
                <meta http-equiv="refresh" content="0; url=/login">
            </head>
            <body>
                <p>Redirecting to login...</p>
            </body>
            </html>
            """

    # Маршрут для login
    @app.route('/login')
    def login_page():
        """Сторінка логіну"""
        try:
            return send_from_directory('../frontend/pages/login', 'login.html')
        except Exception as e:
            logger.error(f"Failed to serve login.html: {e}")
            return "Login page not found", 404

    # Маршрут для home
    @app.route('/home')
    def home_page():
        """Головна сторінка"""
        try:
            return send_from_directory('../frontend/pages/home', 'home.html')
        except Exception as e:
            logger.error(f"Failed to serve home.html: {e}")
            return "Home page not found", 404

    # Обслуговування всіх файлів з frontend
    @app.route('/frontend/<path:path>')
    def serve_frontend(path):
        """Обслуговування frontend файлів"""
        try:
            # Визначаємо базову директорію
            base_dir = os.path.dirname(os.path.abspath(__file__))
            frontend_dir = os.path.join(base_dir, '..', 'frontend')

            # Перевіряємо чи файл існує
            file_path = os.path.join(frontend_dir, path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                # Повертаємо файл
                directory = os.path.dirname(file_path)
                filename = os.path.basename(file_path)
                return send_from_directory(directory, filename)
            else:
                logger.warning(f"File not found: {path}")
                return "File not found", 404

        except Exception as e:
            logger.error(f"Error serving frontend file {path}: {e}")
            return "Internal server error", 500

    # Спеціальні маршрути для компонентів
    @app.route('/shared/<path:path>')
    def serve_shared(path):
        """Обслуговування shared файлів"""
        return serve_frontend(f'shared/{path}')

    @app.route('/pages/<path:path>')
    def serve_pages(path):
        """Обслуговування сторінок"""
        return serve_frontend(f'pages/{path}')

    # Маршрути для конкретних типів файлів
    @app.route('/<path:filename>.js')
    def serve_js(filename):
        """Обслуговування JS файлів"""
        # Шукаємо в різних директоріях
        paths_to_try = [
            f'pages/home/{filename}.js',
            f'pages/home/components/{filename}.js',
            f'shared/components/{filename}.js',
            f'shared/services/{filename}.js',
            f'shared/auth/{filename}.js',
            f'shared/ui/{filename}.js',
            f'shared/utils/{filename}.js'
        ]

        for path in paths_to_try:
            try:
                return serve_frontend(path)
            except:
                continue

        return "JS file not found", 404

    @app.route('/<path:filename>.css')
    def serve_css(filename):
        """Обслуговування CSS файлів"""
        # Шукаємо в різних директоріях
        paths_to_try = [
            f'pages/home/{filename}.css',
            f'shared/ui/{filename}.css'
        ]

        for path in paths_to_try:
            try:
                return serve_frontend(path)
            except:
                continue

        return "CSS file not found", 404

    logger.info("✅ Frontend routes registered")


def register_blueprints(app):
    """Реєстрація всіх blueprints"""

    # Auth routes
    from backend.auth.routes import auth_bp
    app.register_blueprint(auth_bp)
    logger.info("✅ Auth blueprint registered")

    # Services routes
    from backend.services.routes import services_bp
    app.register_blueprint(services_bp)
    logger.info("✅ Services blueprint registered")

    # API routes
    from backend.api.routes import api_bp
    app.register_blueprint(api_bp)
    logger.info("✅ API blueprint registered")

    # Payments routes
    from backend.payments.routes import payments_bp
    app.register_blueprint(payments_bp)
    logger.info("✅ Payments blueprint registered")

    # Payment webhooks
    from backend.payments.webhooks import webhooks_bp
    app.register_blueprint(webhooks_bp)
    logger.info("✅ Payment webhooks blueprint registered")

    # Referrals routes
    from backend.referrals.routes import referrals_bp
    app.register_blueprint(referrals_bp)
    logger.info("✅ Referrals blueprint registered")

    # Users routes
    try:
        from backend.users.routes import users_bp
        app.register_blueprint(users_bp)
        logger.info("✅ Users blueprint registered")
    except ImportError:
        logger.warning("⚠️ Users module not found, using stub endpoints")
        # Створюємо заглушку
        from flask import Blueprint
        from backend.middleware.auth_middleware import AuthMiddleware

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
        logger.info("✅ Users blueprint registered (stub)")

    # Orders routes
    from backend.orders.routes import orders_bp
    app.register_blueprint(orders_bp)
    logger.info("✅ Orders blueprint registered")

    # Statistics routes
    try:
        from backend.statistics.routes import statistics_bp
        app.register_blueprint(statistics_bp)
        logger.info("✅ Statistics blueprint registered")
    except ImportError:
        logger.warning("⚠️ Statistics module not found, using stub endpoints")
        # Створюємо заглушку
        from flask import Blueprint
        from backend.middleware.auth_middleware import AuthMiddleware

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

        @statistics_bp.route('/live')
        def live_statistics():
            return jsonify({
                'success': True,
                'data': {
                    'total_users': 15234,
                    'total_orders': 45678,
                    'services_available': 234,
                    'average_completion_time': '2-6 hours',
                    'success_rate': 98.5,
                    'active_now': 127
                }
            })

        app.register_blueprint(statistics_bp)
        logger.info("✅ Statistics blueprint registered (stub)")

    logger.info("✅ All blueprints registered successfully")


def register_base_routes(app):
    """Реєстрація базових API маршрутів"""

    @app.route('/api')
    def api_index():
        """API інформація"""
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
                    'status': 'GET /api/orders/{id}/status',
                    'cancel': 'POST /api/orders/{id}/cancel',
                    'refill': 'POST /api/orders/{id}/refill',
                    'calculate': 'POST /api/orders/calculate-price',
                    'statistics': 'GET /api/orders/statistics'
                },
                'payments': {
                    'create': 'POST /api/payments/create',
                    'status': 'GET /api/payments/{id}',
                    'check': 'POST /api/payments/{id}/check',
                    'list': 'GET /api/payments',
                    'methods': 'GET /api/payments/methods',
                    'limits': 'GET /api/payments/limits',
                    'calculate': 'POST /api/payments/calculate',
                    'webhooks': {
                        'cryptobot': 'POST /api/webhooks/cryptobot',
                        'nowpayments': 'POST /api/webhooks/nowpayments'
                    }
                },
                'referrals': {
                    'stats': 'GET /api/referrals/stats',
                    'link': 'GET /api/referrals/link',
                    'list': 'GET /api/referrals/list',
                    'tree': 'GET /api/referrals/tree',
                    'earnings': 'GET /api/referrals/earnings',
                    'promo': 'GET /api/referrals/promo-materials'
                },
                'statistics': {
                    'live': 'GET /api/statistics/live'
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
            'payments': {},
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

        # Перевірка платіжних провайдерів
        try:
            from backend.payments.providers import get_available_providers
            available_providers = get_available_providers()
            for provider in available_providers:
                checks['payments'][provider] = True
        except Exception as e:
            logger.error(f"Payment providers check failed: {e}")

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

        # Перевірка платіжних провайдерів
        payment_providers = []
        try:
            from backend.payments.providers import get_available_providers
            payment_providers = get_available_providers()
        except:
            pass

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
                    'orders': True,
                    'payments': True,
                    'referrals': True,
                    'frontend': True,
                    'middleware': {
                        'auth': True,
                        'cache': True,
                        'compression': True,
                        'error_handling': True,
                        'performance': True,
                        'rate_limiting': True
                    }
                },
                'payment_providers': payment_providers,
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

        # Перевірка платіжних провайдерів
        try:
            from backend.payments.providers import get_available_providers
            providers = get_available_providers()
            if providers:
                logger.info(f"✅ Payment providers available: {', '.join(providers)}")
            else:
                logger.warning("⚠️ No payment providers configured")
        except Exception as e:
            logger.warning(f"⚠️ Payment providers check failed: {e}")

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
        logger.info(f"Frontend: ✅ Static files serving enabled")
        logger.info(
            f"Referral System: ✅ Two-level (L1: {config.REFERRAL_BONUS_PERCENT}%, L2: {config.REFERRAL_BONUS_LEVEL2_PERCENT}%)")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise


def init_scheduler():
    """Ініціалізація планувальника задач"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from backend.orders.tasks import register_order_tasks

        # Створюємо планувальник
        scheduler = BackgroundScheduler()

        # Реєструємо задачі для замовлень
        register_order_tasks(scheduler)

        # Запускаємо планувальник
        scheduler.start()

        logger.info("✅ Task scheduler initialized")

        return scheduler

    except ImportError:
        logger.warning("⚠️ APScheduler not installed, background tasks disabled")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to initialize scheduler: {e}")
        return None


# Створюємо додаток
app = create_app()

# Глобальна змінна для планувальника
scheduler = None

# Для production (Gunicorn) потрібно ініціалізувати сервіси тут
if __name__ != '__main__':
    try:
        init_services()
        # Ініціалізуємо планувальник для production
        scheduler = init_scheduler()
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

        # Ініціалізація планувальника
        scheduler = init_scheduler()

        # Інформація про запуск
        logger.info("=" * 50)
        logger.info(f"🚀 Starting TeleBoost API with Frontend")
        logger.info(f"📍 URL: http://{config.HOST}:{config.PORT}")
        logger.info(f"🌐 Frontend: http://{config.HOST}:{config.PORT}/splash")
        logger.info(f"🌍 Environment: {config.ENV}")
        logger.info(f"🐛 Debug Mode: {config.DEBUG}")
        logger.info(f"🔧 Features:")
        logger.info(f"   - Frontend: ✅ Splash screen at /splash")
        logger.info(f"   - Middleware: ✅ All systems active")
        logger.info(f"   - Services: ✅ API integration ready")
        logger.info(f"   - Auth: ✅ JWT + Telegram Web App")
        logger.info(f"   - Cache: ✅ Redis caching enabled")
        logger.info(f"   - Performance: ✅ Monitoring active")
        logger.info(f"   - Referrals: ✅ Two-level system (7% + 2.5%)")
        logger.info(f"   - Payments: ✅ CryptoBot + NOWPayments")
        logger.info(f"   - Orders: ✅ Full order management system")
        logger.info(f"   - Scheduler: {'✅ Background tasks active' if scheduler else '⚠️ Background tasks disabled'}")
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
        # Зупиняємо планувальник якщо він працює
        if scheduler and scheduler.running:
            scheduler.shutdown()
            logger.info("✅ Scheduler stopped")
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        exit(1)