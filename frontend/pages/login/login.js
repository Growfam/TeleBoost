// frontend/pages/login/login.js
/**
 * Сторінка автоматичного входу TeleBoost
 * Production версія з використанням централізованого TelegramWebApp сервісу
 */

import TelegramAuth from '/frontend/shared/auth/TelegramAuth.js';
import { ToastProvider } from '/frontend/shared/components/Toast.js';
import telegramWebApp from '/frontend/shared/services/TelegramWebApp.js';

class LoginPage {
  constructor() {
    this.telegramAuth = null;
    this.debugInfo = [];
  }

  /**
   * Додати debug інформацію
   */
  addDebugInfo(message) {
    this.debugInfo.push(`[${new Date().toISOString()}] ${message}`);
    console.log(`LoginPage: ${message}`);
  }

  /**
   * Ініціалізація сторінки
   */
  async init() {
    this.addDebugInfo('Starting login page initialization...');

    // Ініціалізуємо Toast провайдер
    const toastProvider = new ToastProvider();
    toastProvider.init();

    // Перевіряємо існуючу авторизацію
    const hasAuth = await this.checkExistingAuth();
    if (hasAuth) {
      this.addDebugInfo('Existing auth found, redirecting...');
      return; // Вже перенаправили
    }

    // Ініціалізуємо Telegram Web App через сервіс
    this.addDebugInfo('Initializing Telegram WebApp service...');
    const initialized = await telegramWebApp.init();
    this.addDebugInfo(`TelegramWebApp service initialized: ${initialized}`);

    // Діагностика після ініціалізації
    this.diagnoseTelegramEnvironment();

    // Створюємо компонент автоматичної авторизації
    this.initAuthComponent();
  }

  /**
   * Перевірка існуючої авторизації
   */
  async checkExistingAuth() {
    try {
      const authData = JSON.parse(localStorage.getItem('auth') || '{}');

      if (authData.access_token && authData.user) {
        // Перевіряємо термін дії токена
        if (authData.expires_at) {
          const expiresAt = new Date(authData.expires_at);
          if (expiresAt > new Date()) {
            // Токен валідний - перенаправляємо на головну
            window.location.href = '/home';
            return true;
          }
        }
      }
    } catch (error) {
      localStorage.removeItem('auth');
      this.addDebugInfo(`Error checking existing auth: ${error.message}`);
    }

    return false;
  }

  /**
   * Діагностика Telegram середовища
   */
  diagnoseTelegramEnvironment() {
    const tg = telegramWebApp.getTelegramWebApp();
    if (!tg) {
      this.addDebugInfo('Telegram WebApp not available');
      return;
    }

    // Основні властивості
    this.addDebugInfo(`Platform: ${tg.platform}`);
    this.addDebugInfo(`Version: ${tg.version}`);
    this.addDebugInfo(`ColorScheme: ${tg.colorScheme}`);
    this.addDebugInfo(`IsExpanded: ${tg.isExpanded}`);
    this.addDebugInfo(`ViewportHeight: ${tg.viewportHeight}`);

    // Дані ініціалізації
    const initData = telegramWebApp.getInitData();
    const initDataUnsafe = telegramWebApp.getInitDataUnsafe();

    this.addDebugInfo(`InitData exists: ${!!initData}`);
    this.addDebugInfo(`InitData length: ${initData ? initData.length : 0}`);

    if (initDataUnsafe) {
      this.addDebugInfo(`InitDataUnsafe keys: ${Object.keys(initDataUnsafe).join(', ')}`);
      if (initDataUnsafe.user) {
        this.addDebugInfo(`User ID: ${initDataUnsafe.user.id}`);
        this.addDebugInfo(`Username: ${initDataUnsafe.user.username}`);
        this.addDebugInfo(`First name: ${initDataUnsafe.user.first_name}`);
      }
    }

    // Перевірка чи це Telegram WebApp
    const isTelegramWebApp = telegramWebApp.isTelegramWebApp();
    this.addDebugInfo(`Is Telegram WebApp: ${isTelegramWebApp}`);

    // Виводимо debug інформацію в консоль
    if (window.location.hostname.includes('localhost') || window.location.hostname.includes('127.0.0.1')) {
      console.groupCollapsed('📱 LoginPage Debug Info');
      this.debugInfo.forEach(line => console.log(line));
      console.groupEnd();
    }
  }

  /**
   * Ініціалізація компонента авторизації
   */
  initAuthComponent() {
    this.addDebugInfo('Initializing auth component...');

    this.telegramAuth = new TelegramAuth({
      onSuccess: this.handleAuthSuccess.bind(this),
      onError: this.handleAuthError.bind(this)
    });

    // Ініціалізуємо в контейнері
    this.telegramAuth.init('auth-container');
  }

  /**
   * Обробка успішної авторизації
   */
  handleAuthSuccess(authData) {
    this.addDebugInfo(`Auth success for user: ${authData.user.first_name}`);

    if (window.showToast) {
      window.showToast(`Ласкаво просимо, ${authData.user.first_name}!`, 'success');
    }
  }

  /**
   * Обробка помилки авторизації
   */
  handleAuthError(error) {
    this.addDebugInfo(`Auth error: ${error.message}`);

    let errorMessage = 'Не вдалося увійти. Спробуйте ще раз.';

    if (error.message?.includes('відкрийте додаток через Telegram')) {
      errorMessage = 'Будь ласка, відкрийте додаток через Telegram';
    }

    if (window.showToast) {
      window.showToast(errorMessage, 'error');
    }

    // Додаємо кнопку для перезавантаження
    const authContainer = document.getElementById('auth-container');
    if (authContainer && !authContainer.querySelector('.retry-container')) {
      const retryHtml = `
        <div class="retry-container" style="text-align: center; margin-top: 20px;">
          <button class="retry-button" style="
            padding: 12px 24px;
            background: linear-gradient(135deg, #a855f7 0%, #9333ea 100%);
            border: none;
            border-radius: 12px;
            color: white;
            font-weight: 600;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s ease;
          " onclick="window.location.reload()">
            Спробувати знову
          </button>
        </div>
      `;
      authContainer.insertAdjacentHTML('beforeend', retryHtml);
    }
  }

  /**
   * Очищення при виході зі сторінки
   */
  destroy() {
    if (this.telegramAuth) {
      this.telegramAuth.destroy();
    }
  }
}

// Ініціалізація при завантаженні
document.addEventListener('DOMContentLoaded', () => {
  const loginPage = new LoginPage();
  loginPage.init();

  // Очищення при виході
  window.addEventListener('beforeunload', () => {
    loginPage.destroy();
  });

  // Експортуємо для debug
  if (window.location.hostname.includes('localhost') || window.location.hostname.includes('127.0.0.1')) {
    window.loginPage = loginPage;
  }
});