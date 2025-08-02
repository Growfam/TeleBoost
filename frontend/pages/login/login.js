// frontend/pages/login/login.js
/**
 * Сторінка логіну TeleBoost
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

    // Перевіряємо чи вже авторизований
    await this.checkExistingAuth();

    // Ініціалізуємо Telegram Web App
    this.initTelegram();

    // Створюємо компонент авторизації
    this.initAuthComponent();

    // Анімуємо появу елементів
    this.animatePageLoad();
  }

  /**
   * Перевірка існуючої авторизації
   */
  async checkExistingAuth() {
    try {
      const authData = JSON.parse(localStorage.getItem('auth') || '{}');

      if (authData.access_token && authData.user) {
        // Перевіряємо чи не прострочений токен
        if (authData.expires_at) {
          const expiresAt = new Date(authData.expires_at);
          if (expiresAt > new Date()) {
            // Токен валідний - перенаправляємо на головну
            console.log('User already authenticated, redirecting...');
            window.location.href = '/';
            return;
          }
        }
      }
    } catch (error) {
      console.error('Error checking auth:', error);
    }
  }

  /**
   * Ініціалізація Telegram Web App
   */
  initTelegram() {
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;

      // Розширюємо на весь екран
      tg.expand();

      // Встановлюємо кольори
      tg.setHeaderColor('#1a0033');
      tg.setBackgroundColor('#000000');

      // Готовність
      tg.ready();

      // Логування для дебагу
      if (window.CONFIG?.DEBUG) {
        console.log('Telegram WebApp initialized:', {
          initData: tg.initData,
          user: tg.initDataUnsafe?.user,
          startParam: tg.initDataUnsafe?.start_param
        });
      }
    }
  }

  /**
   * Ініціалізація компонента авторизації
   */
  initAuthComponent() {
    this.telegramAuth = new TelegramAuth({
      onSuccess: this.handleAuthSuccess.bind(this),
      onError: this.handleAuthError.bind(this),
      showUserInfo: false,
      autoLogin: true // Автоматично авторизуємо якщо є дані від Telegram
    });

    // Ініціалізуємо в контейнері
    this.telegramAuth.init('auth-container');
  }

  /**
   * Обробка успішної авторизації
   */
  handleAuthSuccess(authData) {
    console.log('Auth success:', authData);

    if (window.showToast) {
      window.showToast(`Ласкаво просимо, ${authData.user.first_name}!`, 'success');
    }

    // Перенаправляємо на головну через 1 секунду
    setTimeout(() => {
      window.location.href = '/';
    }, 1000);
  }

  /**
   * Обробка помилки авторизації
   */
  handleAuthError(error) {
    console.error('Auth error:', error);

    if (window.showToast) {
      window.showToast(error.message || 'Помилка авторизації', 'error');
    }

    // Показуємо додаткове повідомлення
    const errorContainer = document.createElement('div');
    errorContainer.className = 'error-container animate-fadeIn';
    errorContainer.innerHTML = `
      <p class="error-message">
        ${error.message || 'Не вдалося увійти. Спробуйте ще раз.'}
      </p>
    `;

    const authContainer = document.getElementById('auth-container');
    if (authContainer) {
      authContainer.appendChild(errorContainer);

      // Видаляємо через 5 секунд
      setTimeout(() => {
        errorContainer.remove();
      }, 5000);
    }
  }

  /**
   * Анімація завантаження сторінки
   */
  animatePageLoad() {
    // Додаємо клас для активації CSS анімацій
    document.body.classList.add('page-loaded');

    // Анімуємо features по черзі
    const features = document.querySelectorAll('.feature-item');
    features.forEach((feature, index) => {
      setTimeout(() => {
        feature.classList.add('animate-slideInLeft');
      }, 100 * index);
    });
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

  // Зберігаємо інстанс для дебагу
  if (window.CONFIG?.DEBUG) {
    window.loginPage = loginPage;
  }
});

// Обробка виходу зі сторінки
window.addEventListener('beforeunload', () => {
  if (window.loginPage) {
    window.loginPage.destroy();
  }
});