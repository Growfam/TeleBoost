// frontend/shared/services/APIClient.js
/**
 * Базовий API клієнт для взаємодії з backend
 * ВЕРСИЯ С ПОЛНЫМ ЛОГИРОВАНИЕМ ДЛЯ ДИАГНОСТИКИ
 */

export class APIClient {
  constructor() {
    console.log('🟩 APIClient: Constructor called');

    this.baseURL = window.CONFIG?.API_URL || 'https://teleboost-teleboost.up.railway.app/api';
    this.token = null;
    this.refreshToken = null;
    this.isRefreshing = false;
    this.refreshPromise = null;
    this.requestCount = 0;

    console.log('🟩 APIClient: Base URL set to:', this.baseURL);

    // Завантажуємо токени з localStorage
    this.loadTokens();

    console.log('🟩 APIClient: Constructor completed', {
      hasToken: !!this.token,
      hasRefreshToken: !!this.refreshToken,
      tokenPreview: this.token ? this.token.substring(0, 20) + '...' : 'null'
    });
  }

  /**
   * Завантажити токени з localStorage
   */
  loadTokens() {
    console.log('🟩 APIClient: loadTokens() called');

    try {
      // Перевіряємо що є в localStorage
      const authRaw = localStorage.getItem('auth');
      console.log('🟩 APIClient: localStorage.getItem("auth") result:', {
        exists: !!authRaw,
        length: authRaw?.length || 0,
        preview: authRaw ? authRaw.substring(0, 100) + '...' : 'null'
      });

      if (!authRaw) {
        console.log('🟩 APIClient: No auth data in localStorage');
        return;
      }

      // Парсимо JSON
      const auth = JSON.parse(authRaw);
      console.log('🟩 APIClient: Parsed auth data:', {
        hasAccessToken: !!auth.access_token,
        hasRefreshToken: !!auth.refresh_token,
        hasUser: !!auth.user,
        hasExpiresAt: !!auth.expires_at,
        accessTokenPreview: auth.access_token ? auth.access_token.substring(0, 20) + '...' : 'null'
      });

      this.token = auth.access_token || null;
      this.refreshToken = auth.refresh_token || null;

      // Перевіряємо чи токен не прострочений
      if (auth.expires_at) {
        const expiresAt = new Date(auth.expires_at);
        const now = new Date();
        const isExpired = expiresAt <= now;

        console.log('🟩 APIClient: Token expiration check:', {
          expiresAt: expiresAt.toISOString(),
          now: now.toISOString(),
          isExpired: isExpired,
          timeLeft: isExpired ? 'EXPIRED' : Math.floor((expiresAt - now) / 1000) + ' seconds'
        });

        if (isExpired) {
          console.log('🟩 APIClient: Token expired, clearing auth');
          this.clearTokens();
        }
      }

      console.log('🟩 APIClient: loadTokens() completed', {
        hasToken: !!this.token,
        hasRefreshToken: !!this.refreshToken
      });

    } catch (e) {
      console.error('🟩 APIClient: ERROR in loadTokens():', e);
      console.log('🟩 APIClient: Clearing tokens due to parse error');
      this.clearTokens();
    }
  }

  /**
   * Зберегти токени
   */
  saveTokens(tokens) {
    console.log('🟩 APIClient: saveTokens() called', {
      hasAccessToken: !!tokens.access_token,
      hasRefreshToken: !!tokens.refresh_token,
      expiresIn: tokens.expires_in
    });

    try {
      // Отримуємо існуючі дані
      const existingAuth = JSON.parse(localStorage.getItem('auth') || '{}');
      console.log('🟩 APIClient: Existing auth data:', {
        hasExistingData: Object.keys(existingAuth).length > 0,
        hasExistingUser: !!existingAuth.user
      });

      // Оновлюємо токени
      const authData = {
        ...existingAuth,
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token || existingAuth.refresh_token,
        expires_at: tokens.expires_in
          ? new Date(Date.now() + tokens.expires_in * 1000).toISOString()
          : existingAuth.expires_at
      };

      console.log('🟩 APIClient: Saving auth data:', {
        hasAccessToken: !!authData.access_token,
        hasRefreshToken: !!authData.refresh_token,
        hasUser: !!authData.user,
        expiresAt: authData.expires_at
      });

      localStorage.setItem('auth', JSON.stringify(authData));

      // Оновлюємо локальні змінні
      this.token = authData.access_token;
      this.refreshToken = authData.refresh_token;

      console.log('🟩 APIClient: Tokens saved and updated in memory');

      // Перевіряємо що збереглось
      const savedAuth = localStorage.getItem('auth');
      console.log('🟩 APIClient: Verification - auth saved correctly:', !!savedAuth);

    } catch (e) {
      console.error('🟩 APIClient: ERROR in saveTokens():', e);
    }
  }

  /**
   * Очистити токени
   */
  clearTokens() {
    console.log('🟩 APIClient: clearTokens() called');

    localStorage.removeItem('auth');
    this.token = null;
    this.refreshToken = null;

    console.log('🟩 APIClient: Tokens cleared from memory and localStorage');
  }

  /**
   * Базовий метод для запитів
   */
  async request(endpoint, options = {}) {
    this.requestCount++;
    const requestId = `REQ-${this.requestCount}`;

    console.log(`🟩 APIClient: ${requestId} - request() called`, {
      endpoint: endpoint,
      method: options.method || 'GET',
      hasBody: !!options.body,
      skipAuth: !!options.skipAuth,
      isRetry: !!options.isRetry,
      currentToken: this.token ? this.token.substring(0, 20) + '...' : 'null'
    });

    const url = `${this.baseURL}${endpoint}`;
    console.log(`🟩 APIClient: ${requestId} - Full URL:`, url);

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
      console.log(`🟩 APIClient: ${requestId} - Added Authorization header:`, {
        headerValue: config.headers.Authorization.substring(0, 30) + '...'
      });
    } else {
      console.log(`🟩 APIClient: ${requestId} - No Authorization header:`, {
        hasToken: !!this.token,
        skipAuth: !!options.skipAuth,
        reason: !this.token ? 'No token' : 'skipAuth is true'
      });
    }

    console.log(`🟩 APIClient: ${requestId} - Final request config:`, {
      method: config.method,
      headers: Object.keys(config.headers).reduce((acc, key) => {
        acc[key] = key === 'Authorization'
          ? (config.headers[key] ? config.headers[key].substring(0, 30) + '...' : 'null')
          : config.headers[key];
        return acc;
      }, {}),
      bodyLength: config.body ? config.body.length : 0
    });

    try {
      console.log(`🟩 APIClient: ${requestId} - Sending fetch request...`);
      const response = await fetch(url, config);

      console.log(`🟩 APIClient: ${requestId} - Response received:`, {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        headers: Object.fromEntries(response.headers.entries())
      });

      // Якщо 401 - пробуємо оновити токен
      if (response.status === 401 && this.refreshToken && !options.skipAuth && !options.isRetry) {
        console.log(`🟩 APIClient: ${requestId} - Got 401, attempting token refresh`);

        await this.refreshAccessToken();

        // Повторюємо запит з новим токеном
        if (this.token) {
          console.log(`🟩 APIClient: ${requestId} - Retrying with new token`);
          config.headers.Authorization = `Bearer ${this.token}`;
          const retryResponse = await fetch(url, { ...config, isRetry: true });
          return this.handleResponse(retryResponse, requestId);
        } else {
          console.log(`🟩 APIClient: ${requestId} - No token after refresh, giving up`);
        }
      }

      return this.handleResponse(response, requestId);
    } catch (error) {
      console.error(`🟩 APIClient: ${requestId} - Network error:`, error);
      this.handleError(error, requestId);
    }
  }

  /**
   * Обробка відповіді
   */
  async handleResponse(response, requestId = '') {
    console.log(`🟩 APIClient: ${requestId} - handleResponse() called:`, {
      status: response.status,
      ok: response.ok
    });

    let data;
    let responseText;

    try {
      responseText = await response.text();
      console.log(`🟩 APIClient: ${requestId} - Response text received:`, {
        length: responseText.length,
        preview: responseText.substring(0, 200)
      });

      data = JSON.parse(responseText);
      console.log(`🟩 APIClient: ${requestId} - Response parsed as JSON:`, {
        success: data.success,
        hasData: !!data.data,
        hasError: !!data.error,
        errorCode: data.code
      });

    } catch (e) {
      console.error(`🟩 APIClient: ${requestId} - Failed to parse JSON:`, e);
      console.log(`🟩 APIClient: ${requestId} - Raw response text:`, responseText);

      if (!response.ok) {
        throw {
          status: response.status,
          message: 'Request failed',
          code: 'PARSE_ERROR',
          rawResponse: responseText
        };
      }
      data = {};
    }

    if (!response.ok) {
      console.log(`🟩 APIClient: ${requestId} - Response not OK, throwing error`);
      throw {
        status: response.status,
        message: data.error || 'Request failed',
        code: data.code || 'UNKNOWN_ERROR',
        data
      };
    }

    console.log(`🟩 APIClient: ${requestId} - Response handled successfully`);
    return data;
  }

  /**
   * Обробка помилок
   */
  handleError(error, requestId = '') {
    console.error(`🟩 APIClient: ${requestId} - handleError() called:`, {
      status: error.status,
      message: error.message,
      code: error.code,
      fullError: error
    });

    // Якщо втратили авторизацію
    if (error.status === 401 || error.code === 'UNAUTHORIZED') {
      console.log(`🟩 APIClient: ${requestId} - Unauthorized error, clearing tokens and redirecting`);
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
    console.log('🟩 APIClient: refreshAccessToken() called', {
      isRefreshing: this.isRefreshing,
      hasRefreshToken: !!this.refreshToken
    });

    // Якщо вже оновлюємо - чекаємо
    if (this.isRefreshing) {
      console.log('🟩 APIClient: Already refreshing, waiting for promise');
      return this.refreshPromise;
    }

    this.isRefreshing = true;

    this.refreshPromise = this.request('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: this.refreshToken }),
      skipAuth: true
    }).then(response => {
      console.log('🟩 APIClient: Refresh response received:', {
        success: response.success,
        hasData: !!response.data,
        hasAccessToken: !!response.data?.access_token
      });

      if (response.success && response.data) {
        this.saveTokens(response.data);
        console.log('🟩 APIClient: New tokens saved after refresh');
      } else {
        console.log('🟩 APIClient: Refresh failed, clearing tokens');
        this.clearTokens();
        throw new Error('Failed to refresh token');
      }
      return response;
    }).catch(error => {
      console.error('🟩 APIClient: Error during token refresh:', error);
      // При помилці оновлення - logout і редірект
      this.clearTokens();
      window.dispatchEvent(new CustomEvent('auth:logout'));
      window.location.href = '/login';
      throw error;
    }).finally(() => {
      console.log('🟩 APIClient: Refresh process completed');
      this.isRefreshing = false;
      this.refreshPromise = null;
    });

    return this.refreshPromise;
  }

  // HTTP методи
  async get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;
    console.log('🟩 APIClient: GET request:', url);
    return this.request(url, { method: 'GET' });
  }

  async post(endpoint, data = {}) {
    console.log('🟩 APIClient: POST request:', endpoint, {
      dataKeys: Object.keys(data),
      dataSize: JSON.stringify(data).length
    });
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async put(endpoint, data = {}) {
    console.log('🟩 APIClient: PUT request:', endpoint);
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  async delete(endpoint) {
    console.log('🟩 APIClient: DELETE request:', endpoint);
    return this.request(endpoint, { method: 'DELETE' });
  }

  async patch(endpoint, data = {}) {
    console.log('🟩 APIClient: PATCH request:', endpoint);
    return this.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  }
}

// Singleton instance
console.log('🟩 APIClient: Creating singleton instance');
export const apiClient = new APIClient();

// Auth методи
export const AuthAPI = {
  async loginWithTelegram(initData) {
    console.log('🟩 AuthAPI: loginWithTelegram() called');

    const response = await apiClient.post('/auth/telegram', { initData });

    console.log('🟩 AuthAPI: Login response:', {
      success: response.success,
      hasData: !!response.data,
      hasTokens: !!response.data?.tokens,
      hasUser: !!response.data?.user
    });

    if (response.success && response.data) {
      // Зберігаємо всі дані авторизації
      const authData = {
        access_token: response.data.tokens.access_token,
        refresh_token: response.data.tokens.refresh_token,
        user: response.data.user,
        expires_at: new Date(Date.now() + (response.data.tokens.expires_in || 86400) * 1000).toISOString()
      };

      console.log('🟩 AuthAPI: Saving auth data to localStorage');
      localStorage.setItem('auth', JSON.stringify(authData));

      console.log('🟩 AuthAPI: Reloading tokens in APIClient');
      apiClient.loadTokens(); // Перезавантажуємо токени

      console.log('🟩 AuthAPI: Dispatching auth:login event');
      window.dispatchEvent(new CustomEvent('auth:login', { detail: response.data }));
    }

    return response;
  },

  async logout() {
    console.log('🟩 AuthAPI: logout() called');
    try {
      await apiClient.post('/auth/logout');
    } catch (e) {
      console.log('🟩 AuthAPI: Logout error (ignored):', e);
    }
    apiClient.clearTokens();
    window.dispatchEvent(new CustomEvent('auth:logout'));
    window.location.href = '/login';
  },

  async getMe() {
    console.log('🟩 AuthAPI: getMe() called');
    return apiClient.get('/auth/me');
  },

  async updateProfile(data) {
    console.log('🟩 AuthAPI: updateProfile() called');
    return apiClient.put('/auth/me', data);
  },

  async verify() {
    console.log('🟩 AuthAPI: verify() called');
    return apiClient.get('/auth/verify');
  }
};

// Services API
export const ServicesAPI = {
  async getAll(params = {}) {
    console.log('🟩 ServicesAPI: getAll() called', params);
    return apiClient.get('/services', params);
  },

  async getById(id) {
    console.log('🟩 ServicesAPI: getById() called', id);
    return apiClient.get(`/services/${id}`);
  },

  async getCategories() {
    console.log('🟩 ServicesAPI: getCategories() called');
    return apiClient.get('/services/categories');
  },

  async calculatePrice(data) {
    console.log('🟩 ServicesAPI: calculatePrice() called', data);
    return apiClient.post('/services/calculate-price', data);
  }
};

// Orders API
export const OrdersAPI = {
  async create(data) {
    console.log('🟩 OrdersAPI: create() called', data);
    return apiClient.post('/orders', data);
  },

  async getAll(params = {}) {
    console.log('🟩 OrdersAPI: getAll() called', params);
    return apiClient.get('/orders', params);
  },

  async getById(id) {
    console.log('🟩 OrdersAPI: getById() called', id);
    return apiClient.get(`/orders/${id}`);
  },

  async checkStatus(id) {
    console.log('🟩 OrdersAPI: checkStatus() called', id);
    return apiClient.get(`/orders/${id}/status`);
  },

  async cancel(id) {
    console.log('🟩 OrdersAPI: cancel() called', id);
    return apiClient.post(`/orders/${id}/cancel`);
  },

  async refill(id) {
    console.log('🟩 OrdersAPI: refill() called', id);
    return apiClient.post(`/orders/${id}/refill`);
  },

  async calculatePrice(data) {
    console.log('🟩 OrdersAPI: calculatePrice() called', data);
    return apiClient.post('/orders/calculate-price', data);
  },

  async getStatistics() {
    console.log('🟩 OrdersAPI: getStatistics() called');
    return apiClient.get('/orders/statistics');
  }
};

// Payments API
export const PaymentsAPI = {
  async create(data) {
    console.log('🟩 PaymentsAPI: create() called', data);
    return apiClient.post('/payments/create', data);
  },

  async getById(id) {
    console.log('🟩 PaymentsAPI: getById() called', id);
    return apiClient.get(`/payments/${id}`);
  },

  async check(id) {
    console.log('🟩 PaymentsAPI: check() called', id);
    return apiClient.post(`/payments/${id}/check`);
  },

  async getAll(params = {}) {
    console.log('🟩 PaymentsAPI: getAll() called', params);
    return apiClient.get('/payments', params);
  },

  async getMethods() {
    console.log('🟩 PaymentsAPI: getMethods() called');
    return apiClient.get('/payments/methods');
  },

  async getLimits() {
    console.log('🟩 PaymentsAPI: getLimits() called');
    return apiClient.get('/payments/limits');
  },

  async calculate(data) {
    console.log('🟩 PaymentsAPI: calculate() called', data);
    return apiClient.post('/payments/calculate', data);
  }
};

// Users API
export const UsersAPI = {
  async getProfile() {
    console.log('🟩 UsersAPI: getProfile() called');
    return apiClient.get('/users/profile');
  },

  async getBalance() {
    console.log('🟩 UsersAPI: getBalance() called');
    return apiClient.get('/users/balance');
  },

  async getTransactions(params = {}) {
    console.log('🟩 UsersAPI: getTransactions() called', params);
    return apiClient.get('/users/transactions', params);
  },

  async exportTransactions(params = {}) {
    console.log('🟩 UsersAPI: exportTransactions() called', params);
    return apiClient.get('/users/transactions/export', params);
  },

  async getStatistics() {
    console.log('🟩 UsersAPI: getStatistics() called');
    return apiClient.get('/users/statistics');
  },

  async createWithdrawal(data) {
    console.log('🟩 UsersAPI: createWithdrawal() called', data);
    return apiClient.post('/users/withdraw', data);
  },

  async getSettings() {
    console.log('🟩 UsersAPI: getSettings() called');
    return apiClient.get('/users/settings');
  },

  async updateSettings(data) {
    console.log('🟩 UsersAPI: updateSettings() called', data);
    return apiClient.put('/users/settings', data);
  },

  async getNotifications(params = {}) {
    console.log('🟩 UsersAPI: getNotifications() called', params);
    return apiClient.get('/users/notifications', params);
  },

  async markNotificationRead(id) {
    console.log('🟩 UsersAPI: markNotificationRead() called', id);
    return apiClient.post(`/users/notifications/${id}/read`);
  },

  async getActivity() {
    console.log('🟩 UsersAPI: getActivity() called');
    return apiClient.get('/users/activity');
  }
};

// Referrals API
export const ReferralsAPI = {
  async getStats() {
    console.log('🟩 ReferralsAPI: getStats() called');
    return apiClient.get('/referrals/stats');
  },

  async getLink() {
    console.log('🟩 ReferralsAPI: getLink() called');
    return apiClient.get('/referrals/link');
  },

  async getList(params = {}) {
    console.log('🟩 ReferralsAPI: getList() called', params);
    return apiClient.get('/referrals/list', params);
  },

  async getTree() {
    console.log('🟩 ReferralsAPI: getTree() called');
    return apiClient.get('/referrals/tree');
  },

  async getEarnings(period = 'all') {
    console.log('🟩 ReferralsAPI: getEarnings() called', period);
    return apiClient.get('/referrals/earnings', { period });
  },

  async getPromoMaterials() {
    console.log('🟩 ReferralsAPI: getPromoMaterials() called');
    return apiClient.get('/referrals/promo-materials');
  }
};

// Statistics API (public)
export const StatsAPI = {
  async getLive() {
    console.log('🟩 StatsAPI: getLive() called');
    return apiClient.get('/statistics/live');
  }
};

// Обробники глобальних подій
window.addEventListener('auth:logout', () => {
  console.log('🟩 APIClient: Global auth:logout event received');
  apiClient.clearTokens();
  window.location.href = '/login';
});

console.log('🟩 APIClient: Module initialization completed');

// Додаємо в window для дебагу
if (window.CONFIG?.DEBUG) {
  window.apiClient = apiClient;
  window.AuthAPI = AuthAPI;
  console.log('🟩 APIClient: Debug mode - apiClient and AuthAPI exposed to window');
}

export default apiClient;