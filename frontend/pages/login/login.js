// frontend/pages/login/login.js
/**
 * Сторінка логіну TeleBoost
 * ВЕРСИЯ С ПОЛНЫМ ЛОГИРОВАНИЕМ ДЛЯ ДИАГНОСТИКИ
 */

import TelegramAuth from '/frontend/shared/auth/TelegramAuth.js';
import { ToastProvider } from '/frontend/shared/components/Toast.js';

class LoginPage {
  constructor() {
    console.log('🟨 LoginPage: Constructor called');
    this.telegramAuth = null;
    this.initAttempts = 0;
    this.maxInitAttempts = 5;
  }

  /**
   * Ініціалізація сторінки
   */
  async init() {
    console.log('🟨 LoginPage: init() called');
    console.log('🟨 LoginPage: Current URL:', window.location.href);
    console.log('🟨 LoginPage: localStorage auth:', localStorage.getItem('auth') ? 'EXISTS' : 'NOT EXISTS');

    // Ініціалізуємо Toast провайдер
    console.log('🟨 LoginPage: Initializing ToastProvider');
    const toastProvider = new ToastProvider();
    toastProvider.init();

    // Перевіряємо чи вже авторизований
    console.log('🟨 LoginPage: Checking existing auth...');
    const hasAuth = await this.checkExistingAuth();
    if (hasAuth) {
      console.log('🟨 LoginPage: User already authenticated, redirected to /home');
      return; // Вже редіректнули
    }

    // Ініціалізуємо Telegram Web App
    console.log('🟨 LoginPage: Initializing Telegram Web App');
    this.initTelegram();

    // Створюємо компонент авторизації
    console.log('🟨 LoginPage: Creating auth component');
    this.initAuthComponent();

    // Анімуємо появу елементів
    console.log('🟨 LoginPage: Animating page load');
    this.animatePageLoad();

    console.log('🟨 LoginPage: Initialization completed');
  }

  /**
   * Перевірка існуючої авторизації
   */
  async checkExistingAuth() {
    console.log('🟨 LoginPage: checkExistingAuth() called');

    try {
      const authRaw = localStorage.getItem('auth');
      console.log('🟨 LoginPage: Raw auth data:', {
        exists: !!authRaw,
        length: authRaw?.length || 0,
        preview: authRaw ? authRaw.substring(0, 100) + '...' : 'null'
      });

      if (!authRaw) {
        console.log('🟨 LoginPage: No auth data found');
        return false;
      }

      const authData = JSON.parse(authRaw);
      console.log('🟨 LoginPage: Parsed auth data:', {
        hasAccessToken: !!authData.access_token,
        hasUser: !!authData.user,
        hasExpiresAt: !!authData.expires_at,
        userName: authData.user?.first_name
      });

      if (authData.access_token && authData.user) {
        // Перевіряємо чи не прострочений токен
        if (authData.expires_at) {
          const expiresAt = new Date(authData.expires_at);
          const now = new Date();
          const isValid = expiresAt > now;

          console.log('🟨 LoginPage: Token expiration check:', {
            expiresAt: expiresAt.toISOString(),
            now: now.toISOString(),
            isValid: isValid,
            timeLeft: isValid ? Math.floor((expiresAt - now) / 1000) + ' seconds' : 'EXPIRED'
          });

          if (isValid) {
            // Токен валідний - перенаправляємо на головну
            console.log('🟨 LoginPage: Valid token found, redirecting to /home');
            window.location.href = '/home';
            return true;
          } else {
            console.log('🟨 LoginPage: Token expired, clearing auth');
            localStorage.removeItem('auth');
          }
        }
      }
    } catch (error) {
      console.error('🟨 LoginPage: Error checking auth:', error);
      localStorage.removeItem('auth');
    }

    console.log('🟨 LoginPage: No valid auth found');
    return false;
  }

  /**
   * Ініціалізація Telegram Web App
   */
  initTelegram() {
    console.log('🟨 LoginPage: initTelegram() called');
    console.log('🟨 LoginPage: window.Telegram:', !!window.Telegram);
    console.log('🟨 LoginPage: window.Telegram.WebApp:', !!window.Telegram?.WebApp);

    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;

      console.log('🟨 LoginPage: Telegram WebApp details:', {
        version: tg.version,
        platform: tg.platform,
        colorScheme: tg.colorScheme,
        viewportHeight: tg.viewportHeight,
        viewportStableHeight: tg.viewportStableHeight,
        isExpanded: tg.isExpanded,
        hasInitData: !!tg.initData,
        initDataLength: tg.initData?.length || 0
      });

      // Розширюємо на весь екран
      tg.expand();
      console.log('🟨 LoginPage: Called tg.expand()');

      // Встановлюємо кольори
      tg.setHeaderColor('#1a0033');
      tg.setBackgroundColor('#000000');
      console.log('🟨 LoginPage: Set header and background colors');

      // Готовність
      tg.ready();
      console.log('🟨 LoginPage: Called tg.ready()');

      // Логування для дебагу
      if (window.CONFIG?.DEBUG) {
        console.log('🟨 LoginPage: DEBUG - Telegram WebApp initialized:', {
          initData: tg.initData,
          user: tg.initDataUnsafe?.user,
          startParam: tg.initDataUnsafe?.start_param
        });
      }

      // Намагаємось автологін після ready
      console.log('🟨 LoginPage: Scheduling auto-login attempt');
      this.attemptAutoLogin();
    } else {
      console.log('🟨 LoginPage: Telegram WebApp not available, showing browser warning');
      // Показуємо попередження що потрібен Telegram
      this.showBrowserWarning();
    }
  }

  /**
   * Спроба автологіну
   */
  attemptAutoLogin() {
    console.log('🟨 LoginPage: attemptAutoLogin() called, attempt', this.initAttempts + 1);

    // Чекаємо трохи щоб initData була готова
    setTimeout(() => {
      const tg = window.Telegram?.WebApp;

      console.log('🟨 LoginPage: Auto-login check:', {
        hasTelegram: !!tg,
        hasInitData: !!tg?.initData,
        hasTelegramAuth: !!this.telegramAuth,
        attempt: this.initAttempts + 1
      });

      if (tg?.initData && this.telegramAuth) {
        console.log('🟨 LoginPage: Attempting auto-login with Telegram data');
        this.telegramAuth.handleAuth();
      } else if (this.initAttempts < this.maxInitAttempts) {
        // Пробуємо ще раз через більший інтервал
        this.initAttempts++;
        const nextDelay = 200 * this.initAttempts;
        console.log(`🟨 LoginPage: No initData yet, retrying in ${nextDelay}ms`);
        setTimeout(() => this.attemptAutoLogin(), nextDelay);
      } else {
        console.log('🟨 LoginPage: Max auto-login attempts reached, giving up');
      }
    }, 100);
  }

  /**
   * Показати попередження для браузера
   */
  showBrowserWarning() {
    console.log('🟨 LoginPage: showBrowserWarning() called');

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
      console.log('🟨 LoginPage: Browser warning displayed');
    } else {
      console.error('🟨 LoginPage: auth-container not found');
    }
  }

  /**
   * Ініціалізація компонента авторизації
   */
  initAuthComponent() {
    console.log('🟨 LoginPage: initAuthComponent() called');

    this.telegramAuth = new TelegramAuth({
      onSuccess: this.handleAuthSuccess.bind(this),
      onError: this.handleAuthError.bind(this),
      showUserInfo: false,
      autoLogin: true // Автоматично авторизуємо якщо є дані від Telegram
    });

    console.log('🟨 LoginPage: TelegramAuth instance created');

    // Ініціалізуємо в контейнері
    this.telegramAuth.init('auth-container');
    console.log('🟨 LoginPage: TelegramAuth initialized in auth-container');
  }

  /**
   * Обробка успішної авторизації
   */
  handleAuthSuccess(authData) {
    console.log('🟨 LoginPage: handleAuthSuccess() called');
    console.log('🟨 LoginPage: Auth data received:', {
      hasTokens: !!authData.tokens,
      hasUser: !!authData.user,
      userName: authData.user?.first_name,
      userId: authData.user?.telegram_id
    });

    // Перевіряємо що дані збережені в localStorage
    const savedAuth = localStorage.getItem('auth');
    console.log('🟨 LoginPage: Checking saved auth:', {
      exists: !!savedAuth,
      length: savedAuth?.length || 0
    });

    if (window.showToast) {
      const message = `Ласкаво просимо, ${authData.user.first_name}!`;
      console.log('🟨 LoginPage: Showing success toast:', message);
      window.showToast(message, 'success');
    }

    // Перенаправляємо на головну через 1 секунду
    console.log('🟨 LoginPage: Scheduling redirect to /home in 1 second');
    setTimeout(() => {
      console.log('🟨 LoginPage: Redirecting to /home');
      window.location.href = '/home';
    }, 1000);
  }

  /**
   * Обробка помилки авторизації
   */
  handleAuthError(error) {
    console.error('🟨 LoginPage: handleAuthError() called:', {
      message: error.message,
      code: error.code,
      stack: error.stack
    });

    // Показуємо специфічне повідомлення для різних помилок
    let errorMessage = 'Не вдалося увійти. Спробуйте ще раз.';

    if (error.message?.includes('Telegram WebApp недоступний')) {
      errorMessage = 'Будь ласка, відкрийте додаток через Telegram';
      console.log('🟨 LoginPage: Telegram not available, showing browser warning');
      this.showBrowserWarning();
      return;
    } else if (error.code === 'INVALID_TELEGRAM_DATA') {
      errorMessage = 'Неправильні дані від Telegram. Спробуйте перезапустити бота.';
    } else if (error.code === 'USER_CREATION_FAILED') {
      errorMessage = 'Не вдалося створити користувача. Зверніться до підтримки.';
    }

    console.log('🟨 LoginPage: Error message to show:', errorMessage);

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
      console.log('🟨 LoginPage: Error message displayed in UI');

      // Видаляємо через 5 секунд
      setTimeout(() => {
        errorContainer.remove();
        console.log('🟨 LoginPage: Error message removed');
      }, 5000);
    }
  }

  /**
   * Анімація завантаження сторінки
   */
  animatePageLoad() {
    console.log('🟨 LoginPage: animatePageLoad() called');

    // Додаємо клас для активації CSS анімацій
    document.body.classList.add('page-loaded');

    // Анімуємо features по черзі
    const features = document.querySelectorAll('.feature-item');
    console.log(`🟨 LoginPage: Found ${features.length} feature items to animate`);

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
    console.log('🟨 LoginPage: destroy() called');
    if (this.telegramAuth) {
      this.telegramAuth.destroy();
      console.log('🟨 LoginPage: TelegramAuth destroyed');
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
  console.log('🟨 LoginPage: Adding warning styles');
  const styleElement = document.createElement('div');
  styleElement.id = 'warning-styles';
  styleElement.innerHTML = warningStyles;
  document.head.appendChild(styleElement);
}

// Ініціалізація при завантаженні
document.addEventListener('DOMContentLoaded', () => {
  console.log('🟨 LoginPage: DOMContentLoaded event fired');
  console.log('🟨 LoginPage: Page URL:', window.location.href);
  console.log('🟨 LoginPage: Creating LoginPage instance');

  const loginPage = new LoginPage();
  loginPage.init();

  // Зберігаємо інстанс для дебагу
  if (window.CONFIG?.DEBUG) {
    window.loginPage = loginPage;
    console.log('🟨 LoginPage: DEBUG - loginPage instance exposed to window');
  }
});

// Обробка виходу зі сторінки
window.addEventListener('beforeunload', () => {
  console.log('🟨 LoginPage: beforeunload event fired');
  if (window.loginPage) {
    window.loginPage.destroy();
  }
});

// Логування глобальних помилок
window.addEventListener('error', (event) => {
  console.error('🟨 LoginPage: Global error:', {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    error: event.error
  });
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('🟨 LoginPage: Unhandled promise rejection:', {
    reason: event.reason,
    promise: event.promise
  });
});

console.log('🟨 LoginPage: Script loaded successfully');