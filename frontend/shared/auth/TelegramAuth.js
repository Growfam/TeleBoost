// frontend/shared/auth/TelegramAuth.js
/**
 * Компонент Telegram авторизації для TeleBoost
 * Оновлена версія з покращеною обробкою помилок
 */

import { getIcon } from '../ui/svg.js';

// Стилі для компонента
const styles = `
<style>
.telegram-auth-container {
  max-width: 400px;
  margin: 0 auto;
  padding: 20px;
}

.telegram-auth-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  padding: 32px;
  position: relative;
  overflow: hidden;
  animation: slideUp 0.6s ease-out;
}

.auth-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle at center, rgba(168, 85, 247, 0.1) 0%, transparent 70%);
  animation: pulse 4s ease-in-out infinite;
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
  position: relative;
  z-index: 1;
}

.auth-icon-container {
  width: 64px;
  height: 64px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, #0088cc 0%, #0077bb 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(0, 136, 204, 0.3);
  animation: float 3s ease-in-out infinite;
}

.auth-title {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 8px;
}

.auth-subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.5;
}

.user-info {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 24px;
  position: relative;
  z-index: 1;
}

.user-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.user-avatar {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}

.user-details {
  flex: 1;
}

.user-name {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 4px;
}

.user-id {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
}

.auth-button {
  width: 100%;
  padding: 16px 24px;
  background: linear-gradient(135deg, #0088cc 0%, #0077bb 100%);
  border: none;
  border-radius: 12px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.auth-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(0, 136, 204, 0.4);
}

.auth-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  background: rgba(255, 255, 255, 0.1);
}

.auth-button.success {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
}

.auth-loading {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.7);
  text-align: center;
  margin-top: 20px;
}

.auth-error {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  padding: 16px;
  margin-top: 16px;
  color: #fff;
  font-size: 14px;
  text-align: center;
}

/* Browser warning styles */
.browser-warning {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  position: relative;
  z-index: 1;
  animation: slideUp 0.6s ease-out;
}

.warning-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(245, 158, 11, 0.2);
  border-radius: 12px;
}

.warning-title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 8px;
  text-align: center;
}

.warning-text {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  text-align: center;
  line-height: 1.5;
  margin-bottom: 20px;
}

.warning-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: linear-gradient(135deg, #0088cc 0%, #0077bb 100%);
  border-radius: 12px;
  color: #fff;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s ease;
}

.warning-link:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 136, 204, 0.3);
}

.premium-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.1), rgba(245, 158, 11, 0.1));
  border: 1px solid rgba(251, 191, 36, 0.3);
  border-radius: 8px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 600;
  color: #fbbf24;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.3;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
`;

/**
 * Компонент Telegram авторизації
 */
export class TelegramAuth {
  constructor(options = {}) {
    this.options = {
      onSuccess: options.onSuccess || (() => {}),
      onError: options.onError || (() => {}),
      botUsername: options.botUsername || window.CONFIG?.BOT_USERNAME || 'TeleeBoost_bot',
      buttonText: options.buttonText || 'Увійти через Telegram',
      showUserInfo: options.showUserInfo !== false,
      autoLogin: options.autoLogin !== false
    };

    this.state = {
      isLoading: false,
      error: null,
      user: null,
      isAuthenticated: false,
      isTelegramAvailable: false
    };

    this.element = null;
    this.autoLoginAttempted = false;
  }

  /**
   * Рендер компонента
   */
  render() {
    return `
      ${styles}
      <div class="telegram-auth-container">
        ${this.state.isTelegramAvailable ? this.renderAuthCard() : this.renderBrowserWarning()}
      </div>
    `;
  }

  /**
   * Рендер карточки авторизації
   */
  renderAuthCard() {
    return `
      <div class="telegram-auth-card">
        <div class="auth-glow"></div>
        
        <!-- Header -->
        <div class="auth-header">
          <div class="auth-icon-container">
            ${getIcon('telegram', '', 32)}
          </div>
          <h2 class="auth-title">
            ${this.state.isAuthenticated ? 'Ласкаво просимо!' : 'Вхід через Telegram'}
          </h2>
          <p class="auth-subtitle">
            ${this.state.isAuthenticated 
              ? 'Ви успішно увійшли в систему' 
              : 'Безпечна авторизація через Telegram'
            }
          </p>
        </div>

        ${this.renderContent()}
      </div>
    `;
  }

  /**
   * Рендер попередження для браузера
   */
  renderBrowserWarning() {
    return `
      <div class="browser-warning">
        <div class="warning-icon">
          ${getIcon('warning', '', 32)}
        </div>
        <h3 class="warning-title">Відкрийте в Telegram</h3>
        <p class="warning-text">
          Цей додаток працює тільки в Telegram.<br>
          Натисніть кнопку нижче, щоб відкрити бота.
        </p>
        <div style="text-align: center;">
          <a href="https://t.me/${this.options.botUsername}" class="warning-link" target="_blank">
            ${getIcon('telegram', '', 20)}
            <span>Відкрити в Telegram</span>
          </a>
        </div>
      </div>
      
      <!-- Показуємо кнопку для тестування в dev режимі -->
      ${window.CONFIG?.DEBUG ? `
        <div class="telegram-auth-card" style="margin-top: 20px; opacity: 0.7;">
          <div class="auth-header">
            <h3 style="font-size: 16px; margin-bottom: 16px;">Режим розробки</h3>
          </div>
          <button class="auth-button" onclick="window.telegramAuth.handleDevLogin()">
            ${getIcon('profile', '', 20)}
            <span>Тестовий вхід</span>
          </button>
        </div>
      ` : ''}
    `;
  }

  /**
   * Рендер основного контенту
   */
  renderContent() {
    // Якщо показуємо інформацію про користувача
    if (this.options.showUserInfo && this.state.user) {
      return this.renderUserInfo();
    }

    // Кнопка авторизації
    if (!this.state.isAuthenticated) {
      return this.renderAuthButton();
    }

    // Кнопка успішної авторизації
    return this.renderSuccessButton();
  }

  /**
   * Рендер інформації про користувача
   */
  renderUserInfo() {
    const user = this.state.user;
    const initials = this.getInitials(user);

    return `
      <div class="user-info">
        <div class="user-row">
          <div class="user-avatar">${initials}</div>
          <div class="user-details">
            <div style="display: flex; align-items: center; gap: 8px;">
              <div class="user-name">
                ${user.first_name} ${user.last_name || ''}
              </div>
              ${user.is_premium ? '<div class="premium-badge">⭐ Premium</div>' : ''}
            </div>
            <div class="user-id">#${this.formatUserId(user.telegram_id)}</div>
          </div>
        </div>
        
        ${user.username ? `
          <div style="padding: 12px 0; border-top: 1px solid rgba(255, 255, 255, 0.05);">
            <div style="display: flex; justify-content: space-between;">
              <span style="color: rgba(255, 255, 255, 0.6);">Username</span>
              <span style="color: #fff;">@${user.username}</span>
            </div>
          </div>
        ` : ''}
      </div>
      
      ${this.renderSuccessButton()}
    `;
  }

  /**
   * Рендер кнопки авторизації
   */
  renderAuthButton() {
    return `
      <button 
        class="auth-button ${this.state.isLoading ? 'disabled' : ''}"
        onclick="window.telegramAuth.handleAuth()"
        ${this.state.isLoading ? 'disabled' : ''}
      >
        ${this.state.isLoading ? `
          ${getIcon('loading', 'animate-spin', 20)}
          <span>Авторизація...</span>
        ` : `
          ${getIcon('telegram', '', 20)}
          <span>${this.options.buttonText}</span>
        `}
      </button>
      
      ${this.state.error ? `
        <div class="auth-error">${this.state.error}</div>
      ` : ''}
      
      ${this.state.isLoading ? `
        <p class="auth-loading">
          Зачекайте, перевіряємо ваш Telegram акаунт...
        </p>
      ` : ''}
    `;
  }

  /**
   * Рендер кнопки успішної авторизації
   */
  renderSuccessButton() {
    return `
      <button class="auth-button success">
        ${getIcon('success', '', 20)}
        <span>Авторизовано</span>
      </button>
    `;
  }

  /**
   * Ініціалізація компонента
   */
  init(containerId) {
    this.element = document.getElementById(containerId);
    if (!this.element) {
      console.error(`Container ${containerId} not found`);
      return;
    }

    // Перевіряємо доступність Telegram
    this.checkTelegramAvailability();

    // Рендеримо компонент
    this.element.innerHTML = this.render();

    // Зберігаємо посилання в window для onclick
    window.telegramAuth = this;

    // Ініціалізуємо Telegram Web App
    this.initTelegram();

    // Автологін якщо увімкнено і доступний Telegram
    if (this.options.autoLogin && this.state.isTelegramAvailable && !this.autoLoginAttempted) {
      this.autoLoginAttempted = true;
      setTimeout(() => {
        if (window.Telegram?.WebApp?.initData) {
          this.handleAuth();
        }
      }, 500);
    }
  }

  /**
   * Перевірка доступності Telegram
   */
  checkTelegramAvailability() {
    const tg = window.Telegram?.WebApp;
    this.state.isTelegramAvailable = !!(tg && tg.initData);

    // В режимі розробки завжди показуємо інтерфейс
    if (window.CONFIG?.DEBUG && !this.state.isTelegramAvailable) {
      console.log('Debug mode: Telegram not available, showing browser warning');
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
    }
  }

  /**
   * Обробка авторизації
   */
  async handleAuth() {
    try {
      this.setState({ isLoading: true, error: null });

      const tg = window.Telegram.WebApp;

      if (!tg || !tg.initData) {
        throw new Error('Telegram WebApp недоступний. Відкрийте додаток в Telegram.');
      }

      // Отримуємо дані користувача
      const userData = tg.initDataUnsafe.user;

      if (!userData) {
        throw new Error('Дані користувача не знайдено');
      }

      // Відправляємо на backend
      const response = await fetch(`${window.CONFIG?.API_URL || ''}/auth/telegram`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          initData: tg.initData,
          referralCode: tg.initDataUnsafe.start_param
        })
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Помилка авторизації');
      }

      // Зберігаємо токени
      const authData = {
        access_token: data.data.tokens.access_token,
        refresh_token: data.data.tokens.refresh_token,
        user: data.data.user,
        expires_at: new Date(Date.now() + (data.data.tokens.expires_in || 86400) * 1000).toISOString()
      };

      localStorage.setItem('auth', JSON.stringify(authData));

      // Оновлюємо стан
      this.setState({
        user: data.data.user,
        isAuthenticated: true,
        isLoading: false
      });

      // Викликаємо callback
      this.options.onSuccess(data.data);

      // Відправляємо глобальну подію
      window.dispatchEvent(new CustomEvent('auth:login', { detail: data.data }));

      // Показуємо успішну кнопку на 1.5 секунди
      setTimeout(() => {
        // Редіректимо на головну сторінку
        window.location.href = '/home';
      }, 1500);

    } catch (err) {
      console.error('Auth error:', err);
      this.setState({
        error: err.message,
        isLoading: false
      });
      this.options.onError(err);
    }
  }

  /**
   * Тестовий вхід для розробки
   */
  async handleDevLogin() {
    if (!window.CONFIG?.DEBUG) return;

    try {
      this.setState({ isLoading: true, error: null });

      // Емулюємо дані користувача
      const testUser = {
        id: '12345678',
        telegram_id: '12345678',
        first_name: 'Test',
        last_name: 'User',
        username: 'testuser',
        is_premium: false,
        balance: 100
      };

      // Емулюємо токени
      const authData = {
        access_token: 'test_token_' + Date.now(),
        refresh_token: 'test_refresh_' + Date.now(),
        user: testUser,
        expires_at: new Date(Date.now() + 86400 * 1000).toISOString()
      };

      localStorage.setItem('auth', JSON.stringify(authData));

      this.setState({
        user: testUser,
        isAuthenticated: true,
        isLoading: false
      });

      // Редіректимо на головну
      setTimeout(() => {
        window.location.href = '/home';
      }, 1000);

    } catch (err) {
      console.error('Dev login error:', err);
      this.setState({
        error: 'Помилка тестового входу',
        isLoading: false
      });
    }
  }

  /**
   * Оновити стан
   */
  setState(updates) {
    Object.assign(this.state, updates);
    if (this.element) {
      this.element.innerHTML = this.render();
    }
  }

  /**
   * Форматування ID користувача
   */
  formatUserId(id) {
    return String(id).padStart(9, '0');
  }

  /**
   * Отримати ініціали
   */
  getInitials(user) {
    const first = user.first_name?.[0] || '';
    const last = user.last_name?.[0] || '';
    return (first + last).toUpperCase() || '?';
  }

  /**
   * Знищити компонент
   */
  destroy() {
    if (window.telegramAuth === this) {
      delete window.telegramAuth;
    }
    if (this.element) {
      this.element.innerHTML = '';
    }
  }
}

/**
 * Hook для Telegram авторизації (для сумісності)
 */
export const useTelegramAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const authData = JSON.parse(localStorage.getItem('auth') || '{}');
      const token = authData.access_token;

      if (!token) {
        setIsAuthenticated(false);
        setIsLoading(false);
        return;
      }

      const response = await fetch(`${window.CONFIG?.API_URL || ''}/auth/verify`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();

      if (data.success && data.data.valid) {
        setIsAuthenticated(true);
        setUser(data.data.user);
      } else {
        setIsAuthenticated(false);
        localStorage.removeItem('auth');
      }
    } catch (err) {
      console.error('Auth check error:', err);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async () => {
    // Тригер Telegram авторизації
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.openTelegramLink(`https://t.me/${window.CONFIG?.BOT_USERNAME || 'TeleeBoost_bot'}?start=auth`);
    }
  };

  const logout = () => {
    localStorage.removeItem('auth');
    setIsAuthenticated(false);
    setUser(null);
    window.dispatchEvent(new CustomEvent('auth:logout'));
  };

  return {
    isAuthenticated,
    user,
    isLoading,
    login,
    logout,
    checkAuth
  };
};

export default TelegramAuth;