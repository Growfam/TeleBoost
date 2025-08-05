// frontend/pages/orders/services/OrdersAPI.js
/**
 * API сервіс для роботи з замовленнями
 * FIXED: Використовує apiClient правильно
 */

import { apiClient } from '../../../shared/services/APIClient.js';
import { ordersCache } from '../../../shared/services/CacheService.js';

export class OrdersAPI {
  /**
   * Отримати список замовлень користувача
   */
  static async getOrders(params = {}) {
    try {
      console.log('OrdersAPI: Getting orders with params:', params);

      const cacheKey = `orders:${JSON.stringify(params)}`;

      // Перевіряємо кеш
      const cached = ordersCache.get(cacheKey);
      if (cached) {
        console.log('OrdersAPI: Returning cached orders');
        return cached;
      }

      // Запит до API
      const response = await apiClient.get('/orders', {
        page: params.page || 1,
        limit: params.limit || 20,
        status: params.status,
        search: params.search,
        sort: params.sort || 'created_at:desc'
      });

      console.log('OrdersAPI: Got response:', {
        success: response.success,
        ordersCount: response.data?.orders?.length || 0
      });

      if (response.success && response.data) {
        // Кешуємо на 1 хвилину
        ordersCache.set(cacheKey, response.data, 60000);
        return response.data;
      }

      throw new Error(response.error || 'Failed to fetch orders');
    } catch (error) {
      console.error('OrdersAPI: Error fetching orders:', error);
      throw error;
    }
  }

  /**
   * Отримати деталі конкретного замовлення
   */
  static async getOrderDetails(orderId) {
    try {
      console.log('OrdersAPI: Getting order details:', orderId);

      const cacheKey = `order:${orderId}`;

      // Перевіряємо кеш
      const cached = ordersCache.get(cacheKey);
      if (cached) {
        console.log('OrdersAPI: Returning cached order');
        return cached;
      }

      const response = await apiClient.get(`/orders/${orderId}`);

      console.log('OrdersAPI: Got order details response:', {
        success: response.success,
        hasOrder: !!response.data?.order
      });

      if (response.success && response.data) {
        // Кешуємо на 30 секунд
        ordersCache.set(cacheKey, response.data, 30000);
        return response.data;
      }

      throw new Error(response.error || 'Failed to fetch order details');
    } catch (error) {
      console.error('OrdersAPI: Error fetching order details:', error);
      throw error;
    }
  }

  /**
   * Створити нове замовлення
   */
  static async createOrder(orderData) {
    try {
      console.log('OrdersAPI: Creating order:', orderData);

      const response = await apiClient.post('/orders', orderData);

      console.log('OrdersAPI: Create order response:', {
        success: response.success,
        orderId: response.data?.order?.id
      });

      if (response.success && response.data) {
        // Інвалідуємо кеш списку замовлень
        ordersCache.invalidatePattern('orders:*');
        return response.data;
      }

      throw new Error(response.error || 'Failed to create order');
    } catch (error) {
      console.error('OrdersAPI: Error creating order:', error);
      throw error;
    }
  }

  /**
   * Скасувати замовлення
   */
  static async cancelOrder(orderId) {
    try {
      console.log('OrdersAPI: Cancelling order:', orderId);

      const response = await apiClient.post(`/orders/${orderId}/cancel`);

      console.log('OrdersAPI: Cancel order response:', {
        success: response.success
      });

      if (response.success) {
        // Інвалідуємо кеш
        ordersCache.delete(`order:${orderId}`);
        ordersCache.invalidatePattern('orders:*');
        return response.data || response;
      }

      throw new Error(response.error || 'Failed to cancel order');
    } catch (error) {
      console.error('OrdersAPI: Error cancelling order:', error);
      throw error;
    }
  }

  /**
   * Запросити поповнення для замовлення
   */
  static async requestRefill(orderId) {
    try {
      console.log('OrdersAPI: Requesting refill for order:', orderId);

      const response = await apiClient.post(`/orders/${orderId}/refill`);

      console.log('OrdersAPI: Refill response:', {
        success: response.success
      });

      if (response.success) {
        // Інвалідуємо кеш
        ordersCache.delete(`order:${orderId}`);
        return response.data || response;
      }

      throw new Error(response.error || 'Failed to request refill');
    } catch (error) {
      console.error('OrdersAPI: Error requesting refill:', error);
      throw error;
    }
  }

  /**
   * Повторити замовлення
   */
  static async repeatOrder(orderId) {
    try {
      console.log('OrdersAPI: Repeating order:', orderId);

      // Отримуємо деталі оригінального замовлення
      const orderDetails = await this.getOrderDetails(orderId);

      if (!orderDetails.order) {
        throw new Error('Order not found');
      }

      const { service_id, link, quantity, metadata } = orderDetails.order;

      // Створюємо нове замовлення з тими ж параметрами
      const newOrderData = {
        service_id,
        link,
        quantity,
        ...metadata?.parameters
      };

      return await this.createOrder(newOrderData);
    } catch (error) {
      console.error('OrdersAPI: Error repeating order:', error);
      throw error;
    }
  }

  /**
   * Оновити статус замовлення
   */
  static async checkOrderStatus(orderId) {
    try {
      console.log('OrdersAPI: Checking order status:', orderId);

      const response = await apiClient.get(`/orders/${orderId}/status`);

      console.log('OrdersAPI: Status check response:', {
        success: response.success,
        updated: response.data?.updated
      });

      if (response.success) {
        // Оновлюємо кеш якщо статус змінився
        if (response.data?.updated) {
          ordersCache.delete(`order:${orderId}`);
          ordersCache.invalidatePattern('orders:*');
        }

        return response.data;
      }

      throw new Error(response.error || 'Failed to check order status');
    } catch (error) {
      console.error('OrdersAPI: Error checking order status:', error);
      throw error;
    }
  }

  /**
   * Отримати статистику замовлень
   */
  static async getOrderStatistics() {
    try {
      console.log('OrdersAPI: Getting order statistics');

      const cacheKey = 'orders:statistics';

      // Перевіряємо кеш
      const cached = ordersCache.get(cacheKey);
      if (cached) {
        return cached;
      }

      const response = await apiClient.get('/orders/statistics');

      console.log('OrdersAPI: Statistics response:', {
        success: response.success
      });

      if (response.success && response.data) {
        // Кешуємо на 5 хвилин
        ordersCache.set(cacheKey, response.data, 300000);
        return response.data;
      }

      throw new Error(response.error || 'Failed to fetch statistics');
    } catch (error) {
      console.error('OrdersAPI: Error fetching statistics:', error);
      throw error;
    }
  }

  /**
   * Масове оновлення статусів
   */
  static async bulkUpdateStatus(orderIds) {
    try {
      console.log('OrdersAPI: Bulk updating statuses for', orderIds.length, 'orders');

      const promises = orderIds.map(id => this.checkOrderStatus(id));
      const results = await Promise.allSettled(promises);

      const updated = results.filter(r => r.status === 'fulfilled' && r.value?.updated).length;

      if (updated > 0) {
        // Інвалідуємо кеш
        ordersCache.invalidatePattern('orders:*');
      }

      return {
        total: orderIds.length,
        updated,
        failed: results.filter(r => r.status === 'rejected').length
      };
    } catch (error) {
      console.error('OrdersAPI: Error bulk updating:', error);
      throw error;
    }
  }
}

// Експортуємо хелпер функції
export const ordersAPI = {
  list: (params) => OrdersAPI.getOrders(params),
  get: (id) => OrdersAPI.getOrderDetails(id),
  create: (data) => OrdersAPI.createOrder(data),
  cancel: (id) => OrdersAPI.cancelOrder(id),
  refill: (id) => OrdersAPI.requestRefill(id),
  repeat: (id) => OrdersAPI.repeatOrder(id),
  checkStatus: (id) => OrdersAPI.checkOrderStatus(id),
  statistics: () => OrdersAPI.getOrderStatistics(),
  bulkStatus: (ids) => OrdersAPI.bulkUpdateStatus(ids)
};

export default OrdersAPI;