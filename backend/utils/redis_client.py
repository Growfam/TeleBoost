# backend/utils/redis_client.py
"""
TeleBoost Redis Client
Клієнт для роботи з Redis кешем
"""
import redis
import json
import pickle
import logging
from typing import Any, Optional, Union, List, Dict
from datetime import timedelta

from backend.config import config

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis клієнт з підтримкою різних типів даних"""

    def __init__(self):
        """Ініціалізація Redis підключення"""
        try:
            # Парсимо Redis URL
            self.client = redis.from_url(
                config.REDIS_URL,
                decode_responses=config.REDIS_DECODE_RESPONSES,
                max_connections=config.REDIS_MAX_CONNECTIONS,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 1,  # TCP_KEEPINTVL
                    3: 1,  # TCP_KEEPCNT
                }
            )
            # Тестуємо підключення
            self.client.ping()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.client = None

    def _serialize(self, value: Any) -> str:
        """Серіалізація значення"""
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        elif isinstance(value, (str, int, float, bool)):
            return str(value)
        else:
            # Для складних об'єктів використовуємо pickle
            return pickle.dumps(value).hex()

    def _deserialize(self, value: str, data_type: str = 'auto') -> Any:
        """Десеріалізація значення"""
        if value is None:
            return None

        if data_type == 'json' or (data_type == 'auto' and value.startswith('{') or value.startswith('[')):
            try:
                return json.loads(value)
            except:
                pass

        if data_type == 'int':
            return int(value)
        elif data_type == 'float':
            return float(value)
        elif data_type == 'bool':
            return value.lower() in ('true', '1', 'yes')

        # Спробуємо pickle
        try:
            return pickle.loads(bytes.fromhex(value))
        except:
            return value

    def get(self, key: str, default: Any = None, data_type: str = 'auto') -> Any:
        """Отримати значення з кешу"""
        if not self.client:
            return default

        try:
            value = self.client.get(key)
            if value is None:
                return default
            return self._deserialize(value, data_type)
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Зберегти значення в кеш"""
        if not self.client:
            return False

        try:
            serialized = self._serialize(value)
            if ttl:
                return self.client.setex(key, ttl, serialized)
            else:
                return self.client.set(key, serialized)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    def delete(self, *keys: str) -> int:
        """Видалити ключі"""
        if not self.client:
            return 0

        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return 0

    def exists(self, *keys: str) -> int:
        """Перевірити існування ключів"""
        if not self.client:
            return 0

        try:
            return self.client.exists(*keys)
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return 0

    def expire(self, key: str, seconds: int) -> bool:
        """Встановити TTL для ключа"""
        if not self.client:
            return False

        try:
            return self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis expire error for key {key}: {e}")
            return False

    def ttl(self, key: str) -> int:
        """Отримати TTL ключа"""
        if not self.client:
            return -2

        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error(f"Redis ttl error for key {key}: {e}")
            return -2

    def incr(self, key: str, amount: int = 1) -> int:
        """Інкрементувати значення"""
        if not self.client:
            return 0

        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis incr error for key {key}: {e}")
            return 0

    def decr(self, key: str, amount: int = 1) -> int:
        """Декрементувати значення"""
        if not self.client:
            return 0

        try:
            return self.client.decrby(key, amount)
        except Exception as e:
            logger.error(f"Redis decr error for key {key}: {e}")
            return 0

    def hget(self, name: str, key: str, default: Any = None, data_type: str = 'auto') -> Any:
        """Отримати значення з хешу"""
        if not self.client:
            return default

        try:
            value = self.client.hget(name, key)
            if value is None:
                return default
            return self._deserialize(value, data_type)
        except Exception as e:
            logger.error(f"Redis hget error for {name}:{key}: {e}")
            return default

    def hset(self, name: str, key: str, value: Any) -> bool:
        """Встановити значення в хеш"""
        if not self.client:
            return False

        try:
            serialized = self._serialize(value)
            return self.client.hset(name, key, serialized)
        except Exception as e:
            logger.error(f"Redis hset error for {name}:{key}: {e}")
            return False

    def hgetall(self, name: str, data_type: str = 'auto') -> Dict[str, Any]:
        """Отримати весь хеш"""
        if not self.client:
            return {}

        try:
            data = self.client.hgetall(name)
            return {k: self._deserialize(v, data_type) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Redis hgetall error for {name}: {e}")
            return {}

    def hdel(self, name: str, *keys: str) -> int:
        """Видалити ключі з хешу"""
        if not self.client:
            return 0

        try:
            return self.client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Redis hdel error for {name}: {e}")
            return 0

    def sadd(self, key: str, *values: Any) -> int:
        """Додати елементи в set"""
        if not self.client:
            return 0

        try:
            serialized = [self._serialize(v) for v in values]
            return self.client.sadd(key, *serialized)
        except Exception as e:
            logger.error(f"Redis sadd error for {key}: {e}")
            return 0

    def smembers(self, key: str, data_type: str = 'auto') -> set:
        """Отримати всі елементи set"""
        if not self.client:
            return set()

        try:
            members = self.client.smembers(key)
            return {self._deserialize(m, data_type) for m in members}
        except Exception as e:
            logger.error(f"Redis smembers error for {key}: {e}")
            return set()

    def srem(self, key: str, *values: Any) -> int:
        """Видалити елементи з set"""
        if not self.client:
            return 0

        try:
            serialized = [self._serialize(v) for v in values]
            return self.client.srem(key, *serialized)
        except Exception as e:
            logger.error(f"Redis srem error for {key}: {e}")
            return 0

    def keys(self, pattern: str) -> List[str]:
        """Знайти ключі за паттерном"""
        if not self.client:
            return []

        try:
            return self.client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis keys error for pattern {pattern}: {e}")
            return []

    def flushdb(self) -> bool:
        """Очистити всю БД (обережно!)"""
        if not self.client:
            return False

        try:
            return self.client.flushdb()
        except Exception as e:
            logger.error(f"Redis flushdb error: {e}")
            return False

    def ping(self) -> bool:
        """Перевірити з'єднання"""
        if not self.client:
            return False

        try:
            return self.client.ping()
        except:
            return False

    def pipeline(self):
        """Створити pipeline для batch операцій"""
        if not self.client:
            return None
        return self.client.pipeline()

    def execute_pipeline(self, pipe) -> List[Any]:
        """Виконати pipeline"""
        try:
            return pipe.execute()
        except Exception as e:
            logger.error(f"Redis pipeline execute error: {e}")
            return []


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
    key = CACHE_KEYS.format(CACHE_KEYS.USER, user_id=user_id)
    ttl = ttl or config.CACHE_TTL.get('user', 300)
    return cache_set(key, data, ttl)


def get_cached_user_data(user_id: str) -> Optional[dict]:
    """Отримати кешовані дані користувача"""
    from backend.utils.constants import CACHE_KEYS
    key = CACHE_KEYS.format(CACHE_KEYS.USER, user_id=user_id)
    return cache_get(key, data_type='json')


def invalidate_user_cache(user_id: str):
    """Інвалідувати весь кеш користувача"""
    from backend.utils.constants import CACHE_KEYS
    patterns = [
        CACHE_KEYS.format(CACHE_KEYS.USER, user_id=user_id),
        CACHE_KEYS.format(CACHE_KEYS.USER_BALANCE, user_id=user_id),
        CACHE_KEYS.format(CACHE_KEYS.USER_ORDERS, user_id=user_id),
        CACHE_KEYS.format(CACHE_KEYS.USER_REFERRALS, user_id=user_id),
    ]
    return cache_delete(*patterns)