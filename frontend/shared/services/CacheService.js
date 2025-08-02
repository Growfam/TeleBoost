// frontend/shared/services/CacheService.js
/**
 * Сервіс для кешування даних в пам'яті
 * Підтримує TTL, LRU евікцію та автоматичне очищення
 */
export class CacheService {
  constructor(options = {}) {
    this.maxSize = options.maxSize || 100; // Максимальний розмір кешу
    this.defaultTTL = options.defaultTTL || 300000; // 5 хвилин
    this.cache = new Map();
    this.accessOrder = new Map(); // Для LRU
    this.timers = new Map(); // Таймери для TTL

    // Автоматичне очищення кожні 5 хвилин
    this.cleanupInterval = setInterval(() => this.cleanup(), 300000);
  }

  /**
   * Отримати значення з кешу
   */
  get(key) {
    const item = this.cache.get(key);

    if (!item) {
      return null;
    }

    // Перевіряємо чи не протухло
    if (item.expiry && Date.now() > item.expiry) {
      this.delete(key);
      return null;
    }

    // Оновлюємо час доступу для LRU
    this.accessOrder.set(key, Date.now());

    return item.value;
  }

  /**
   * Зберегти значення в кеш
   */
  set(key, value, ttl = this.defaultTTL) {
    // Якщо досягли максимального розміру - видаляємо найстаріший
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      this.evictLRU();
    }

    // Очищаємо старий таймер якщо є
    if (this.timers.has(key)) {
      clearTimeout(this.timers.get(key));
    }

    const expiry = ttl ? Date.now() + ttl : null;

    // Зберігаємо дані
    this.cache.set(key, { value, expiry });
    this.accessOrder.set(key, Date.now());

    // Встановлюємо таймер для автовидалення
    if (ttl) {
      const timer = setTimeout(() => this.delete(key), ttl);
      this.timers.set(key, timer);
    }

    return value;
  }

  /**
   * Видалити з кешу
   */
  delete(key) {
    if (this.timers.has(key)) {
      clearTimeout(this.timers.get(key));
      this.timers.delete(key);
    }

    this.cache.delete(key);
    this.accessOrder.delete(key);

    return true;
  }

  /**
   * Перевірити наявність в кеші
   */
  has(key) {
    const item = this.cache.get(key);

    if (!item) {
      return false;
    }

    // Перевіряємо чи не протухло
    if (item.expiry && Date.now() > item.expiry) {
      this.delete(key);
      return false;
    }

    return true;
  }

  /**
   * Очистити весь кеш
   */
  clear() {
    // Очищаємо всі таймери
    this.timers.forEach(timer => clearTimeout(timer));

    this.cache.clear();
    this.accessOrder.clear();
    this.timers.clear();
  }

  /**
   * Отримати розмір кешу
   */
  get size() {
    return this.cache.size;
  }

  /**
   * Видалити найстаріший елемент (LRU)
   */
  evictLRU() {
    let oldestKey = null;
    let oldestTime = Date.now();

    // Знаходимо найстаріший за часом доступу
    this.accessOrder.forEach((time, key) => {
      if (time < oldestTime) {
        oldestTime = time;
        oldestKey = key;
      }
    });

    if (oldestKey) {
      this.delete(oldestKey);
    }
  }

  /**
   * Очистити протухлі елементи
   */
  cleanup() {
    const now = Date.now();
    const keysToDelete = [];

    this.cache.forEach((item, key) => {
      if (item.expiry && now > item.expiry) {
        keysToDelete.push(key);
      }
    });

    keysToDelete.forEach(key => this.delete(key));
  }

  /**
   * Отримати або обчислити значення
   * Якщо в кеші немає - викликає функцію та кешує результат
   */
  async getOrSet(key, factory, ttl = this.defaultTTL) {
    // Перевіряємо кеш
    let value = this.get(key);

    if (value !== null) {
      return value;
    }

    // Обчислюємо значення
    value = await factory();

    // Кешуємо
    this.set(key, value, ttl);

    return value;
  }

  /**
   * Інвалідувати кеш за паттерном
   */
  invalidatePattern(pattern) {
    const regex = new RegExp(pattern);
    const keysToDelete = [];

    this.cache.forEach((_, key) => {
      if (regex.test(key)) {
        keysToDelete.push(key);
      }
    });

    keysToDelete.forEach(key => this.delete(key));

    return keysToDelete.length;
  }

  /**
   * Отримати статистику кешу
   */
  getStats() {
    let totalSize = 0;
    let expiredCount = 0;
    const now = Date.now();

    this.cache.forEach(item => {
      if (item.expiry && now > item.expiry) {
        expiredCount++;
      }
      // Приблизний розмір в байтах
      totalSize += JSON.stringify(item.value).length;
    });

    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      totalSizeBytes: totalSize,
      expiredCount,
      hitRate: this.calculateHitRate()
    };
  }

  /**
   * Розрахувати hit rate (потребує додаткового трекінгу)
   */
  calculateHitRate() {
    // Спрощена версія - можна розширити з детальним трекінгом
    return 0;
  }

  /**
   * Знищити сервіс (очистити інтервали)
   */
  destroy() {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }
    this.clear();
  }
}

// Створюємо глобальні інстанси для різних типів даних
export const servicesCache = new CacheService({
  maxSize: 200,
  defaultTTL: 3600000 // 1 година
});

export const ordersCache = new CacheService({
  maxSize: 100,
  defaultTTL: 180000 // 3 хвилини
});

export const userCache = new CacheService({
  maxSize: 50,
  defaultTTL: 300000 // 5 хвилин
});

export const generalCache = new CacheService({
  maxSize: 100,
  defaultTTL: 600000 // 10 хвилин
});

// Хелпер для кешування API запитів
export function withCache(cacheInstance, keyPrefix) {
  return function(target, propertyKey, descriptor) {
    const originalMethod = descriptor.value;

    descriptor.value = async function(...args) {
      const cacheKey = `${keyPrefix}:${propertyKey}:${JSON.stringify(args)}`;

      // Пробуємо отримати з кешу
      const cached = cacheInstance.get(cacheKey);
      if (cached !== null) {
        return cached;
      }

      // Викликаємо оригінальний метод
      const result = await originalMethod.apply(this, args);

      // Кешуємо результат
      cacheInstance.set(cacheKey, result);

      return result;
    };

    return descriptor;
  };
}

// Клас для кешування з підтримкою промісів
export class PromiseCache extends CacheService {
  constructor(options) {
    super(options);
    this.pendingPromises = new Map();
  }

  /**
   * Отримати або обчислити з дедуплікацією промісів
   */
  async getOrSet(key, factory, ttl = this.defaultTTL) {
    // Перевіряємо кеш
    const cached = this.get(key);
    if (cached !== null) {
      return cached;
    }

    // Перевіряємо чи вже виконується запит
    if (this.pendingPromises.has(key)) {
      return this.pendingPromises.get(key);
    }

    // Створюємо новий проміс
    const promise = factory().then(
      value => {
        this.set(key, value, ttl);
        this.pendingPromises.delete(key);
        return value;
      },
      error => {
        this.pendingPromises.delete(key);
        throw error;
      }
    );

    this.pendingPromises.set(key, promise);
    return promise;
  }

  clear() {
    super.clear();
    this.pendingPromises.clear();
  }
}

// Експортуємо глобальний інстанс для промісів
export const promiseCache = new PromiseCache({
  maxSize: 100,
  defaultTTL: 300000
});

export default CacheService;