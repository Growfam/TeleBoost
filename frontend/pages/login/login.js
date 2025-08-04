// frontend/pages/login/login.js
/**
 * Сторінка автоматичного входу TeleBoost
 * Production версія
 */

import TelegramAuth from '/frontend/shared/auth/TelegramAuth.js';
import { ToastProvider } from '/frontend/shared/components/Toast.js';

class LoginPage {
  constructor() {
    this.telegramAuth = null;
  }

  /**
   * Ініціалізація сторінки
   */
  async init() {
    // Ініціалізуємо Toast провайдер
    const toastProvider = new ToastProvider();
    toastProvider.init();

    // Перевіряємо існуючу авторизацію
    const hasAuth = await this.checkExistingAuth();
    if (hasAuth) {
      return; // Вже перенаправили
    }

    // Ініціалізуємо Telegram Web App
    this.initTelegram();

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
    }

    return false;
  }

  /**
   * Ініціалізація Telegram Web App
   */
  initTelegram() {
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;
      tg.expand();
      tg.setHeaderColor('#1a0033');
      tg.setBackgroundColor('#000000');
      tg.ready();
    }
  }

  /**
   * Ініціалізація компонента авторизації
   */
  initAuthComponent() {
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
    if (window.showToast) {
      window.showToast(`Ласкаво просимо, ${authData.user.first_name}!`, 'success');
    }
  }

  /**
   * Обробка помилки авторизації
   */
  handleAuthError(error) {
    let errorMessage = 'Не вдалося увійти. Спробуйте ще раз.';

    if (error.message?.includes('відкрийте додаток через Telegram')) {
      errorMessage = 'Будь ласка, відкрийте додаток через Telegram';
    }

    if (window.showToast) {
      window.showToast(errorMessage, 'error');
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
});