// frontend/pages/home/services/ApiHome.js
/**
 * API сервіс для домашньої сторінки
 * Всі запити для HOME компонентів
 */

import { apiClient } from '/frontend/shared/services/APIClient.js';

// Переконуємося що використовуємо HTTPS
if (apiClient.baseURL.startsWith('http://')) {
    apiClient.baseURL = apiClient.baseURL.replace('http://', 'https://');
    console.log('ApiHome: Forced HTTPS for apiClient');
}

/**
 * API для користувача (баланс)
 */
export const UserAPI = {
  /**
   * Отримати інформацію про користувача з балансом
   */
  async getMe() {
    return apiClient.get('/auth/me');
  },

  /**
   * Отримати тільки баланс
   */
  async getBalance() {
    try {
      const response = await apiClient.get('/users/balance');
      return response;
    } catch (error) {
      // Якщо /users/balance не працює, беремо з /auth/me
      console.warn('Using /auth/me for balance');
      const response = await apiClient.get('/auth/me');
      if (response.success && response.data?.user) {
        return {
          success: true,
          data: {
            balance: response.data.user.balance || 0,
            currency: 'USD'
          }
        };
      }
      throw error;
    }
  }
};

/**
 * API для сервісів
 */
export const ServicesAPI = {
  /**
   * Отримати популярні сервіси для головної
   */
  async getPopular(limit = 6) {
    return apiClient.get('/services', {
      category: 'telegram',
      active: true,
      limit: limit
    });
  },

  /**
   * Отримати всі сервіси
   */
  async getAll(params = {}) {
    return apiClient.get('/services', params);
  },

  /**
   * Отримати категорії
   */
  async getCategories() {
    return apiClient.get('/services/categories');
  }
};

/**
 * API для замовлень
 */
export const OrdersAPI = {
  /**
   * Отримати останні замовлення для головної
   */
  async getRecent(limit = 5) {
    return apiClient.get('/orders', {
      limit: limit,
      page: 1
    });
  },

  /**
   * Отримати всі замовлення
   */
  async getAll(params = {}) {
    return apiClient.get('/orders', params);
  },

  /**
   * Перевірити статус замовлення
   */
  async checkStatus(orderId) {
    return apiClient.get(`/orders/${orderId}/status`);
  }
};

/**
 * API для статистики
 */
export const StatsAPI = {
  /**
   * Отримати live статистику
   */
  async getLive() {
    return apiClient.get('/statistics/live');
  }
};

/**
 * Комбіновані методи для головної сторінки
 */
export const HomeAPI = {
  /**
   * Завантажити всі дані для головної сторінки
   */
  async loadHomeData() {
    try {
      // Паралельно завантажуємо всі дані
      const [userData, servicesData, ordersData, statsData] = await Promise.allSettled([
        UserAPI.getMe(),
        ServicesAPI.getPopular(),
        OrdersAPI.getRecent(),
        StatsAPI.getLive()
      ]);

      return {
        user: userData.status === 'fulfilled' ? userData.value : null,
        services: servicesData.status === 'fulfilled' ? servicesData.value : null,
        orders: ordersData.status === 'fulfilled' ? ordersData.value : null,
        stats: statsData.status === 'fulfilled' ? statsData.value : null
      };
    } catch (error) {
      console.error('Error loading home data:', error);
      throw error;
    }
  },

  /**
   * Оновити тільки баланс
   */
  async refreshBalance() {
    return UserAPI.getBalance();
  },

  /**
   * Оновити тільки замовлення
   */
  async refreshOrders() {
    return OrdersAPI.getRecent();
  },

  /**
   * Оновити тільки статистику
   */
  async refreshStats() {
    return StatsAPI.getLive();
  }
};

// Експортуємо за замовчуванням HomeAPI
export default HomeAPI;