# backend/utils/redis_client.py
"""
TeleBoost Redis Client
Надійний клієнт для роботи з Redis на Railway
"""
import redis
import json
import pickle
import logging
import time
from typing import Any, Optional, Union, List, Dict
from datetime import timedelta
from urllib.parse import urlparse

from backend.config import config

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis клієнт з підтримкою Railway та graceful degradation"""

    def __init__(self):
        """Ініціалізація Redis підключення"""
        self.client = None
        self._connection_attempts = 0
        self._max_retries = 3
        self._retry_delay = 1.0

        # Спробуємо підключитися
        self._connect()

    def _connect(self):
        """Підключення до Redis з retry логікою"""
        while self._connection_attempts < self._max_retries:
            try:
                self._connection_attempts += 1

                # Парсимо URL для визначення SSL
                parsed_url = urlparse(config.REDIS_URL)
                use_ssl = parsed_url.scheme == 'rediss'

                # Базові параметри підключення
                connection_kwargs = {
                    'decode_responses': config.REDIS_DECODE_RESPONSES,
                    'max_connections': 10,  # Менше connections для Railway
                    'socket_connect_timeout': 30,
                    'socket_timeout': 30,
                    'retry_on_timeout': True,
                    'retry_on_error': [redis.ConnectionError, redis.TimeoutError],
                    'socket_keepalive': True,
                    'health_check_interval': 30,
                }

                # Додаємо SSL параметри якщо потрібно
                if use_ssl:
                    connection_kwargs.update({
                        'ssl': True,
                        'ssl_cert_reqs': None,
                        'ssl_ca_certs': None,
                        'ssl_check_hostname': False,
                    })

                # Створюємо connection pool
                pool = redis.ConnectionPool.from_url(
                    config.REDIS_URL,
                    **connection_kwargs
                )

                # Створюємо клієнт
                self.client = redis.Redis(connection_pool=pool)

                # Тестуємо підключення
                self.client.ping()

                logger.info(f"✅ Redis connected successfully (attempt {self._connection_attempts})")
                self._connection_attempts = 0  # Reset counter on success
                return True

            except redis.RedisError as e:
                logger.warning(
                    f"Redis connection attempt {self._connection_attempts} failed: {type(e).__name__}: {str(e)}")

                if self._connection_attempts < self._max_retries:
                    time.sleep(self._retry_delay * self._connection_attempts)
                    continue
                else:
                    logger.error(f"❌ Redis connection failed after {self._max_retries} attempts")
                    self.client = None
                    return False

            except Exception as e:
                logger.error(f"❌ Unexpected error connecting to Redis: {type(e).__name__}: {str(e)}")
                self.client = None
                return False

    def _ensure_connected(self):
        """Перевірка та відновлення підключення якщо потрібно"""
        if not self.client:
            return False

        try:
            self.client.ping()
            return True
        except:
            # Спробуємо перепідключитися
            logger.info("Redis connection lost, attempting to reconnect...")
            self._connection_attempts = 0
            return self._connect()

    def _serialize(self, value: Any) -> str:
        """Серіалізація значення"""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        elif isinstance(value, (str, int, float, bool)):
            return str(value)
        else:
            # Для складних об'єктів використовуємо pickle
            return pickle.dumps(value).hex()

    def _deserialize(self, value: str, data_type: str = 'auto') -> Any:
        """Десеріалізація значення"""
        if value is None:
            return None

        if data_type == 'json' or (data_type == 'auto' and (value.startswith('{') or value.startswith('['))):
            try:
                return json.loads(value)
            except:
                pass

        if data_type == 'int':
            try:
                return int(value)
            except:
                return 0
        elif data_type == 'float':
            try:
                return float(value)
            except:
                return 0.0
        elif data_type == 'bool':
            return value.lower() in ('true', '1', 'yes')

        # Спробуємо pickle
        try:
            return pickle.loads(bytes.fromhex(value))
        except:
            return value

    def get(self, key: str, default: Any = None, data_type: str = 'auto') -> Any:
        """Отримати значення з кешу"""
        if not self._ensure_connected():
            return default

        try:
            value = self.client.get(key)
            if value is None:
                return default
            return self._deserialize(value, data_type)
        except Exception as e:
            logger.debug(f"Redis get error for key {key}: {type(e).__name__}")
            return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Зберегти значення в кеш"""
        if not self._ensure_connected():
            return False

        try:
            serialized = self._serialize(value)

            if ttl and ttl > 0:
                return bool(self.client.setex(key, ttl, serialized))
            else:
                return bool(self.client.set(key, serialized))
        except Exception as e:
            logger.debug(f"Redis set error for key {key}: {type(e).__name__}")
            return False

    def delete(self, *keys: str) -> int:
        """Видалити ключі"""
        if not self._ensure_connected() or not keys:
            return 0

        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.debug(f"Redis delete error: {type(e).__name__}")
            return 0

    def exists(self, *keys: str) -> int:
        """Перевірити існування ключів"""
        if not self._ensure_connected() or not keys:
            return 0

        try:
            return self.client.exists(*keys)
        except Exception as e:
            logger.debug(f"Redis exists error: {type(e).__name__}")
            return 0

    def expire(self, key: str, seconds: int) -> bool:
        """Встановити TTL для ключа"""
        if not self._ensure_connected():
            return False

        try:
            return bool(self.client.expire(key, seconds))
        except Exception as e:
            logger.debug(f"Redis expire error for key {key}: {type(e).__name__}")
            return False

    def ttl(self, key: str) -> int:
        """Отримати TTL ключа"""
        if not self._ensure_connected():
            return -2

        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.debug(f"Redis ttl error for key {key}: {type(e).__name__}")
            return -2

    def incr(self, key: str, amount: int = 1) -> int:
        """Інкрементувати значення"""
        if not self._ensure_connected():
            return 0

        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.debug(f"Redis incr error for key {key}: {type(e).__name__}")
            return 0

    def decr(self, key: str, amount: int = 1) -> int:
        """Декрементувати значення"""
        if not self._ensure_connected():
            return 0

        try:
            return self.client.decrby(key, amount)
        except Exception as e:
            logger.debug(f"Redis decr error for key {key}: {type(e).__name__}")
            return 0

    def hget(self, name: str, key: str, default: Any = None, data_type: str = 'auto') -> Any:
        """Отримати значення з хешу"""
        if not self._ensure_connected():
            return default

        try:
            value = self.client.hget(name, key)
            if value is None:
                return default
            return self._deserialize(value, data_type)
        except Exception as e:
            logger.debug(f"Redis hget error for {name}:{key}: {type(e).__name__}")
            return default

    def hset(self, name: str, key: str, value: Any) -> bool:
        """Встановити значення в хеш"""
        if not self._ensure_connected():
            return False

        try:
            serialized = self._serialize(value)
            return bool(self.client.hset(name, key, serialized))
        except Exception as e:
            logger.debug(f"Redis hset error for {name}:{key}: {type(e).__name__}")
            return False

    def hgetall(self, name: str, data_type: str = 'auto') -> Dict[str, Any]:
        """Отримати весь хеш"""
        if not self._ensure_connected():
            return {}

        try:
            data = self.client.hgetall(name)
            return {k: self._deserialize(v, data_type) for k, v in data.items()}
        except Exception as e:
            logger.debug(f"Redis hgetall error for {name}: {type(e).__name__}")
            return {}

    def hdel(self, name: str, *keys: str) -> int:
        """Видалити ключі з хешу"""
        if not self._ensure_connected() or not keys:
            return 0

        try:
            return self.client.hdel(name, *keys)
        except Exception as e:
            logger.debug(f"Redis hdel error for {name}: {type(e).__name__}")
            return 0

    def sadd(self, key: str, *values: Any) -> int:
        """Додати елементи в set"""
        if not self._ensure_connected() or not values:
            return 0

        try:
            serialized = [self._serialize(v) for v in values]
            return self.client.sadd(key, *serialized)
        except Exception as e:
            logger.debug(f"Redis sadd error for {key}: {type(e).__name__}")
            return 0

    def smembers(self, key: str, data_type: str = 'auto') -> set:
        """Отримати всі елементи set"""
        if not self._ensure_connected():
            return set()

        try:
            members = self.client.smembers(key)
            return {self._deserialize(m, data_type) for m in members}
        except Exception as e:
            logger.debug(f"Redis smembers error for {key}: {type(e).__name__}")
            return set()

    def srem(self, key: str, *values: Any) -> int:
        """Видалити елементи з set"""
        if not self._ensure_connected() or not values:
            return 0

        try:
            serialized = [self._serialize(v) for v in values]
            return self.client.srem(key, *serialized)
        except Exception as e:
            logger.debug(f"Redis srem error for {key}: {type(e).__name__}")
            return 0

    def zadd(self, key: str, mapping: Dict[Any, float]) -> int:
        """Додати елементи в sorted set"""
        if not self._ensure_connected() or not mapping:
            return 0

        try:
            return self.client.zadd(key, mapping)
        except Exception as e:
            logger.debug(f"Redis zadd error for {key}: {type(e).__name__}")
            return 0

    def zcard(self, key: str) -> int:
        """Отримати кількість елементів в sorted set"""
        if not self._ensure_connected():
            return 0

        try:
            return self.client.zcard(key)
        except Exception as e:
            logger.debug(f"Redis zcard error for {key}: {type(e).__name__}")
            return 0

    def zremrangebyscore(self, key: str, min: Any, max: Any) -> int:
        """Видалити елементи з sorted set за score"""
        if not self._ensure_connected():
            return 0

        try:
            return self.client.zremrangebyscore(key, min, max)
        except Exception as e:
            logger.debug(f"Redis zremrangebyscore error for {key}: {type(e).__name__}")
            return 0

    def zrange(self, key: str, start: int, end: int, withscores: bool = False) -> list:
        """Отримати елементи з sorted set"""
        if not self._ensure_connected():
            return []

        try:
            return list(self.client.zrange(key, start, end, withscores=withscores))
        except Exception as e:
            logger.debug(f"Redis zrange error for {key}: {type(e).__name__}")
            return []

    def keys(self, pattern: str) -> List[str]:
        """Знайти ключі за паттерном"""
        if not self._ensure_connected():
            return []

        try:
            # Використовуємо scan замість keys для продуктивності
            keys = []
            cursor = 0
            while True:
                cursor, partial_keys = self.client.scan(cursor, match=pattern, count=100)
                keys.extend(partial_keys)
                if cursor == 0:
                    break
            return keys
        except Exception as e:
            logger.debug(f"Redis keys error for pattern {pattern}: {type(e).__name__}")
            return []

    def clear_pattern(self, pattern: str) -> int:
        """Видалити всі ключі за паттерном"""
        if not self._ensure_connected():
            return 0

        try:
            keys = self.keys(pattern)
            if keys:
                return self.delete(*keys)
            return 0
        except Exception as e:
            logger.debug(f"Redis clear pattern error: {type(e).__name__}")
            return 0

    def flushdb(self) -> bool:
        """Очистити всю БД (обережно!)"""
        if not self._ensure_connected():
            return False

        try:
            return bool(self.client.flushdb())
        except Exception as e:
            logger.debug(f"Redis flushdb error: {type(e).__name__}")
            return False

    def ping(self) -> bool:
        """Перевірити з'єднання"""
        try:
            if self.client:
                return self.client.ping()
            return False
        except:
            return False

    def pipeline(self):
        """Створити pipeline для batch операцій"""
        if not self._ensure_connected():
            return None
        return self.client.pipeline()

    def execute_pipeline(self, pipe) -> List[Any]:
        """Виконати pipeline"""
        if not pipe:
            return []
        try:
            return pipe.execute()
        except Exception as e:
            logger.debug(f"Redis pipeline execute error: {type(e).__name__}")
            return []

    def setex(self, key: str, seconds: int, value: Any) -> bool:
        """Встановити значення з TTL"""
        return self.set(key, value, ttl=seconds)

    def lpush(self, key: str, *values: Any) -> int:
        """Додати елементи на початок списку"""
        if not self._ensure_connected() or not values:
            return 0

        try:
            serialized = [self._serialize(v) for v in values]
            return self.client.lpush(key, *serialized)
        except Exception as e:
            logger.debug(f"Redis lpush error for {key}: {type(e).__name__}")
            return 0

    def rpush(self, key: str, *values: Any) -> int:
        """Додати елементи в кінець списку"""
        if not self._ensure_connected() or not values:
            return 0

        try:
            serialized = [self._serialize(v) for v in values]
            return self.client.rpush(key, *serialized)
        except Exception as e:
            logger.debug(f"Redis rpush error for {key}: {type(e).__name__}")
            return 0

    def lrange(self, key: str, start: int, end: int, data_type: str = 'auto') -> List[Any]:
        """Отримати елементи списку"""
        if not self._ensure_connected():
            return []

        try:
            values = self.client.lrange(key, start, end)
            return [self._deserialize(v, data_type) for v in values]
        except Exception as e:
            logger.debug(f"Redis lrange error for {key}: {type(e).__name__}")
            return []

    def llen(self, key: str) -> int:
        """Отримати довжину списку"""
        if not self._ensure_connected():
            return 0

        try:
            return self.client.llen(key)
        except Exception as e:
            logger.debug(f"Redis llen error for {key}: {type(e).__name__}")
            return 0

    def lpop(self, key: str, data_type: str = 'auto') -> Any:
        """Видалити та повернути перший елемент списку"""
        if not self._ensure_connected():
            return None

        try:
            value = self.client.lpop(key)
            if value is None:
                return None
            return self._deserialize(value, data_type)
        except Exception as e:
            logger.debug(f"Redis lpop error for {key}: {type(e).__name__}")
            return None

    def rpop(self, key: str, data_type: str = 'auto') -> Any:
        """Видалити та повернути останній елемент списку"""
        if not self._ensure_connected():
            return None

        try:
            value = self.client.rpop(key)
            if value is None:
                return None
            return self._deserialize(value, data_type)
        except Exception as e:
            logger.debug(f"Redis rpop error for {key}: {type(e).__name__}")
            return None

    def publish(self, channel: str, message: Any) -> int:
        """Опублікувати повідомлення в канал"""
        if not self._ensure_connected():
            return 0

        try:
            serialized = self._serialize(message)
            return self.client.publish(channel, serialized)
        except Exception as e:
            logger.debug(f"Redis publish error for channel {channel}: {type(e).__name__}")
            return 0

    def subscribe(self, *channels: str):
        """Підписатися на канали"""
        if not self._ensure_connected() or not channels:
            return None

        try:
            pubsub = self.client.pubsub()
            pubsub.subscribe(*channels)
            return pubsub
        except Exception as e:
            logger.debug(f"Redis subscribe error: {type(e).__name__}")
            return None

    def info(self) -> Dict[str, Any]:
        """Отримати інформацію про Redis сервер"""
        if not self._ensure_connected():
            return {}

        try:
            return self.client.info()
        except Exception as e:
            logger.debug(f"Redis info error: {type(e).__name__}")
            return {}

    def close(self):
        """Закрити підключення"""
        if self.client:
            try:
                self.client.close()
                logger.info("Redis connection closed")
            except:
                pass
            finally:
                self.client = None


# Створюємо глобальний екземпляр
redis_client = RedisClient()


# Допоміжні функції для кешування
def cache_get(key: str, default: Any = None, data_type: str = 'auto') -> Any:
    """Швидкий доступ до get"""
    return redis_client.get(key, default, data_type)


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Швидкий доступ до set"""
    return redis_client.set(key, value, ttl)


def cache_delete(*keys: str) -> int:
    """Швидкий доступ до delete"""
    return redis_client.delete(*keys)


def cache_user_data(user_id: str, data: dict, ttl: int = None) -> bool:
    """Кешувати дані користувача"""
    from backend.utils.constants import CACHE_KEYS
    key = CACHE_KEYS['USER'].format(user_id=user_id)
    ttl = ttl or config.CACHE_TTL.get('user', 300)
    return cache_set(key, data, ttl)


def get_cached_user_data(user_id: str) -> Optional[dict]:
    """Отримати кешовані дані користувача"""
    from backend.utils.constants import CACHE_KEYS
    key = CACHE_KEYS['USER'].format(user_id=user_id)
    return cache_get(key, data_type='json')


def invalidate_user_cache(user_id: str) -> int:
    """Інвалідувати весь кеш користувача"""
    from backend.utils.constants import CACHE_KEYS
    patterns = [
        CACHE_KEYS['USER'].format(user_id=user_id),
        CACHE_KEYS['USER_BALANCE'].format(user_id=user_id),
        CACHE_KEYS['USER_ORDERS'].format(user_id=user_id),
        CACHE_KEYS['USER_REFERRALS'].format(user_id=user_id),
    ]
    return cache_delete(*patterns)


def cache_service_data(service_id: int, data: dict, ttl: int = None) -> bool:
    """Кешувати дані сервісу"""
    from backend.utils.constants import CACHE_KEYS
    key = CACHE_KEYS['SERVICE'].format(service_id=service_id)
    ttl = ttl or config.CACHE_TTL.get('services', 3600)
    return cache_set(key, data, ttl)


def get_cached_service_data(service_id: int) -> Optional[dict]:
    """Отримати кешовані дані сервісу"""
    from backend.utils.constants import CACHE_KEYS
    key = CACHE_KEYS['SERVICE'].format(service_id=service_id)
    return cache_get(key, data_type='json')


def invalidate_service_cache(service_id: Optional[int] = None) -> int:
    """Інвалідувати кеш сервісів"""
    from backend.utils.constants import CACHE_KEYS

    if service_id:
        # Конкретний сервіс
        key = CACHE_KEYS['SERVICE'].format(service_id=service_id)
        return cache_delete(key)
    else:
        # Всі сервіси
        pattern = "service:*"
        deleted = redis_client.clear_pattern(pattern)
        # Також очищаємо список всіх сервісів
        cache_delete(CACHE_KEYS['SERVICES'])
        return deleted + 1


def get_or_set_cache(key: str, callback: callable, ttl: int = 300, data_type: str = 'auto') -> Any:
    """Отримати з кешу або встановити через callback"""
    # Спробуємо отримати з кешу
    cached = cache_get(key, data_type=data_type)
    if cached is not None:
        return cached

    # Викликаємо callback для отримання даних
    data = callback()

    # Кешуємо результат
    if data is not None:
        cache_set(key, data, ttl)

    return data