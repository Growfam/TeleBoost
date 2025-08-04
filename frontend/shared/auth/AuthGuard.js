// frontend/shared/auth/AuthGuard.js
/**
 * AuthGuard компонент для TeleBoost
 * Production версія
 */

import { getIcon } from '../ui/svg.js';

/**
 * AuthGuard клас для захисту сторінок
 */
export default class AuthGuard {
  constructor(options = {}) {
    this.options = {
      isAuthenticated: options.isAuthenticated || false,
      isLoading: options.isLoading || false,
      error: options.error || null,
      onRetry: options.onRetry || null,
      redirectTo: options.redirectTo || '/login'
    };

    this.element = null;
  }

  /**
   * Рендер компонента
   */
  render() {
    let content = '';

    if (this.options.error) {
      content = this.renderError();
    } else if (this.options.isLoading) {
      content = this.renderLoading();
    } else {
      content = this.renderUnauthorized();
    }

    return `
      <div class="auth-guard-container">
        <div class="auth-card">
          ${this.options.isLoading ? '<div class="auth-progress-bar"></div>' : ''}
          
          <div class="auth-icon-container">
            <div class="auth-icon-glow"></div>
            ${this.getIcon()}
          </div>
          
          ${content}
        </div>
      </div>
    `;
  }

  /**
   * Отримати іконку
   */
  getIcon() {
    if (this.options.error) {
      return getIcon('error', '', 40);
    } else if (this.options.isLoading) {
      return getIcon('loading', 'animate-spin', 40);
    } else {
      return getIcon('close', '', 40);
    }
  }

  /**
   * Рендер помилки
   */
  renderError() {
    return `
      <h2 class="auth-title">Помилка доступу</h2>
      <div class="auth-error-container">
        <p class="auth-error-text">${this.options.error}</p>
      </div>
      ${this.options.onRetry ? `
        <button class="auth-button" id="retry-button">
          Спробувати знову
        </button>
      ` : ''}
    `;
  }

  /**
   * Рендер завантаження
   */
  renderLoading() {
    return `
      <h2 class="auth-title">Перевірка доступу</h2>
      <p class="auth-subtitle">
        Перевіряємо ваші дані авторизації...
      </p>
      <div class="auth-loader"></div>
    `;
  }

  /**
   * Рендер неавторизованого стану
   */
  renderUnauthorized() {
    return `
      <h2 class="auth-title">Потрібна авторизація</h2>
      <p class="auth-subtitle">
        Будь ласка, увійдіть для доступу до цієї сторінки
      </p>
      <button class="auth-button" id="login-button">
        Перейти до входу
      </button>
    `;
  }

  /**
   * Показати AuthGuard
   */
  show() {
    const div = document.createElement('div');
    div.innerHTML = this.render();
    this.element = div.firstElementChild;

    document.body.appendChild(this.element);
    this.attachEventListeners();

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        this.element?.classList.add('auth-guard-active');
      });
    });
  }

  /**
   * Сховати AuthGuard
   */
  hide() {
    if (this.element) {
      this.element.classList.add('auth-guard-hiding');
      this.element.classList.remove('auth-guard-active');

      setTimeout(() => {
        this.element?.remove();
        this.element = null;
      }, 300);
    }
  }

  /**
   * Додати обробники подій
   */
  attachEventListeners() {
    const retryBtn = this.element?.querySelector('#retry-button');
    if (retryBtn) {
      retryBtn.addEventListener('click', () => {
        if (this.options.onRetry) {
          this.options.onRetry();
        }
      });
    }

    const loginBtn = this.element?.querySelector('#login-button');
    if (loginBtn) {
      loginBtn.addEventListener('click', () => {
        window.location.href = this.options.redirectTo;
      });
    }
  }

  /**
   * Оновити опції
   */
  update(options) {
    Object.assign(this.options, options);

    if (this.element) {
      this.element.innerHTML = this.render();
      this.attachEventListeners();
    }
  }

  /**
   * Статичний метод для перевірки авторизації
   */
  static async check() {
    try {
      const authData = JSON.parse(localStorage.getItem('auth') || '{}');
      const token = authData.access_token;

      if (!token) {
        return { isAuthenticated: false, user: null };
      }

      // Перевіряємо термін дії токена
      if (authData.expires_at) {
        const expiresAt = new Date(authData.expires_at);
        if (expiresAt <= new Date()) {
          localStorage.removeItem('auth');
          return { isAuthenticated: false, user: null };
        }
      }

      // Якщо є збережений користувач - повертаємо його
      if (authData.user) {
        return { isAuthenticated: true, user: authData.user };
      }

      // Інакше верифікуємо токен з API
      const response = await fetch(`${window.CONFIG?.API_URL || ''}/auth/verify`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();

      if (data.success && data.data?.valid && data.data?.user) {
        authData.user = data.data.user;
        localStorage.setItem('auth', JSON.stringify(authData));
        return { isAuthenticated: true, user: data.data.user };
      }

      localStorage.removeItem('auth');
      return { isAuthenticated: false, user: null };

    } catch (error) {
      return { isAuthenticated: false, user: null };
    }
  }

  /**
   * Статичний метод для редіректу на логін
   */
  static redirectToLogin() {
    window.location.href = '/login';
  }
}

// Стилі компонента
const styles = `
<style>
/* Container */
.auth-guard-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #000 0%, #1a0033 50%, #000 100%);
  z-index: 9999;
  opacity: 0;
  transition: opacity 0.3s ease-out;
}

.auth-guard-container.auth-guard-active {
  opacity: 1;
}

.auth-guard-container.auth-guard-hiding {
  opacity: 0;
  transition: opacity 0.3s ease-in;
}

/* Card */
.auth-card {
  width: 90%;
  max-width: 400px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  position: relative;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  animation: slideUp 0.6s ease-out;
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

/* Progress bar */
.auth-progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  background: linear-gradient(90deg, #a855f7, #ec4899);
  animation: progress 2s ease-out;
  border-radius: 0 0 24px 24px;
  width: 100%;
}

@keyframes progress {
  from {
    width: 0%;
  }
  to {
    width: 100%;
  }
}

/* Icon */
.auth-icon-container {
  width: 80px;
  height: 80px;
  margin: 0 auto 24px;
  background: rgba(168, 85, 247, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

.auth-icon-glow {
  position: absolute;
  inset: -20px;
  background: radial-gradient(circle, rgba(168, 85, 247, 0.2) 0%, transparent 70%);
  border-radius: 50%;
}

/* Typography */
.auth-title {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  text-align: center;
  margin-bottom: 12px;
}

.auth-subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.7);
  text-align: center;
  margin-bottom: 32px;
  line-height: 1.5;
}

/* Loader */
.auth-loader {
  width: 40px;
  height: 40px;
  margin: 0 auto;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top: 3px solid #a855f7;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Error */
.auth-error-container {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 24px;
}

.auth-error-text {
  color: #fff;
  font-size: 14px;
  margin: 0;
  text-align: center;
}

/* Button */
.auth-button {
  width: 100%;
  padding: 14px 24px;
  background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
  border: none;
  border-radius: 12px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.auth-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(168, 85, 247, 0.4);
}

.auth-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
`;

// Додаємо стилі при завантаженні
if (!document.getElementById('auth-guard-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'auth-guard-styles';
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}