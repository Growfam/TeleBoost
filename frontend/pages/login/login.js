// frontend/pages/login/login.js
/**
 * Сторінка логіну TeleBoost
 */

import TelegramAuth from '/frontend/shared/auth/TelegramAuth.js';
import { ToastProvider } from '/frontend/shared/components/Toast.js';

class LoginPage {
  constructor() {
    this.telegramAuth = null;
    this.initAttempts = 0;
    this.maxInitAttempts = 5;
  }

  /**
   * Ініціалізація сторінки
   */
  async init() {
    // Ініціалізуємо Toast провайдер
    const toastProvider = new ToastProvider();
    toastProvider.init();

    // Перевіряємо чи вже авторизований
    const hasAuth = await this.checkExistingAuth();
    if (hasAuth) {
      return; // Вже редіректнули
    }

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
            window.location.href = '/home';
            return true;
          }
        }
      }
    } catch (error) {
      console.error('Error checking auth:', error);
    }

    return false;
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

      // Намагаємось автологін після ready
      this.attemptAutoLogin();
    } else {
      // Показуємо попередження що потрібен Telegram
      this.showBrowserWarning();
    }
  }

  /**
   * Спроба автологіну
   */
  attemptAutoLogin() {
    // Чекаємо трохи щоб initData була готова
    setTimeout(() => {
      const tg = window.Telegram?.WebApp;

      if (tg?.initData && this.telegramAuth) {
        console.log('Attempting auto-login with Telegram data');
        this.telegramAuth.handleAuth();
      } else if (this.initAttempts < this.maxInitAttempts) {
        // Пробуємо ще раз через більший інтервал
        this.initAttempts++;
        setTimeout(() => this.attemptAutoLogin(), 200 * this.initAttempts);
      } else {
        console.log('Auto-login not available - no initData');
      }
    }, 100);
  }

  /**
   * Показати попередження для браузера
   */
  showBrowserWarning() {
    const warningHtml = `
      <div class="browser-warning glass-card animate-fadeIn">
        <div class="warning-icon">⚠️</div>
        <h3 class="warning-title">Telegram Required</h3>
        <p class="warning-text">
          Цей додаток працює тільки через Telegram.
          <br>
          Будь ласка, відкрийте бота в Telegram.
        </p>
        <a href="https://t.me/${window.CONFIG?.BOT_USERNAME || 'TeleeBoost_bot'}" 
           class="btn btn-primary" 
           target="_blank">
          Відкрити в Telegram
        </a>
      </div>
    `;

    // Додаємо попередження в auth-container
    const authContainer = document.getElementById('auth-container');
    if (authContainer) {
      authContainer.innerHTML = warningHtml;
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
      window.location.href = '/home';
    }, 1000);
  }

  /**
   * Обробка помилки авторизації
   */
  handleAuthError(error) {
    console.error('Auth error:', error);

    // Показуємо специфічне повідомлення для різних помилок
    let errorMessage = 'Не вдалося увійти. Спробуйте ще раз.';

    if (error.message?.includes('Telegram WebApp недоступний')) {
      errorMessage = 'Будь ласка, відкрийте додаток через Telegram';
      this.showBrowserWarning();
      return;
    } else if (error.code === 'INVALID_TELEGRAM_DATA') {
      errorMessage = 'Неправильні дані від Telegram. Спробуйте перезапустити бота.';
    } else if (error.code === 'USER_CREATION_FAILED') {
      errorMessage = 'Не вдалося створити користувача. Зверніться до підтримки.';
    }

    if (window.showToast) {
      window.showToast(errorMessage, 'error');
    }

    // Показуємо додаткове повідомлення
    const errorContainer = document.createElement('div');
    errorContainer.className = 'error-container animate-fadeIn';
    errorContainer.innerHTML = `
      <p class="error-message">
        ${error.message || errorMessage}
      </p>
    `;

    const authContainer = document.getElementById('auth-container');
    if (authContainer && !authContainer.querySelector('.browser-warning')) {
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

// Стилі для browser warning
const warningStyles = `
<style>
.browser-warning {
  max-width: 320px;
  margin: 0 auto;
  padding: 32px;
  text-align: center;
}

.warning-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.warning-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.warning-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 24px;
  line-height: 1.5;
}

.browser-warning .btn {
  width: 100%;
}
</style>
`;

// Додаємо стилі
if (!document.getElementById('warning-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'warning-styles';
  styleElement.innerHTML = warningStyles;
  document.head.appendChild(styleElement);
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