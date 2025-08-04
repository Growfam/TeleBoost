// frontend/shared/auth/TelegramAuth.js
/**
 * Компонент автоматичної Telegram авторизації для TeleBoost
 * Production версія
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
  padding: 40px;
  position: relative;
  overflow: hidden;
  animation: fadeIn 0.6s ease-out;
  text-align: center;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.auth-icon-container {
  width: 80px;
  height: 80px;
  margin: 0 auto 24px;
  background: linear-gradient(135deg, #0088cc 0%, #0077bb 100%);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(0, 136, 204, 0.3);
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

.auth-title {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 12px;
}

.auth-subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.5;
  margin-bottom: 32px;
}

.auth-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top: 3px solid #0088cc;
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

.loading-text {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.7);
}

.auth-error {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  padding: 16px;
  margin-top: 24px;
  color: #fff;
  font-size: 14px;
}

.auth-success {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.success-icon {
  width: 64px;
  height: 64px;
  background: rgba(34, 197, 94, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #22c55e;
}

.success-text {
  font-size: 18px;
  font-weight: 600;
  color: #22c55e;
}

.redirect-text {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
}
</style>
`;

/**
 * Компонент автоматичної Telegram авторизації
 */
export class TelegramAuth {
  constructor(options = {}) {
    this.options = {
      onSuccess: options.onSuccess || (() => {}),
      onError: options.onError || (() => {})
    };

    this.state = {
      isLoading: true,
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
          <div class="auth-icon-container">
            ${getIcon('telegram', '', 40)}
          </div>
          
          <h2 class="auth-title">Автоматичний вхід</h2>
          <p class="auth-subtitle">Підключаємось до вашого Telegram акаунту...</p>
          
          ${this.renderContent()}
        </div>
      </div>
    `;
  }

  /**
   * Рендер контенту
   */
  renderContent() {
    if (this.state.error) {
      return `
        <div class="auth-error">
          ${this.state.error}
        </div>
      `;
    }

    if (this.state.isAuthenticated) {
      return `
        <div class="auth-success">
          <div class="success-icon">
            ${getIcon('success', '', 32)}
          </div>
          <div class="success-text">Успішно авторизовано!</div>
          <div class="redirect-text">Перенаправлення...</div>
        </div>
      `;
    }

    return `
      <div class="auth-loading">
        <div class="loading-spinner"></div>
        <div class="loading-text">Авторизація...</div>
      </div>
    `;
  }

  /**
   * Ініціалізація компонента
   */
  init(containerId) {
    this.element = document.getElementById(containerId);
    if (!this.element) {
      return;
    }

    // Рендеримо компонент
    this.element.innerHTML = this.render();

    // Автоматично починаємо авторизацію
    setTimeout(() => {
      this.performAutoAuth();
    }, 500);
  }

  /**
   * Автоматична авторизація
   */
  async performAutoAuth() {
    try {
      const tg = window.Telegram?.WebApp;

      if (!tg || !tg.initData) {
        throw new Error('Будь ласка, відкрийте додаток через Telegram');
      }

      // Отримуємо дані користувача
      const userData = tg.initDataUnsafe.user;
      if (!userData) {
        throw new Error('Не вдалося отримати дані користувача');
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

      // Глобальна подія
      window.dispatchEvent(new CustomEvent('auth:login', { detail: data.data }));

      // Перенаправляємо на головну через 1 секунду
      setTimeout(() => {
        window.location.href = '/home';
      }, 1000);

    } catch (err) {
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
   * Знищити компонент
   */
  destroy() {
    if (this.element) {
      this.element.innerHTML = '';
    }
  }
}

export default TelegramAuth;