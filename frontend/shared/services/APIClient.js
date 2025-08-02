// frontend/shared/services/APIClient.js
/**
 * Базовий API клієнт для взаємодії з backend
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
      const auth = JSON.parse(localStorage.getItem('auth') || '{}');
      this.token = auth.access_token;
      this.refreshToken = auth.refresh_token;
    } catch (e) {
      console.error('Failed to load tokens:', e);
    }
  }

  /**
   * Зберегти токени
   */
  saveTokens(tokens) {
    try {
      localStorage.setItem('auth', JSON.stringify(tokens));
      this.token = tokens.access_token;
      this.refreshToken = tokens.refresh_token;
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
      if (response.status === 401 && this.refreshToken && !options.skipAuth) {
        await this.refreshAccessToken();
        // Повторюємо запит з новим токеном
        config.headers.Authorization = `Bearer ${this.token}`;
        const retryResponse = await fetch(url, config);
        return this.handleResponse(retryResponse);
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
    const data = await response.json();

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
    if (error.status === 401) {
      this.clearTokens();
      window.dispatchEvent(new CustomEvent('auth:logout'));
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
      if (response.success) {
        this.token = response.data.access_token;
        const auth = JSON.parse(localStorage.getItem('auth') || '{}');
        auth.access_token = this.token;
        localStorage.setItem('auth', JSON.stringify(auth));
      }
      return response;
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
    if (response.success) {
      apiClient.saveTokens(response.data.tokens);
      window.dispatchEvent(new CustomEvent('auth:login', { detail: response.data }));
    }
    return response;
  },

  async logout() {
    try {
      await apiClient.post('/auth/logout');
    } catch (e) {
      // Ігноруємо помилки при logout
    }
    apiClient.clearTokens();
    window.dispatchEvent(new CustomEvent('auth:logout'));
  },

  async getMe() {
    return apiClient.get('/auth/me');
  },

  async updateProfile(data) {
    return apiClient.put('/auth/me', data);
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

  async getMethods() {
    return apiClient.get('/payments/methods');
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
  }
};

// Statistics API (public)
export const StatsAPI = {
  async getLive() {
    return apiClient.get('/statistics/live');
  }
};

export default apiClient;