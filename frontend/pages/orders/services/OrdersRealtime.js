// frontend/pages/orders/services/OrdersRealtime.js
/**
 * Real-time сервіс для оновлення замовлень
 * Працює через realtimeService та забезпечує автоматичні оновлення
 */

import { realtimeService, RealtimeSubscriptions } from '../../../shared/services/RealtimeService.js';
import { ordersCache } from '../../../shared/services/CacheService.js';

export class OrdersRealtime {
  constructor() {
    this.subscriptions = new Map();
    this.callbacks = new Map();
    this.activeOrderIds = new Set();
    this.updateInterval = null;
    this.isActive = false;
  }

  /**
   * Запустити real-time оновлення
   */
  start() {
    if (this.isActive) return;

    this.isActive = true;

    // Підписка на створення нових замовлень
    const unsubNewOrder = RealtimeSubscriptions.onNewOrder((order) => {
      this.handleNewOrder(order);
    });
    this.subscriptions.set('new_order', unsubNewOrder);

    // Підписка на зміну статусу замовлень
    const unsubStatusChange = RealtimeSubscriptions.onOrderStatusChange((data) => {
      this.handleStatusChange(data);
    });
    this.subscriptions.set('status_change', unsubStatusChange);

    // Запускаємо періодичне оновлення активних замовлень
    this.startActiveOrdersUpdate();

    console.log('OrdersRealtime: Started');
  }

  /**
   * Зупинити real-time оновлення
   */
  stop() {
    if (!this.isActive) return;

    // Відписуємось від всіх подій
    this.subscriptions.forEach(unsubscribe => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    });
    this.subscriptions.clear();

    // Зупиняємо періодичне оновлення
    this.stopActiveOrdersUpdate();

    // Очищаємо трекінг
    this.activeOrderIds.clear();
    this.callbacks.clear();

    this.isActive = false;

    console.log('OrdersRealtime: Stopped');
  }

  /**
   * Підписатись на оновлення конкретного замовлення
   */
  trackOrder(orderId, callback) {
    if (!orderId || !callback) return;

    // Додаємо callback
    if (!this.callbacks.has(orderId)) {
      this.callbacks.set(orderId, new Set());
    }
    this.callbacks.get(orderId).add(callback);

    // Додаємо в активні якщо потрібно
    this.activeOrderIds.add(orderId);

    // Підписуємось на real-time оновлення
    const unsubscribe = RealtimeSubscriptions.trackOrder(orderId, (order) => {
      this.handleOrderUpdate(orderId, order);
    });

    // Повертаємо функцію для відписки
    return () => {
      const callbacks = this.callbacks.get(orderId);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.callbacks.delete(orderId);
          this.activeOrderIds.delete(orderId);
        }
      }
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    };
  }

  /**
   * Додати callback для всіх оновлень
   */
  onUpdate(callback) {
    const id = Date.now() + Math.random();
    this.callbacks.set(`global_${id}`, callback);

    return () => {
      this.callbacks.delete(`global_${id}`);
    };
  }

  /**
   * Обробка нового замовлення
   */
  handleNewOrder(order) {
    // Інвалідуємо кеш списку
    ordersCache.invalidatePattern('orders:*');

    // Сповіщаємо всі глобальні callbacks
    this.notifyGlobalCallbacks({
      type: 'new_order',
      order
    });

    // Додаємо в активні якщо воно в процесі
    if (order.status === 'processing' || order.status === 'in_progress') {
      this.activeOrderIds.add(order.id);
    }
  }

  /**
   * Обробка зміни статусу
   */
  handleStatusChange(data) {
    const { orderId, oldStatus, newStatus, order } = data;

    // Інвалідуємо кеш
    ordersCache.delete(`order:${orderId}`);
    ordersCache.invalidatePattern('orders:*');

    // Сповіщаємо callbacks для конкретного замовлення
    const callbacks = this.callbacks.get(orderId);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback({
            type: 'status_change',
            orderId,
            oldStatus,
            newStatus,
            order
          });
        } catch (error) {
          console.error('Error in order callback:', error);
        }
      });
    }

    // Сповіщаємо глобальні callbacks
    this.notifyGlobalCallbacks({
      type: 'status_change',
      orderId,
      oldStatus,
      newStatus,
      order
    });

    // Оновлюємо список активних замовлень
    if (newStatus === 'completed' || newStatus === 'cancelled' || newStatus === 'failed') {
      this.activeOrderIds.delete(orderId);
    }
  }

  /**
   * Обробка оновлення замовлення
   */
  handleOrderUpdate(orderId, order) {
    // Інвалідуємо кеш
    ordersCache.delete(`order:${orderId}`);

    // Сповіщаємо callbacks
    const callbacks = this.callbacks.get(orderId);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback({
            type: 'order_update',
            orderId,
            order
          });
        } catch (error) {
          console.error('Error in order callback:', error);
        }
      });
    }

    // Сповіщаємо глобальні callbacks
    this.notifyGlobalCallbacks({
      type: 'order_update',
      orderId,
      order
    });
  }

  /**
   * Сповістити всі глобальні callbacks
   */
  notifyGlobalCallbacks(data) {
    this.callbacks.forEach((callback, key) => {
      if (key.startsWith('global_')) {
        try {
          callback(data);
        } catch (error) {
          console.error('Error in global callback:', error);
        }
      }
    });
  }

  /**
   * Запустити періодичне оновлення активних замовлень
   */
  startActiveOrdersUpdate() {
    // Оновлюємо кожні 30 секунд
    this.updateInterval = setInterval(() => {
      this.updateActiveOrders();
    }, 30000);

    // Перше оновлення через 5 секунд
    setTimeout(() => {
      this.updateActiveOrders();
    }, 5000);
  }

  /**
   * Зупинити періодичне оновлення
   */
  stopActiveOrdersUpdate() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }
  }

  /**
   * Оновити всі активні замовлення
   */
  async updateActiveOrders() {
    if (this.activeOrderIds.size === 0) return;

    try {
      const { ordersAPI } = await import('./OrdersAPI.js');
      const orderIds = Array.from(this.activeOrderIds);

      // Масове оновлення статусів
      const result = await ordersAPI.bulkStatus(orderIds);

      console.log(`OrdersRealtime: Updated ${result.updated} of ${result.total} orders`);
    } catch (error) {
      console.error('Error updating active orders:', error);
    }
  }

  /**
   * Отримати кількість активних замовлень
   */
  getActiveOrdersCount() {
    return this.activeOrderIds.size;
  }

  /**
   * Перевірити чи замовлення відслідковується
   */
  isTracking(orderId) {
    return this.activeOrderIds.has(orderId);
  }

  /**
   * Форсувати оновлення конкретного замовлення
   */
  async forceUpdate(orderId) {
    try {
      const { ordersAPI } = await import('./OrdersAPI.js');
      const result = await ordersAPI.checkStatus(orderId);

      if (result.updated) {
        // Якщо оновлено - сповіщаємо callbacks
        const order = await ordersAPI.get(orderId);
        this.handleOrderUpdate(orderId, order.order);
      }

      return result;
    } catch (error) {
      console.error('Error forcing order update:', error);
      throw error;
    }
  }

  /**
   * Отримати статистику real-time
   */
  getStats() {
    return {
      isActive: this.isActive,
      activeOrders: this.activeOrderIds.size,
      trackedOrders: Array.from(this.callbacks.keys()).filter(k => !k.startsWith('global_')).length,
      globalCallbacks: Array.from(this.callbacks.keys()).filter(k => k.startsWith('global_')).length
    };
  }
}

// Створюємо singleton інстанс
export const ordersRealtime = new OrdersRealtime();

// Хелпери для швидкого доступу
export const OrdersRealtimeHelpers = {
  start: () => ordersRealtime.start(),
  stop: () => ordersRealtime.stop(),
  track: (orderId, callback) => ordersRealtime.trackOrder(orderId, callback),
  onUpdate: (callback) => ordersRealtime.onUpdate(callback),
  forceUpdate: (orderId) => ordersRealtime.forceUpdate(orderId),
  getStats: () => ordersRealtime.getStats(),
  isActive: () => ordersRealtime.isActive
};

// Auto-start якщо сторінка orders
if (typeof window !== 'undefined' && window.location.pathname === '/orders') {
  window.addEventListener('DOMContentLoaded', () => {
    ordersRealtime.start();
  });

  // Stop при виході зі сторінки
  window.addEventListener('beforeunload', () => {
    ordersRealtime.stop();
  });
}

export default ordersRealtime;