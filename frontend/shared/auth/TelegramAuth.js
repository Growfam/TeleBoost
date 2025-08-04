// frontend/shared/auth/TelegramAuth.js
/**
 * Компонент автоматичної Telegram авторизації для TeleBoost
 * Production версія з використанням централізованого TelegramWebApp сервісу
 */

import { getIcon } from '../ui/svg.js';
import telegramWebApp from '../services/TelegramWebApp.js';

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

.browser-warning {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 16px;
  padding: 24px;
  text-align: center;
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
  color: #f59e0b;
}

.warning-title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 8px;
}

.warning-text {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
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

.debug-info {
  margin-top: 20px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  font-family: monospace;
  font-size: 12px;
  text-align: left;
  color: #0f0;
}

.debug-line {
  margin: 4px 0;
}

.retry-button {
  margin-top: 20px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #0088cc 0%, #0077bb 100%);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.retry-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 136, 204, 0.3);
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
      isAuthenticated: false,
      isTelegramWebApp: false,
      debugInfo: []
    };

    this.element = null;
    this.authAttempts = 0;
    this.maxAuthAttempts = 5;
  }

  /**
   * Додати debug інформацію
   */
  addDebugInfo(message) {
    this.state.debugInfo.push(`[${new Date().toISOString()}] ${message}`);
    console.log(`TelegramAuth: ${message}`);
  }

  /**
   * Рендер компонента
   */
  render() {
    return `
      ${styles}
      <div class="telegram-auth-container">
        ${this.state.isTelegramWebApp ? this.renderAuthCard() : this.renderBrowserWarning()}
        ${this.renderDebugInfo()}
      </div>
    `;
  }

  /**
   * Рендер debug інформації
   */
  renderDebugInfo() {
    if (!window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1')) {
      return '';
    }

    return `
      <div class="debug-info">
        <div><strong>Debug Information:</strong></div>
        ${this.state.debugInfo.map(line => `<div class="debug-line">${line}</div>`).join('')}
      </div>
    `;
  }

  /**
   * Рендер карточки авторизації
   */
  renderAuthCard() {
    return `
      <div class="telegram-auth-card">
        <div class="auth-icon-container">
          ${getIcon('telegram', '', 40)}
        </div>
        
        <h2 class="auth-title">Автоматичний вхід</h2>
        <p class="auth-subtitle">Підключаємось до вашого Telegram акаунту...</p>
        
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
          <a href="https://t.me/${window.CONFIG?.BOT_USERNAME || 'TeleeBoost_bot'}" 
             class="warning-link" 
             target="_blank">
            ${getIcon('telegram', '', 20)}
            <span>Відкрити в Telegram</span>
          </a>
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
        <button class="retry-button" onclick="window.location.reload()">
          Спробувати знову
        </button>
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
        <div class="loading-text">Авторизація... (спроба ${this.authAttempts}/${this.maxAuthAttempts})</div>
      </div>
    `;
  }

  /**
   * Ініціалізація компонента
   */
  async init(containerId) {
    this.element = document.getElementById(containerId);
    if (!this.element) {
      return;
    }

    // Перевіряємо чи це Telegram WebApp
    await this.checkTelegramWebApp();

    // Рендеримо компонент
    this.element.innerHTML = this.render();

    // Якщо це Telegram - починаємо авторизацію
    if (this.state.isTelegramWebApp) {
      this.startAuthProcess();
    }
  }

  /**
   * Перевірка Telegram WebApp
   */
  async checkTelegramWebApp() {
    // Чекаємо ініціалізації TelegramWebApp сервісу
    const initialized = await telegramWebApp.init();
    this.addDebugInfo(`TelegramWebApp service initialized: ${initialized}`);

    const tg = telegramWebApp.getTelegramWebApp();

    if (tg) {
      this.addDebugInfo(`Version: ${tg.version}`);
      this.addDebugInfo(`Platform: ${tg.platform}`);

      const initData = telegramWebApp.getInitData();
      const initDataUnsafe = telegramWebApp.getInitDataUnsafe();

      this.addDebugInfo(`initData exists: ${!!initData}`);
      this.addDebugInfo(`initData length: ${initData ? initData.length : 0}`);

      if (initDataUnsafe) {
        this.addDebugInfo(`initDataUnsafe keys: ${Object.keys(initDataUnsafe).join(', ')}`);
        if (initDataUnsafe.user) {
          this.addDebugInfo(`User ID: ${initDataUnsafe.user.id}`);
          this.addDebugInfo(`Username: ${initDataUnsafe.user.username}`);
        }
      }
    }

    this.state.isTelegramWebApp = telegramWebApp.isTelegramWebApp();
    this.addDebugInfo(`Is Telegram WebApp: ${this.state.isTelegramWebApp}`);
  }

  /**
   * Початок процесу авторизації
   */
  startAuthProcess() {
    // Спробуємо авторизуватись одразу
    this.performAutoAuth();
  }

  /**
   * Автоматична авторизація
   */
  async performAutoAuth() {
    try {
      this.authAttempts++;

      const initData = telegramWebApp.getInitData();

      if (!initData) {
        this.addDebugInfo(`Auth attempt ${this.authAttempts}: No initData`);

        if (this.authAttempts < this.maxAuthAttempts) {
          // Спробуємо ще раз через секунду
          setTimeout(() => this.performAutoAuth(), 1000);

          // Оновлюємо UI
          if (this.element) {
            this.element.innerHTML = this.render();
          }
          return;
        } else {
          throw new Error('Не вдалося отримати дані від Telegram. Спробуйте перезапустити додаток.');
        }
      }

      this.addDebugInfo('Sending auth request to backend...');

      // Відправляємо на backend
      const response = await fetch(`${window.CONFIG?.API_URL || ''}/auth/telegram`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          initData: initData,
          referralCode: telegramWebApp.getInitDataUnsafe()?.start_param
        })
      });

      const data = await response.json();
      this.addDebugInfo(`Backend response: ${response.status} ${data.success ? 'success' : 'error'}`);

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
      this.addDebugInfo('Auth data saved to localStorage');

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
      this.addDebugInfo(`Auth error: ${err.message}`);

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