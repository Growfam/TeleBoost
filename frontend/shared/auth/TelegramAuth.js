// frontend/shared/auth/TelegramAuth.js
/**
 * Компонент Telegram авторизації для TeleBoost
 * Виправлена версія з правильним збереженням токенів
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
      isAuthenticated: false
    };

    this.element = null;
  }

  /**
   * Рендер компонента
   */
  render() {
    return `
      ${styles}
      <div class="telegram-auth-container">
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
      </div>
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

    // Рендеримо компонент
    this.element.innerHTML = this.render();

    // Зберігаємо посилання в window для onclick
    window.telegramAuth = this;

    // Ініціалізуємо Telegram Web App
    this.initTelegram();

    // Автологін якщо увімкнено
    if (this.options.autoLogin && window.Telegram?.WebApp?.initDataUnsafe?.user) {
      setTimeout(() => this.handleAuth(), 500);
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
        throw new Error('Telegram WebApp недоступний');
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

      // ВИПРАВЛЕННЯ: Зберігаємо токени правильно як об'єкт
      const authData = {
        access_token: data.data.tokens.access_token,
        refresh_token: data.data.tokens.refresh_token,
        user: data.data.user,
        expires_at: new Date(Date.now() + (data.data.tokens.expires_in || 86400) * 1000).toISOString()
      };

      // Зберігаємо в localStorage як об'єкт
      localStorage.setItem('auth', JSON.stringify(authData));

      // Видаляємо старі ключі якщо вони є
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');

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
        // Закриваємо або перенаправляємо
        if (tg.close) {
          tg.close();
        } else {
          window.location.href = '/';
        }
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
 * Hook для Telegram авторизації
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
      // ВИПРАВЛЕННЯ: Читаємо токен з правильного місця
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