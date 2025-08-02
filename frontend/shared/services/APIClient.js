// frontend/shared/services/APIClient.js
/**
 * Базовий API клієнт для взаємодії з backend
 * ВИПРАВЛЕНО: Узгоджено читання токенів з TelegramAuth
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

    // Слухаємо події авторизації
    window.addEventListener('auth:login', (e) => this.handleAuthLogin(e.detail));
    window.addEventListener('auth:logout', () => this.handleAuthLogout());
  }

  /**
   * Завантажити токени з localStorage
   * ВИПРАВЛЕНО: Правильно читаємо формат з TelegramAuth
   */
  loadTokens() {
    try {
      const authData = localStorage.getItem('auth');

      if (!authData) {
        this.clearTokens();
        return;
      }

      const auth = JSON.parse(authData);

      // Перевіряємо термін дії токена
      if (auth.expires_at && new Date(auth.expires_at) < new Date()) {
        console.warn('Token expired, clearing auth data');
        this.clearTokens();
        return;
      }

      this.token = auth.access_token;
      this.refreshToken = auth.refresh_token;

      console.log('Tokens loaded successfully');
    } catch (e) {
      console.error('Failed to load tokens:', e);
      this.clearTokens();
    }
  }

  /**
   * Зберегти токени
   * ВИПРАВЛЕНО: Зберігаємо в тому ж форматі що й TelegramAuth
   */
  saveTokens(tokens, user = null) {
    try {
      const authData = {
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        token_type: tokens.token_type || 'Bearer',
        expires_in: tokens.expires_in,
        expires_at: tokens.expires_at || new Date(Date.now() + (tokens.expires_in || 86400) * 1000).toISOString(),
        user: user || JSON.parse(localStorage.getItem('auth') || '{}').user
      };

      localStorage.setItem('auth', JSON.stringify(authData));
      this.token = tokens.access_token;
      this.refreshToken = tokens.refresh_token;

      console.log('Tokens saved successfully');
    } catch (e) {
      console.error('Failed to save tokens:', e);
    }
  }

  /**
   * Очистити токени
   */
  clearTokens() {
    localStorage.removeItem('auth');
    // Очищаємо старі ключі якщо вони існують
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');

    this.token = null;
    this.refreshToken = null;
  }

  /**
   * Обробка події входу
   */
  handleAuthLogin(authData) {
    if (authData.tokens) {
      this.saveTokens(authData.tokens, authData.user);
    }
  }

  /**
   * Обробка події виходу
   */
  handleAuthLogout() {
    this.clearTokens();
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
      console.log(`API Request: ${options.method || 'GET'} ${endpoint}`);

      const response = await fetch(url, config);

      // Логуємо статус
      console.log(`API Response: ${response.status} ${response.statusText}`);

      // Якщо 401 - пробуємо оновити токен
      if (response.status === 401 && this.refreshToken && !options.skipAuth && !options.isRetry) {
        console.log('Token expired, attempting refresh...');

        const refreshed = await this.refreshAccessToken();

        if (refreshed) {
          // Повторюємо запит з новим токеном
          config.headers.Authorization = `Bearer ${this.token}`;
          const retryResponse = await fetch(url, { ...config, isRetry: true });
          return this.handleResponse(retryResponse);
        }
      }

      return this.handleResponse(response);
    } catch (error) {
      console.error('API Request failed:', error);
      this.handleError(error);
    }
  }

  /**
   * Обробка відповіді
   */
  async handleResponse(response) {
    let data;

    try {
      const text = await response.text();
      data = text ? JSON.parse(text) : {};
    } catch (e) {
      console.error('Failed to parse response:', e);
      data = { error: 'Invalid response format' };
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

      // Не редіректимо якщо вже на сторінці логіну
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }

    throw error;
  }

  /**
   * Оновити access token
   * ВИПРАВЛЕНО: Правильно зберігаємо оновлений токен
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
        // Зберігаємо новий токен
        const currentAuth = JSON.parse(localStorage.getItem('auth') || '{}');

        this.saveTokens({
          access_token: response.data.access_token,
          refresh_token: currentAuth.refresh_token, // Refresh token не змінюється
          token_type: response.data.token_type || 'Bearer',
          expires_in: response.data.expires_in || 86400
        }, currentAuth.user);

        console.log('Token refreshed successfully');
        return true;
      }

      console.error('Failed to refresh token');
      this.clearTokens();
      return false;
    }).catch(error => {
      console.error('Token refresh error:', error);
      this.clearTokens();
      return false;
    }).finally(() => {
      this.isRefreshing = false;
      this.refreshPromise = null;
    });

    return this.refreshPromise;
  }

  /**
   * Перевірити чи авторизований
   */
  isAuthenticated() {
    return !!this.token;
  }

  /**
   * Отримати поточного користувача
   */
  getCurrentUser() {
    try {
      const auth = JSON.parse(localStorage.getItem('auth') || '{}');
      return auth.user || null;
    } catch (e) {
      return null;
    }
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
      // Токени вже збережені в TelegramAuth, тут тільки emit подію
      window.dispatchEvent(new CustomEvent('auth:login', { detail: response.data }));
    }

    return response;
  },

  async logout() {
    try {
      await apiClient.post('/auth/logout');
    } catch (e) {
      // Ігноруємо помилки при logout
      console.error('Logout error:', e);
    }

    apiClient.clearTokens();
    window.dispatchEvent(new CustomEvent('auth:logout'));
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
  },

  async sync() {
    return apiClient.post('/services/sync');
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
  },

  async getLimits() {
    return apiClient.get('/payments/limits');
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
  },

  async getOverview() {
    return apiClient.get('/statistics/overview', {}, { skipAuth: true });
  }
};

// Config API
export const ConfigAPI = {
  async getPublic() {
    return apiClient.get('/config', {}, { skipAuth: true });
  },

  async getStatus() {
    return apiClient.get('/status', {}, { skipAuth: true });
  }
};

export default apiClient;