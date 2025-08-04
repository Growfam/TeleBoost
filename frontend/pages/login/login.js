// frontend/pages/login/login.js
/**
 * Сторінка автоматичного входу TeleBoost
 * Production версія
 * FIXED: Додано виклик tg.ready() та повна діагностика
 */

import TelegramAuth from '/frontend/shared/auth/TelegramAuth.js';
import { ToastProvider } from '/frontend/shared/components/Toast.js';

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

    // Ініціалізуємо Telegram Web App з повною діагностикою
    await this.initTelegram();

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
   * Ініціалізація Telegram Web App
   */
  async initTelegram() {
    this.addDebugInfo('Initializing Telegram WebApp...');

    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;

      // Діагностика перед ready()
      this.addDebugInfo(`Before ready() - Platform: ${tg.platform}, Version: ${tg.version}`);
      this.addDebugInfo(`Before ready() - initData exists: ${!!tg.initData}`);
      this.addDebugInfo(`Before ready() - initDataUnsafe exists: ${!!tg.initDataUnsafe}`);

      // Викликаємо ready() і чекаємо трохи
      try {
        tg.ready();
        this.addDebugInfo('Called tg.ready()');

        // Чекаємо 100мс після ready()
        await new Promise(resolve => setTimeout(resolve, 100));

        // Повторна діагностика після ready()
        this.addDebugInfo(`After ready() - initData exists: ${!!tg.initData}`);
        this.addDebugInfo(`After ready() - initData length: ${tg.initData ? tg.initData.length : 0}`);

        // Встановлюємо тему та розширюємо
        tg.expand();
        tg.setHeaderColor('#1a0033');
        tg.setBackgroundColor('#000000');

        this.addDebugInfo('Telegram WebApp configured successfully');

        // Якщо все ще немає initData, спробуємо ще раз через секунду
        if (!tg.initData) {
          this.addDebugInfo('No initData after ready(), waiting 1 second...');
          await new Promise(resolve => setTimeout(resolve, 1000));

          // Викликаємо ready() ще раз
          tg.ready();
          this.addDebugInfo('Called tg.ready() again');

          // Фінальна перевірка
          this.addDebugInfo(`Final check - initData exists: ${!!tg.initData}`);
        }

      } catch (e) {
        this.addDebugInfo(`Error during Telegram init: ${e.message}`);
      }

      // Додаткова діагностика середовища
      this.diagnoseTelegramEnvironment();

    } else {
      this.addDebugInfo('Telegram WebApp not available');
    }
  }

  /**
   * Діагностика Telegram середовища
   */
  diagnoseTelegramEnvironment() {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;

    // Перевіряємо всі доступні властивості
    const properties = [
      'initData',
      'initDataUnsafe',
      'version',
      'platform',
      'colorScheme',
      'themeParams',
      'isExpanded',
      'viewportHeight',
      'viewportStableHeight',
      'headerColor',
      'backgroundColor',
      'isClosingConfirmationEnabled',
      'MainButton',
      'BackButton'
    ];

    this.addDebugInfo('=== Telegram WebApp Properties ===');
    properties.forEach(prop => {
      try {
        const value = tg[prop];
        const type = typeof value;
        if (type === 'object' && value !== null) {
          this.addDebugInfo(`${prop}: ${JSON.stringify(value)}`);
        } else if (type === 'string' && value.length > 100) {
          this.addDebugInfo(`${prop}: [string, length: ${value.length}]`);
        } else {
          this.addDebugInfo(`${prop}: ${value} (${type})`);
        }
      } catch (e) {
        this.addDebugInfo(`${prop}: [Error: ${e.message}]`);
      }
    });

    // Перевіряємо методи
    const methods = ['ready', 'expand', 'close', 'sendData', 'openLink', 'openTelegramLink'];
    this.addDebugInfo('=== Telegram WebApp Methods ===');
    methods.forEach(method => {
      this.addDebugInfo(`${method}: ${typeof tg[method]}`);
    });

    // Виводимо debug інформацію в консоль у зручному форматі
    if (window.location.hostname.includes('localhost') || window.location.hostname.includes('127.0.0.1')) {
      console.groupCollapsed('📱 Telegram WebApp Debug Info');
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