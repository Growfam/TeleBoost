// frontend/shared/services/APIClient.js
/**
 * Базовий API клієнт для взаємодії з backend
 * Містить тільки базову логіку та аутентифікацію
 */

export class APIClient {
  constructor() {
    // ЗАВЖДИ використовуємо HTTPS для Railway!
    let configUrl = window.CONFIG?.API_URL || 'https://teleboost-teleboost.up.railway.app/api';

    // Примусово змінюємо HTTP на HTTPS
    if (configUrl.startsWith('http://')) {
      configUrl = configUrl.replace('http://', 'https://');
    }

    this.baseURL = configUrl;
    console.log('APIClient initialized with HTTPS:', this.baseURL);

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
      this.token = auth.access_token || null;
      this.refreshToken = auth.refresh_token || null;

      // Перевіряємо термін дії
      if (auth.expires_at) {
        const expiresAt = new Date(auth.expires_at);
        if (expiresAt <= new Date()) {
          this.clearTokens();
        }
      }
    } catch (e) {
      this.clearTokens();
    }
  }

  /**
   * Зберегти токени
   */
  saveTokens(tokens) {
    try {
      const existingAuth = JSON.parse(localStorage.getItem('auth') || '{}');

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
      // Ignore
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
    // Перезавантажуємо токени перед запитом
    if (!options.skipAuth) {
      this.loadTokens();
    }

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
          return this.request(endpoint, { ...options, isRetry: true });
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
      const responseText = await response.text();
      data = JSON.parse(responseText);
    } catch (e) {
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
    // Якщо втратили авторизацію
    if (error.status === 401 || error.code === 'UNAUTHORIZED') {
      this.clearTokens();
      window.dispatchEvent(new CustomEvent('auth:logout'));
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
        this.clearTokens();
        throw new Error('Failed to refresh token');
      }
      return response;
    }).catch(error => {
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

    // ДІАГНОСТИКА
    console.log('APIClient GET request to:', `${this.baseURL}${url}`);

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

// Singleton instance з примусовим HTTPS
export const apiClient = new APIClient();

// Додатково переконуємося що глобальний apiClient також використовує HTTPS
if (typeof window !== 'undefined') {
  window.apiClient = apiClient;
}

/**
 * Auth API - єдиний API в цьому файлі
 */
export const AuthAPI = {
  /**
   * Авторизація через Telegram
   */
  async loginWithTelegram(initData) {
    const response = await apiClient.post('/auth/telegram', { initData });

    if (response.success && response.data) {
      const authData = {
        access_token: response.data.tokens.access_token,
        refresh_token: response.data.tokens.refresh_token,
        user: response.data.user,
        expires_at: new Date(Date.now() + (response.data.tokens.expires_in || 86400) * 1000).toISOString()
      };

      localStorage.setItem('auth', JSON.stringify(authData));
      apiClient.loadTokens();
      window.dispatchEvent(new CustomEvent('auth:login', { detail: response.data }));
    }

    return response;
  },

  /**
   * Вихід
   */
  async logout() {
    try {
      await apiClient.post('/auth/logout');
    } catch (e) {
      // Ignore
    }
    apiClient.clearTokens();
    window.dispatchEvent(new CustomEvent('auth:logout'));
    window.location.href = '/login';
  },

  /**
   * Отримати поточного користувача
   */
  async getMe() {
    return apiClient.get('/auth/me');
  },

  /**
   * Оновити профіль
   */
  async updateProfile(data) {
    return apiClient.put('/auth/me', data);
  },

  /**
   * Верифікувати токен
   */
  async verify() {
    return apiClient.get('/auth/verify');
  },

  /**
   * Оновити токен
   */
  async refresh() {
    return apiClient.refreshAccessToken();
  }
};

// Обробники глобальних подій
window.addEventListener('auth:logout', () => {
  apiClient.clearTokens();
  window.location.href = '/login';
});

export default apiClient;