// frontend/shared/auth/TelegramAuth.js
/**
 * Компонент авторизації через Telegram Web App
 * ВИПРАВЛЕНО: Узгоджено збереження токенів з APIClient
 */

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

.user-info {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 24px;
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

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
</style>
`;

/**
 * Компонент Telegram авторизації
 */
export default class TelegramAuth {
  constructor(options = {}) {
    this.onSuccess = options.onSuccess || (() => {});
    this.onError = options.onError || (() => {});
    this.botUsername = options.botUsername || 'TeleeBoost_bot';
    this.buttonText = options.buttonText || 'Увійти через Telegram';
    this.showUserInfo = options.showUserInfo !== false;
    this.autoLogin = options.autoLogin !== false;

    this.state = {
      isLoading: false,
      error: null,
      user: null,
      isAuthenticated: false
    };

    // Додаємо стилі
    if (!document.getElementById('telegram-auth-styles')) {
      const styleElement = document.createElement('div');
      styleElement.id = 'telegram-auth-styles';
      styleElement.innerHTML = styles;
      document.head.appendChild(styleElement);
    }
  }

  /**
   * Рендер компонента
   */
  render() {
    return `
      <div class="telegram-auth-container">
        <div class="telegram-auth-card">
          <div class="auth-glow"></div>
          
          ${this.renderHeader()}
          ${this.state.user && this.showUserInfo ? this.renderUserInfo() : ''}
          ${this.renderButton()}
          ${this.state.error ? this.renderError() : ''}
        </div>
      </div>
    `;
  }

  renderHeader() {
    return `
      <div class="auth-header">
        <div class="auth-icon-container">
          ${this.getTelegramIcon()}
        </div>
        <h2 class="auth-title">
          ${this.state.isAuthenticated ? 'Вітаємо!' : 'Вхід через Telegram'}
        </h2>
        <p class="auth-subtitle">
          ${this.state.isAuthenticated 
            ? 'Ви успішно увійшли в систему' 
            : 'Безпечна авторизація через Telegram'}
        </p>
      </div>
    `;
  }

  renderUserInfo() {
    const user = this.state.user;
    return `
      <div class="user-info">
        <div class="user-row">
          <div class="user-avatar">
            ${this.getInitials(user)}
          </div>
          <div class="user-details">
            <div style="display: flex; align-items: center; gap: 8px;">
              <div class="user-name">
                ${user.first_name} ${user.last_name || ''}
              </div>
              ${user.is_premium ? '<div class="premium-badge">⭐ Premium</div>' : ''}
            </div>
            <div class="user-id">
              ${this.formatUserId(user.telegram_id)}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  renderButton() {
    if (this.state.isAuthenticated) {
      return `
        <button class="auth-button success">
          ${this.getCheckIcon()}
          <span>Авторизовано</span>
        </button>
      `;
    }

    return `
      <button class="auth-button" id="telegram-auth-btn" ${this.state.isLoading ? 'disabled' : ''}>
        ${this.state.isLoading ? '<div class="spinner"></div>' : this.getTelegramIcon(20)}
        <span>${this.state.isLoading ? 'Авторизація...' : this.buttonText}</span>
      </button>
    `;
  }

  renderError() {
    return `<div class="auth-error">${this.state.error}</div>`;
  }

  /**
   * Ініціалізація після рендеру
   */
  init() {
    // Ініціалізуємо Telegram Web App
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;
      tg.expand();
      tg.setHeaderColor('#1a0033');
      tg.setBackgroundColor('#000000');
      tg.ready();

      // Автоматичний вхід якщо включено
      if (this.autoLogin && tg.initDataUnsafe?.user) {
        this.handleAuth();
      }
    }

    // Додаємо обробник кнопки
    const authBtn = document.getElementById('telegram-auth-btn');
    if (authBtn) {
      authBtn.addEventListener('click', () => this.handleAuth());
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

      const userData = tg.initDataUnsafe.user;
      if (!userData) {
        throw new Error('Дані користувача не знайдено');
      }

      // Відправляємо на сервер
      const response = await fetch('/api/auth/telegram', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          initData: tg.initData,
          referralCode: tg.initDataUnsafe.start_param,
        }),
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Помилка авторизації');
      }

      // ВИПРАВЛЕННЯ: Зберігаємо токени правильно як об'єкт
      const authData = {
        access_token: data.data.tokens.access_token,
        refresh_token: data.data.tokens.refresh_token,
        token_type: data.data.tokens.token_type,
        expires_in: data.data.tokens.expires_in,
        expires_at: new Date(Date.now() + data.data.tokens.expires_in * 1000).toISOString(),
        user: data.data.user
      };

      // Зберігаємо як єдиний об'єкт
      localStorage.setItem('auth', JSON.stringify(authData));

      // Видаляємо старі ключі якщо вони існують
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');

      // Оновлюємо стан
      this.setState({
        user: data.data.user,
        isAuthenticated: true,
        isLoading: false
      });

      // Викликаємо callback
      this.onSuccess(data.data);

      // Emit подію для інших компонентів
      window.dispatchEvent(new CustomEvent('auth:login', { detail: data.data }));

      // Показуємо успішну кнопку і потім закриваємо/редіректимо
      setTimeout(() => {
        if (tg.close) {
          tg.close();
        } else {
          window.location.href = '/';
        }
      }, 1500);

    } catch (err) {
      this.setState({ 
        error: err.message, 
        isLoading: false 
      });
      this.onError(err);
    }
  }

  /**
   * Оновити стан і перерендерити
   */
  setState(newState) {
    Object.assign(this.state, newState);
    this.rerender();
  }

  /**
   * Перерендерити компонент
   */
  rerender() {
    const container = document.querySelector('.telegram-auth-container');
    if (container) {
      container.outerHTML = this.render();
      this.init();
    }
  }

  /**
   * Допоміжні методи
   */
  formatUserId(id) {
    return `#${String(id).padStart(9, '0')}`;
  }

  getInitials(user) {
    const first = user.first_name?.[0] || '';
    const last = user.last_name?.[0] || '';
    return (first + last).toUpperCase() || '?';
  }

  getTelegramIcon(size = 32) {
    return `
      <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none">
        <path d="M21.198 2.433a2.242 2.242 0 0 0-1.022.215l-8.609 3.33c-2.068.8-4.133 1.598-5.724 2.21a405.15 405.15 0 0 1-2.849 1.09c-.42.147-.99.332-1.473.901-.728.968.193 1.798.919 2.112 1.058.46 2.06.745 3.059 1.122 1.074.409 2.156.842 3.23 1.295l-.138-.03c.265.624.535 1.239.804 1.858.382.883.761 1.769 1.137 2.663.19.448.521 1.05 1.08 1.246.885.32 1.694-.244 2.122-.715l1.358-1.493c.858.64 1.708 1.271 2.558 1.921l.033.025c1.153.865 1.805 1.354 2.495 1.592.728.25 1.361.151 1.88-.253.506-.395.748-.987.818-1.486.308-2.17.63-4.335.919-6.507.316-2.378.63-4.764.867-7.158.094-.952.187-1.912.272-2.875.046-.523.153-1.308-.327-1.83a1.743 1.743 0 0 0-.965-.465z" fill="#fff"/>
      </svg>
    `;
  }

  getCheckIcon(size = 20) {
    return `
      <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none">
        <path d="M20 6L9 17L4 12" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    `;
  }
}

/**
 * Hook для використання Telegram Auth в React-like компонентах
 */
export function useTelegramAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      // ВИПРАВЛЕННЯ: Читаємо auth об'єкт правильно
      const authData = localStorage.getItem('auth');
      
      if (!authData) {
        setIsAuthenticated(false);
        setIsLoading(false);
        return;
      }

      const auth = JSON.parse(authData);
      const token = auth.access_token;

      if (!token) {
        setIsAuthenticated(false);
        setIsLoading(false);
        return;
      }

      // Перевіряємо чи токен не прострочений
      if (auth.expires_at && new Date(auth.expires_at) < new Date()) {
        localStorage.removeItem('auth');
        setIsAuthenticated(false);
        setIsLoading(false);
        return;
      }

      const response = await fetch('/api/auth/verify', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();

      if (data.success && data.data.valid) {
        setIsAuthenticated(true);
        setUser(data.data.user || auth.user);
      } else {
        setIsAuthenticated(false);
        localStorage.removeItem('auth');
      }
    } catch (err) {
      console.error('Auth check failed:', err);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async () => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.openTelegramLink(`https://t.me/${botUsername}?start=auth`);
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
    checkAuth,
  };
}

/**
 * HOC для захисту компонентів
 */
export function withAuth(Component) {
  return function AuthenticatedComponent(props) {
    const { isAuthenticated, isLoading, user } = useTelegramAuth();

    if (isLoading) {
      return `
        <div class="auth-loading">
          <div class="spinner"></div>
          <p>Перевірка авторизації...</p>
        </div>
      `;
    }

    if (!isAuthenticated) {
      const auth = new TelegramAuth({
        onSuccess: () => window.location.reload()
      });
      return auth.render();
    }

    return Component({ ...props, user });
  };
}

/**
 * Guard для перевірки авторизації
 */
export class AuthGuard {
  static async check() {
    const authData = localStorage.getItem('auth');
    
    if (!authData) {
      return { isAuthenticated: false, user: null };
    }

    try {
      const auth = JSON.parse(authData);
      
      // Перевіряємо термін дії
      if (auth.expires_at && new Date(auth.expires_at) < new Date()) {
        localStorage.removeItem('auth');
        return { isAuthenticated: false, user: null };
      }

      return { 
        isAuthenticated: true, 
        user: auth.user,
        token: auth.access_token 
      };
    } catch (err) {
      console.error('Failed to parse auth data:', err);
      return { isAuthenticated: false, user: null };
    }
  }

  static requireAuth() {
    const auth = this.check();
    if (!auth.isAuthenticated) {
      window.location.href = '/login';
      return false;
    }
    return true;
  }
}