// frontend/shared/services/APIClient.js
/**
 * Базовий API клієнт для взаємодії з backend
 * Виправлена версія з правильною обробкою токенів
 */
export class APIClient {
  constructor() {
    this.baseURL = window.CONFIG?.API_URL || 'https://teleboost-teleboost.up.railway.app/api';
    this.token = null;
    this.refreshToken = null;
    this.isRefreshing = false;
    this.refreshPromise = null;

    // Завантажуємо токени з localStorage
    this.loadTokens();
  }

  /**
   * Завантажити токени з localStorage
   */
  loadTokens() {
    try {
      // Читаємо з правильного ключа
      const auth = JSON.parse(localStorage.getItem('auth') || '{}');
      this.token = auth.access_token || null;
      this.refreshToken = auth.refresh_token || null;

      // Перевіряємо чи токен не прострочений
      if (auth.expires_at) {
        const expiresAt = new Date(auth.expires_at);
        if (expiresAt <= new Date()) {
          console.log('Token expired, clearing auth');
          this.clearTokens();
        }
      }
    } catch (e) {
      console.error('Failed to load tokens:', e);
      // Очищаємо якщо не можемо прочитати
      this.clearTokens();
    }
  }

  /**
   * Зберегти токени
   */
  saveTokens(tokens) {
    try {
      // Отримуємо існуючі дані
      const existingAuth = JSON.parse(localStorage.getItem('auth') || '{}');

      // Оновлюємо токени
      const authData = {
        ...existingAuth,
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token || existingAuth.refresh_token,
        expires_at: tokens.expires_in
          ? new Date(Date.now() + tokens.expires_in * 1000).toISOString()
          : existingAuth.expires_at
      };

      localStorage.setItem('auth', JSON.stringify(authData));
      this.token = authData.access_token;
      this.refreshToken = authData.refresh_token;
    } catch (e) {
      console.error('Failed to save tokens:', e);
    }
  }

  /**
   * Очистити токени
   */
  clearTokens() {
    localStorage.removeItem('auth');
    this.token = null;
    this.refreshToken = null;
  }

  /**
   * Базовий метод для запитів
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;

    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      }
    };

    // Додаємо токен якщо є
    if (this.token && !options.skipAuth) {
      config.headers.Authorization = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, config);

      // Якщо 401 - пробуємо оновити токен
      if (response.status === 401 && this.refreshToken && !options.skipAuth && !options.isRetry) {
        await this.refreshAccessToken();

        // Повторюємо запит з новим токеном
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`;
          const retryResponse = await fetch(url, { ...config, isRetry: true });
          return this.handleResponse(retryResponse);
        }
      }

      return this.handleResponse(response);
    } catch (error) {
      this.handleError(error);
    }
  }

  /**
   * Обробка відповіді
   */
  async handleResponse(response) {
    let data;

    try {
      data = await response.json();
    } catch (e) {
      // Якщо не можемо розпарсити JSON
      if (!response.ok) {
        throw {
          status: response.status,
          message: 'Request failed',
          code: 'PARSE_ERROR'
        };
      }
      data = {};
    }

    if (!response.ok) {
      throw {
        status: response.status,
        message: data.error || 'Request failed',
        code: data.code || 'UNKNOWN_ERROR',
        data
      };
    }

    return data;
  }

  /**
   * Обробка помилок
   */
  handleError(error) {
    console.error('API Error:', error);

    // Якщо втратили авторизацію
    if (error.status === 401 || error.code === 'UNAUTHORIZED') {
      this.clearTokens();
      window.dispatchEvent(new CustomEvent('auth:logout'));
      // Редірект на сторінку логіну
      window.location.href = '/login';
    }

    throw error;
  }

  /**
   * Оновити access token
   */
  async refreshAccessToken() {
    // Якщо вже оновлюємо - чекаємо
    if (this.isRefreshing) {
      return this.refreshPromise;
    }

    this.isRefreshing = true;

    this.refreshPromise = this.request('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: this.refreshToken }),
      skipAuth: true
    }).then(response => {
      if (response.success && response.data) {
        this.saveTokens(response.data);
      } else {
        // Не вдалось оновити - очищаємо токени
        this.clearTokens();
        throw new Error('Failed to refresh token');
      }
      return response;
    }).catch(error => {
      // При помилці оновлення - logout і редірект
      this.clearTokens();
      window.dispatchEvent(new CustomEvent('auth:logout'));
      window.location.href = '/login';
      throw error;
    }).finally(() => {
      this.isRefreshing = false;
      this.refreshPromise = null;
    });

    return this.refreshPromise;
  }

  // HTTP методи
  async get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;
    return this.request(url, { method: 'GET' });
  }

  async post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async put(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }

  async patch(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  }
}

// Singleton instance
export const apiClient = new APIClient();

// Auth методи
export const AuthAPI = {
  async loginWithTelegram(initData) {
    const response = await apiClient.post('/auth/telegram', { initData });
    if (response.success && response.data) {
      // Зберігаємо всі дані авторизації
      const authData = {
        access_token: response.data.tokens.access_token,
        refresh_token: response.data.tokens.refresh_token,
        user: response.data.user,
        expires_at: new Date(Date.now() + (response.data.tokens.expires_in || 86400) * 1000).toISOString()
      };

      localStorage.setItem('auth', JSON.stringify(authData));
      apiClient.loadTokens(); // Перезавантажуємо токени

      window.dispatchEvent(new CustomEvent('auth:login', { detail: response.data }));
    }
    return response;
  },

  async logout() {
    try {
      await apiClient.post('/auth/logout');
    } catch (e) {
      // Ігноруємо помилки при logout
      console.log('Logout error (ignored):', e);
    }
    apiClient.clearTokens();
    window.dispatchEvent(new CustomEvent('auth:logout'));
    // Редірект на логін
    window.location.href = '/login';
  },

  async getMe() {
    return apiClient.get('/auth/me');
  },

  async updateProfile(data) {
    return apiClient.put('/auth/me', data);
  },

  async verify() {
    return apiClient.get('/auth/verify');
  }
};

// Services API
export const ServicesAPI = {
  async getAll(params = {}) {
    return apiClient.get('/services', params);
  },

  async getById(id) {
    return apiClient.get(`/services/${id}`);
  },

  async getCategories() {
    return apiClient.get('/services/categories');
  },

  async calculatePrice(data) {
    return apiClient.post('/services/calculate-price', data);
  }
};

// Orders API
export const OrdersAPI = {
  async create(data) {
    return apiClient.post('/orders', data);
  },

  async getAll(params = {}) {
    return apiClient.get('/orders', params);
  },

  async getById(id) {
    return apiClient.get(`/orders/${id}`);
  },

  async checkStatus(id) {
    return apiClient.get(`/orders/${id}/status`);
  },

  async cancel(id) {
    return apiClient.post(`/orders/${id}/cancel`);
  },

  async refill(id) {
    return apiClient.post(`/orders/${id}/refill`);
  },

  async calculatePrice(data) {
    return apiClient.post('/orders/calculate-price', data);
  },

  async getStatistics() {
    return apiClient.get('/orders/statistics');
  }
};

// Payments API
export const PaymentsAPI = {
  async create(data) {
    return apiClient.post('/payments/create', data);
  },

  async getById(id) {
    return apiClient.get(`/payments/${id}`);
  },

  async check(id) {
    return apiClient.post(`/payments/${id}/check`);
  },

  async getAll(params = {}) {
    return apiClient.get('/payments', params);
  },

  async getMethods() {
    return apiClient.get('/payments/methods');
  },

  async getLimits() {
    return apiClient.get('/payments/limits');
  },

  async calculate(data) {
    return apiClient.post('/payments/calculate', data);
  }
};

// Users API
export const UsersAPI = {
  async getProfile() {
    return apiClient.get('/users/profile');
  },

  async getBalance() {
    return apiClient.get('/users/balance');
  },

  async getTransactions(params = {}) {
    return apiClient.get('/users/transactions', params);
  },

  async exportTransactions(params = {}) {
    return apiClient.get('/users/transactions/export', params);
  },

  async getStatistics() {
    return apiClient.get('/users/statistics');
  },

  async createWithdrawal(data) {
    return apiClient.post('/users/withdraw', data);
  },

  async getSettings() {
    return apiClient.get('/users/settings');
  },

  async updateSettings(data) {
    return apiClient.put('/users/settings', data);
  },

  async getNotifications(params = {}) {
    return apiClient.get('/users/notifications', params);
  },

  async markNotificationRead(id) {
    return apiClient.post(`/users/notifications/${id}/read`);
  },

  async getActivity() {
    return apiClient.get('/users/activity');
  }
};

// Referrals API
export const ReferralsAPI = {
  async getStats() {
    return apiClient.get('/referrals/stats');
  },

  async getLink() {
    return apiClient.get('/referrals/link');
  },

  async getList(params = {}) {
    return apiClient.get('/referrals/list', params);
  },

  async getTree() {
    return apiClient.get('/referrals/tree');
  },

  async getEarnings(period = 'all') {
    return apiClient.get('/referrals/earnings', { period });
  },

  async getPromoMaterials() {
    return apiClient.get('/referrals/promo-materials');
  }
};

// Statistics API (public)
export const StatsAPI = {
  async getLive() {
    return apiClient.get('/statistics/live');
  }
};

// Обробники глобальних подій
window.addEventListener('auth:logout', () => {
  // Очищаємо всі дані і редіректимо на логін
  apiClient.clearTokens();
  window.location.href = '/login';
});

export default apiClient;