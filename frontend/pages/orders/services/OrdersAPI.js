// frontend/pages/orders/services/OrdersAPI.js
/**
 * API сервіс для роботи з замовленнями
 * Production версія з кешуванням та обробкою помилок
 */

import { apiClient } from '../../../shared/services/APIClient.js';
import { ordersCache } from '../../../shared/services/CacheService.js';

export class OrdersAPI {
  /**
   * Отримати список замовлень користувача
   */
  static async getOrders(params = {}) {
    try {
      const cacheKey = `orders:${JSON.stringify(params)}`;

      // Перевіряємо кеш
      const cached = ordersCache.get(cacheKey);
      if (cached) {
        return cached;
      }

      const response = await apiClient.get('/orders', {
        page: params.page || 1,
        limit: params.limit || 20,
        status: params.status,
        search: params.search,
        sort: params.sort || 'created_at:desc'
      });

      if (response.success) {
        // Кешуємо на 1 хвилину
        ordersCache.set(cacheKey, response.data, 60000);
        return response.data;
      }

      throw new Error(response.error || 'Failed to fetch orders');
    } catch (error) {
      console.error('Error fetching orders:', error);
      throw error;
    }
  }

  /**
   * Отримати деталі конкретного замовлення
   */
  static async getOrderDetails(orderId) {
    try {
      const cacheKey = `order:${orderId}`;

      // Перевіряємо кеш
      const cached = ordersCache.get(cacheKey);
      if (cached) {
        return cached;
      }

      const response = await apiClient.get(`/orders/${orderId}`);

      if (response.success) {
        // Кешуємо на 30 секунд
        ordersCache.set(cacheKey, response.data, 30000);
        return response.data;
      }

      throw new Error(response.error || 'Failed to fetch order details');
    } catch (error) {
      console.error('Error fetching order details:', error);
      throw error;
    }
  }

  /**
   * Створити нове замовлення
   */
  static async createOrder(orderData) {
    try {
      const response = await apiClient.post('/orders', orderData);

      if (response.success) {
        // Інвалідуємо кеш списку замовлень
        ordersCache.invalidatePattern('orders:*');
        return response.data;
      }

      throw new Error(response.error || 'Failed to create order');
    } catch (error) {
      console.error('Error creating order:', error);
      throw error;
    }
  }

  /**
   * Скасувати замовлення
   */
  static async cancelOrder(orderId) {
    try {
      const response = await apiClient.post(`/orders/${orderId}/cancel`);

      if (response.success) {
        // Інвалідуємо кеш
        ordersCache.delete(`order:${orderId}`);
        ordersCache.invalidatePattern('orders:*');
        return response.data;
      }

      throw new Error(response.error || 'Failed to cancel order');
    } catch (error) {
      console.error('Error cancelling order:', error);
      throw error;
    }
  }

  /**
   * Запросити поповнення для замовлення
   */
  static async requestRefill(orderId) {
    try {
      const response = await apiClient.post(`/orders/${orderId}/refill`);

      if (response.success) {
        // Інвалідуємо кеш
        ordersCache.delete(`order:${orderId}`);
        return response.data;
      }

      throw new Error(response.error || 'Failed to request refill');
    } catch (error) {
      console.error('Error requesting refill:', error);
      throw error;
    }
  }

  /**
   * Повторити замовлення
   */
  static async repeatOrder(orderId) {
    try {
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
      console.error('Error repeating order:', error);
      throw error;
    }
  }

  /**
   * Оновити статус замовлення (перевірка з API)
   */
  static async checkOrderStatus(orderId) {
    try {
      const response = await apiClient.get(`/orders/${orderId}/status`);

      if (response.success) {
        // Оновлюємо кеш якщо статус змінився
        if (response.data.updated) {
          ordersCache.delete(`order:${orderId}`);
          ordersCache.invalidatePattern('orders:*');
        }

        return response.data;
      }

      throw new Error(response.error || 'Failed to check order status');
    } catch (error) {
      console.error('Error checking order status:', error);
      throw error;
    }
  }

  /**
   * Отримати статистику замовлень
   */
  static async getOrderStatistics() {
    try {
      const cacheKey = 'orders:statistics';

      // Перевіряємо кеш
      const cached = ordersCache.get(cacheKey);
      if (cached) {
        return cached;
      }

      const response = await apiClient.get('/orders/statistics');

      if (response.success) {
        // Кешуємо на 5 хвилин
        ordersCache.set(cacheKey, response.data, 300000);
        return response.data;
      }

      throw new Error(response.error || 'Failed to fetch statistics');
    } catch (error) {
      console.error('Error fetching order statistics:', error);
      throw error;
    }
  }

  /**
   * Масове оновлення статусів замовлень
   */
  static async bulkUpdateStatus(orderIds) {
    try {
      const promises = orderIds.map(id => this.checkOrderStatus(id));
      const results = await Promise.allSettled(promises);

      const updated = results.filter(r => r.status === 'fulfilled' && r.value.updated).length;

      if (updated > 0) {
        // Інвалідуємо кеш якщо були оновлення
        ordersCache.invalidatePattern('orders:*');
      }

      return {
        total: orderIds.length,
        updated,
        failed: results.filter(r => r.status === 'rejected').length
      };
    } catch (error) {
      console.error('Error bulk updating statuses:', error);
      throw error;
    }
  }

  /**
   * Отримати історію замовлень з пагінацією
   */
  static async getOrderHistory(page = 1, limit = 20) {
    try {
      const response = await apiClient.get('/orders/history', {
        page,
        limit,
        include_service: true
      });

      if (response.success) {
        return response.data;
      }

      throw new Error(response.error || 'Failed to fetch order history');
    } catch (error) {
      console.error('Error fetching order history:', error);
      throw error;
    }
  }

  /**
   * Експорт замовлень
   */
  static async exportOrders(format = 'csv', filters = {}) {
    try {
      const response = await apiClient.get('/orders/export', {
        format,
        ...filters
      });

      if (response.success) {
        // Завантажуємо файл
        const blob = new Blob([response.data], {
          type: format === 'csv' ? 'text/csv' : 'application/pdf'
        });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `orders_${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        return true;
      }

      throw new Error(response.error || 'Failed to export orders');
    } catch (error) {
      console.error('Error exporting orders:', error);
      throw error;
    }
  }
}

// Експортуємо хелпер функції для швидкого доступу
export const ordersAPI = {
  list: (params) => OrdersAPI.getOrders(params),
  get: (id) => OrdersAPI.getOrderDetails(id),
  create: (data) => OrdersAPI.createOrder(data),
  cancel: (id) => OrdersAPI.cancelOrder(id),
  refill: (id) => OrdersAPI.requestRefill(id),
  repeat: (id) => OrdersAPI.repeatOrder(id),
  checkStatus: (id) => OrdersAPI.checkOrderStatus(id),
  statistics: () => OrdersAPI.getOrderStatistics(),
  bulkStatus: (ids) => OrdersAPI.bulkUpdateStatus(ids),
  history: (page, limit) => OrdersAPI.getOrderHistory(page, limit),
  export: (format, filters) => OrdersAPI.exportOrders(format, filters)
};

export default OrdersAPI;