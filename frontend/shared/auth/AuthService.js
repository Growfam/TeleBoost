// frontend/shared/services/AuthService.js
/**
 * Централізований сервіс авторизації
 * Управляє всією логікою авторизації в додатку
 */

import { apiClient, AuthAPI } from './APIClient.js';
import { userCache } from './CacheService.js';

class AuthService {
  constructor() {
    this.user = null;
    this.isAuthenticated = false;
    this.isInitialized = false;
    this.initPromise = null;

    // Підписуємося на події
    this.setupEventListeners();
  }

  /**
   * Налаштування слухачів подій
   */
  setupEventListeners() {
    // Подія логіну
    window.addEventListener('auth:login', (e) => {
      this.user = e.detail.user;
      this.isAuthenticated = true;
      userCache.set('current_user', this.user, 300000); // 5 хвилин
    });

    // Подія логауту
    window.addEventListener('auth:logout', () => {
      this.user = null;
      this.isAuthenticated = false;
      userCache.clear();
    });
  }

  /**
   * Ініціалізація сервісу
   */
  async init() {
    // Якщо вже ініціалізуємо - повертаємо проміс
    if (this.initPromise) {
      return this.initPromise;
    }

    // Якщо вже ініціалізовано
    if (this.isInitialized) {
      return {
        isAuthenticated: this.isAuthenticated,
        user: this.user
      };
    }

    this.initPromise = this._performInit();
    const result = await this.initPromise;
    this.initPromise = null;

    return result;
  }

  /**
   * Виконати ініціалізацію
   */
  async _performInit() {
    try {
      // Перевіряємо наявність токена
      const authData = this.getStoredAuth();

      if (!authData || !authData.access_token) {
        this.isInitialized = true;
        return {
          isAuthenticated: false,
          user: null
        };
      }

      // Перевіряємо чи не прострочений токен
      if (authData.expires_at) {
        const expiresAt = new Date(authData.expires_at);
        if (expiresAt <= new Date()) {
          console.log('Token expired, clearing auth');
          this.clearAuth();
          this.isInitialized = true;
          return {
            isAuthenticated: false,
            user: null
          };
        }
      }

      // Перевіряємо кеш користувача
      const cachedUser = userCache.get('current_user');
      if (cachedUser) {
        this.user = cachedUser;
        this.isAuthenticated = true;
        this.isInitialized = true;
        return {
          isAuthenticated: true,
          user: cachedUser
        };
      }

      // Верифікуємо токен з сервером
      const response = await AuthAPI.verify();

      if (response.success && response.data?.valid && response.data?.user) {
        this.user = response.data.user;
        this.isAuthenticated = true;
        userCache.set('current_user', this.user, 300000);

        // Оновлюємо дані користувача в localStorage
        const storedAuth = this.getStoredAuth();
        storedAuth.user = this.user;
        this.saveAuth(storedAuth);
      } else {
        // Токен невалідний
        this.clearAuth();
        this.isAuthenticated = false;
        this.user = null;
      }

    } catch (error) {
      console.error('Auth initialization error:', error);
      // При помилці вважаємо користувача неавторизованим
      this.isAuthenticated = false;
      this.user = null;
    }

    this.isInitialized = true;

    return {
      isAuthenticated: this.isAuthenticated,
      user: this.user
    };
  }

  /**
   * Перевірити авторизацію
   */
  async check() {
    if (!this.isInitialized) {
      return this.init();
    }

    return {
      isAuthenticated: this.isAuthenticated,
      user: this.user
    };
  }

  /**
   * Авторизація через Telegram
   */
  async loginWithTelegram(initData) {
    try {
      const response = await AuthAPI.loginWithTelegram(initData);

      if (response.success && response.data) {
        // AuthAPI вже зберігає токени і відправляє подію
        this.user = response.data.user;
        this.isAuthenticated = true;

        return {
          success: true,
          user: this.user
        };
      }

      return {
        success: false,
        error: response.error || 'Login failed'
      };

    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        error: error.message || 'Login failed'
      };
    }
  }

  /**
   * Вийти з системи
   */
  async logout() {
    try {
      await AuthAPI.logout();
    } catch (error) {
      console.error('Logout error:', error);
    }

    // Очищаємо локальні дані
    this.clearAuth();
    this.user = null;
    this.isAuthenticated = false;

    // Перенаправляємо на логін
    window.location.href = '/login';
  }

  /**
   * Оновити профіль користувача
   */
  async updateProfile(data) {
    try {
      const response = await AuthAPI.updateProfile(data);

      if (response.success && response.data?.user) {
        this.user = response.data.user;

        // Оновлюємо кеш
        userCache.set('current_user', this.user, 300000);

        // Оновлюємо localStorage
        const authData = this.getStoredAuth();
        authData.user = this.user;
        this.saveAuth(authData);

        return { success: true, user: this.user };
      }

      return {
        success: false,
        error: response.error || 'Update failed'
      };

    } catch (error) {
      console.error('Profile update error:', error);
      return {
        success: false,
        error: error.message || 'Update failed'
      };
    }
  }

  /**
   * Отримати поточного користувача
   */
  getCurrentUser() {
    return this.user;
  }

  /**
   * Перевірити чи авторизований
   */
  isLoggedIn() {
    return this.isAuthenticated;
  }

  /**
   * Отримати збережені дані авторизації
   */
  getStoredAuth() {
    try {
      return JSON.parse(localStorage.getItem('auth') || '{}');
    } catch (e) {
      console.error('Failed to parse auth data:', e);
      return {};
    }
  }

  /**
   * Зберегти дані авторизації
   */
  saveAuth(authData) {
    try {
      localStorage.setItem('auth', JSON.stringify(authData));
    } catch (e) {
      console.error('Failed to save auth data:', e);
    }
  }

  /**
   * Очистити дані авторизації
   */
  clearAuth() {
    localStorage.removeItem('auth');
    userCache.delete('current_user');
    apiClient.clearTokens();
  }

  /**
   * Отримати токен
   */
  getAccessToken() {
    const authData = this.getStoredAuth();
    return authData.access_token || null;
  }

  /**
   * Оновити токени (викликається з APIClient)
   */
  updateTokens(tokens) {
    const authData = this.getStoredAuth();
    authData.access_token = tokens.access_token;
    authData.refresh_token = tokens.refresh_token || authData.refresh_token;

    if (tokens.expires_in) {
      authData.expires_at = new Date(Date.now() + tokens.expires_in * 1000).toISOString();
    }

    this.saveAuth(authData);
  }

  /**
   * Middleware для захищених роутів
   */
  async requireAuth() {
    const { isAuthenticated } = await this.check();

    if (!isAuthenticated) {
      window.location.href = '/login';
      return false;
    }

    return true;
  }

  /**
   * Middleware для адмін роутів
   */
  async requireAdmin() {
    const { isAuthenticated, user } = await this.check();

    if (!isAuthenticated) {
      window.location.href = '/login';
      return false;
    }

    if (!user?.is_admin) {
      window.location.href = '/';
      return false;
    }

    return true;
  }
}

// Створюємо singleton
export const authService = new AuthService();

// Експортуємо хелпери
export const isAuthenticated = () => authService.isLoggedIn();
export const getCurrentUser = () => authService.getCurrentUser();
export const requireAuth = () => authService.requireAuth();
export const requireAdmin = () => authService.requireAdmin();

// Автоматично ініціалізуємо при завантаженні
if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    authService.init().catch(console.error);
  });
}

export default authService;