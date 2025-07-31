# backend/main.py
"""
TeleBoost Main Application
Головний файл Flask додатку
"""
import os
import sys
import logging
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
from werkzeug.exceptions import HTTPException

# Додаємо backend до sys.path для правильних імпортів
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import config
from backend.supabase_client import supabase
from backend.utils.redis_client import redis_client

# Налаштування логування
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        # Можна додати FileHandler для збереження в файл
    ]
)
logger = logging.getLogger(__name__)

# Глобальна змінна для limiter
limiter = None


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
             'X-RateLimit-Reset'
         ])

    # Rate Limiting
    global limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[config.RATELIMIT_DEFAULT] if config.RATELIMIT_ENABLED else [],
        storage_uri=config.RATELIMIT_STORAGE_URL if config.RATELIMIT_ENABLED else None,
        headers_enabled=config.RATELIMIT_HEADERS_ENABLED
    )

    # Реєстрація middleware
    register_middleware(app)

    # Реєстрація error handlers
    register_error_handlers(app)

    # Реєстрація blueprints
    register_blueprints(app)

    # Реєстрація базових маршрутів
    register_base_routes(app)

    logger.info("✅ Flask app created successfully")

    return app


def register_middleware(app):
    """Реєстрація middleware"""

    @app.before_request
    def before_request():
        """Виконується перед кожним запитом"""
        # Request ID для трейсингу
        request.request_id = request.headers.get('X-Request-ID',
                                                 f"req_{int(datetime.utcnow().timestamp() * 1000)}")

        # Логування запиту
        logger.info(f"[{request.request_id}] {request.method} {request.path} from {request.remote_addr}")

        # Ініціалізація g об'єкта
        g.start_time = datetime.utcnow()
        g.current_user = None
        g.jwt_payload = None

    @app.after_request
    def after_request(response):
        """Виконується після кожного запиту"""
        # Додаємо security headers
        for header, value in config.SECURITY_HEADERS.items():
            response.headers[header] = value

        # Додаємо request ID
        response.headers['X-Request-ID'] = getattr(request, 'request_id', '')

        # Додаємо час обробки
        if hasattr(g, 'start_time'):
            duration = (datetime.utcnow() - g.start_time).total_seconds()
            response.headers['X-Response-Time'] = f"{duration:.3f}s"

        # Логування відповіді
        logger.info(f"[{getattr(request, 'request_id', '')}] Response: {response.status_code}")

        return response

    @app.teardown_appcontext
    def teardown_db(exception):
        """Очищення ресурсів після запиту"""
        if exception:
            logger.error(f"Request teardown with exception: {exception}")


def register_error_handlers(app):
    """Реєстрація обробників помилок"""

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Endpoint not found',
            'code': 'NOT_FOUND',
            'path': request.path
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'success': False,
            'error': 'Method not allowed',
            'code': 'METHOD_NOT_ALLOWED',
            'allowed_methods': error.valid_methods if hasattr(error, 'valid_methods') else []
        }), 405

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'code': 'BAD_REQUEST',
            'message': str(error) if config.DEBUG else 'Invalid request'
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'code': 'UNAUTHORIZED'
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'code': 'FORBIDDEN'
        }), 403

    @app.errorhandler(429)
    def ratelimit_exceeded(error):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded',
            'code': 'RATE_LIMIT_EXCEEDED',
            'retry_after': error.description if hasattr(error, 'description') else 60
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'request_id': getattr(request, 'request_id', '')
        }), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Обробка всіх інших винятків"""
        # Якщо це HTTP виняток - передаємо його далі
        if isinstance(error, HTTPException):
            return error

        # Логуємо помилку
        logger.error(f"Unhandled exception: {error}", exc_info=True)

        # Повертаємо generic помилку
        return jsonify({
            'success': False,
            'error': 'An error occurred',
            'code': 'UNKNOWN_ERROR',
            'request_id': getattr(request, 'request_id', ''),
            'message': str(error) if config.DEBUG else 'An error occurred'
        }), 500


def register_blueprints(app):
    """Реєстрація всіх blueprints"""

    # Auth routes - повністю готові
    from backend.auth.routes import auth_bp
    app.register_blueprint(auth_bp)
    logger.info("✅ Auth blueprint registered")

    # Для решти створюємо тимчасові заглушки
    # щоб додаток міг запуститися

    from flask import Blueprint

    # === Users Blueprint ===
    users_bp = Blueprint('users', __name__, url_prefix='/api/users')

    @users_bp.route('/balance')
    def get_balance():
        from backend.auth.decorators import jwt_required
        # Заглушка - потім замінимо на реальну реалізацію
        return jsonify({
            'success': True,
            'data': {
                'balance': 0.00,
                'currency': 'UAH'
            }
        })

    @users_bp.route('/transactions')
    def get_transactions():
        return jsonify({
            'success': True,
            'data': {
                'transactions': [],
                'total': 0
            }
        })

    app.register_blueprint(users_bp)
    logger.info("✅ Users blueprint registered (stub)")

    # === Services Blueprint ===
    services_bp = Blueprint('services', __name__, url_prefix='/api/services')

    @services_bp.route('/')
    def get_services():
        return jsonify({
            'success': True,
            'data': {
                'services': [],
                'categories': []
            }
        })

    @services_bp.route('/<int:service_id>')
    def get_service(service_id):
        return jsonify({
            'success': False,
            'error': 'Service not found',
            'code': 'NOT_FOUND'
        }), 404

    app.register_blueprint(services_bp)
    logger.info("✅ Services blueprint registered (stub)")

    # === Orders Blueprint ===
    orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')

    @orders_bp.route('/', methods=['GET'])
    def get_orders():
        return jsonify({
            'success': True,
            'data': {
                'orders': [],
                'total': 0
            }
        })

    @orders_bp.route('/', methods=['POST'])
    def create_order():
        return jsonify({
            'success': False,
            'error': 'Orders not implemented yet',
            'code': 'NOT_IMPLEMENTED'
        }), 501

    app.register_blueprint(orders_bp)
    logger.info("✅ Orders blueprint registered (stub)")

    # === Payments Blueprint ===
    payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')

    @payments_bp.route('/create', methods=['POST'])
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
    logger.info("✅ Payments blueprint registered (stub)")

    # === Referrals Blueprint ===
    referrals_bp = Blueprint('referrals', __name__, url_prefix='/api/referrals')

    @referrals_bp.route('/stats')
    def referral_stats():
        return jsonify({
            'success': True,
            'data': {
                'total_referrals': 0,
                'total_earned': 0.00,
                'referrals': []
            }
        })

    app.register_blueprint(referrals_bp)
    logger.info("✅ Referrals blueprint registered (stub)")

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
                    'transactions': 'GET /api/users/transactions'
                },
                'services': {
                    'list': 'GET /api/services',
                    'details': 'GET /api/services/{id}'
                },
                'orders': {
                    'list': 'GET /api/orders',
                    'create': 'POST /api/orders',
                    'details': 'GET /api/orders/{id}'
                },
                'payments': {
                    'create': 'POST /api/payments/create',
                    'webhooks': {
                        'cryptobot': 'POST /api/payments/webhooks/cryptobot',
                        'nowpayments': 'POST /api/payments/webhooks/nowpayments'
                    }
                },
                'referrals': {
                    'stats': 'GET /api/referrals/stats'
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
        """Статус API"""
        return jsonify({
            'success': True,
            'data': {
                'version': '1.0.0',
                'environment': config.ENV,
                'debug': config.DEBUG,
                'bot_username': config.BOT_USERNAME,
                'features': {
                    'auth': True,
                    'orders': False,  # Поки не реалізовано
                    'payments': False,  # Поки не реалізовано
                    'referrals': False  # Поки не реалізовано
                }
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