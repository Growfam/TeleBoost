// frontend/shared/auth/AuthGuard.js
/**
 * AuthGuard компонент для TeleBoost
 * Переписаний з React на Vanilla JS
 */

import { getIcon } from '../ui/svg.js';

// SVG Icons
const ShieldIcon = (size = 24, color = '#a855f7') => `
  <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none">
    <path
      d="M12 2L4 7V12C4 16.5 6.84 20.74 11 21.92C11.35 22.03 11.65 22.03 12 21.92C16.16 20.74 20 16.5 20 12V7L12 2Z"
      fill="${color}"
      fill-opacity="0.1"
      stroke="${color}"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <path
      d="M9 12L11 14L15 10"
      stroke="${color}"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
`;

const LockIcon = (size = 20, color = '#fff') => `
  <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none">
    <rect x="5" y="11" width="14" height="10" rx="2" fill="${color}" fill-opacity="0.1" stroke="${color}" stroke-width="2"/>
    <path d="M7 11V7C7 4.23858 9.23858 2 12 2C14.7614 2 17 4.23858 17 7V11" stroke="${color}" stroke-width="2" stroke-linecap="round"/>
    <circle cx="12" cy="16" r="1" fill="${color}"/>
  </svg>
`;

const AlertIcon = (size = 20, color = '#ef4444') => `
  <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none">
    <path
      d="M12 2L2 20H22L12 2Z"
      fill="${color}"
      fill-opacity="0.1"
      stroke="${color}"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <path d="M12 9V13" stroke="${color}" stroke-width="2" stroke-linecap="round"/>
    <circle cx="12" cy="17" r="0.5" fill="${color}" stroke="${color}"/>
  </svg>
`;

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
    this.particles = this.generateParticles();
  }

  /**
   * Генерація частинок для фону
   */
  generateParticles() {
    return Array.from({ length: 5 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      delay: Math.random() * 10,
      duration: 10 + Math.random() * 10,
    }));
  }

  /**
   * Рендер компонента
   */
  render() {
    const particles = this.particles.map(p => `
      <div class="auth-particle" 
           style="left: ${p.left}%; 
                  animation-delay: ${p.delay}s; 
                  animation-duration: ${p.duration}s;">
      </div>
    `).join('');

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
        <div class="auth-particles">${particles}</div>
        
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
      return AlertIcon(40);
    } else if (this.options.isLoading) {
      return ShieldIcon(40);
    } else {
      return LockIcon(40);
    }
  }

  /**
   * Рендер помилки
   */
  renderError() {
    return `
      <h2 class="auth-title">Помилка доступу</h2>
      <div class="auth-error-container">
        ${AlertIcon(20)}
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
    // Створюємо елемент
    const div = document.createElement('div');
    div.innerHTML = this.render();
    this.element = div.firstElementChild;

    // Додаємо в DOM
    document.body.appendChild(this.element);

    // Додаємо обробники
    this.attachEventListeners();

    // Анімація появи з затримкою для плавності
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

      // Чекаємо завершення анімації
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
    // Retry button
    const retryBtn = this.element?.querySelector('#retry-button');
    if (retryBtn) {
      retryBtn.addEventListener('click', () => {
        if (this.options.onRetry) {
          this.options.onRetry();
        }
      });

      this.addButtonHover(retryBtn);
    }

    // Login button
    const loginBtn = this.element?.querySelector('#login-button');
    if (loginBtn) {
      loginBtn.addEventListener('click', () => {
        window.location.href = this.options.redirectTo;
      });

      this.addButtonHover(loginBtn);
    }
  }

  /**
   * Додати hover ефект для кнопки
   */
  addButtonHover(button) {
    button.addEventListener('mouseenter', () => {
      button.classList.add('button-hover');
    });
    button.addEventListener('mouseleave', () => {
      button.classList.remove('button-hover');
    });
  }

  /**
   * Оновити опції
   */
  update(options) {
    Object.assign(this.options, options);

    if (this.element) {
      // Перерендеримо
      this.element.innerHTML = this.render();
      this.attachEventListeners();
    }
  }

  /**
   * Статичний метод для перевірки авторизації
   */
  static async check() {
    try {
      // Перевіряємо localStorage
      const authData = JSON.parse(localStorage.getItem('auth') || '{}');
      const token = authData.access_token;

      if (!token) {
        return { isAuthenticated: false, user: null };
      }

      // Перевіряємо чи не прострочений токен
      if (authData.expires_at) {
        const expiresAt = new Date(authData.expires_at);
        if (expiresAt <= new Date()) {
          console.log('Token expired, clearing auth');
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
        // Оновлюємо дані користувача
        authData.user = data.data.user;
        localStorage.setItem('auth', JSON.stringify(authData));

        return { isAuthenticated: true, user: data.data.user };
      }

      // Токен невалідний - очищаємо
      localStorage.removeItem('auth');
      return { isAuthenticated: false, user: null };

    } catch (error) {
      console.error('Auth check failed:', error);
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

/**
 * Middleware функція для захисту сторінок
 */
export async function requireAuth() {
  const authGuard = new AuthGuard({
    isLoading: true
  });

  // Показуємо loader
  authGuard.show();

  try {
    const { isAuthenticated, user } = await AuthGuard.check();

    if (isAuthenticated) {
      // Ховаємо guard і повертаємо користувача
      authGuard.hide();
      return { success: true, user };
    } else {
      // Показуємо unauthorized стан
      authGuard.update({
        isLoading: false,
        isAuthenticated: false
      });
      return { success: false, user: null };
    }
  } catch (error) {
    // Показуємо помилку
    authGuard.update({
      isLoading: false,
      error: 'Не вдалося перевірити авторизацію',
      onRetry: () => {
        window.location.reload();
      }
    });
    return { success: false, user: null, error };
  }
}

/**
 * Декоратор для захисту класів
 */
export function withAuth(ComponentClass) {
  return class extends ComponentClass {
    async init() {
      const { success, user } = await requireAuth();

      if (success) {
        this.user = user;
        if (super.init) {
          await super.init();
        }
      }
      // Якщо не авторизований - AuthGuard вже показаний
    }
  };
}

// Стилі компонента
const styles = `
<style>
/* Animations */
@keyframes float {
  0% {
    transform: translateY(100vh) translateX(0);
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    transform: translateY(-100vh) translateX(100px);
    opacity: 0;
  }
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

@keyframes fadeOut {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.8;
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
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

@keyframes progress {
  from {
    width: 0%;
  }
  to {
    width: 100%;
  }
}

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

/* Particles */
.auth-particles {
  position: absolute;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.auth-particle {
  position: absolute;
  width: 4px;
  height: 4px;
  background: rgba(168, 85, 247, 0.4);
  border-radius: 50%;
  animation: float 15s infinite linear;
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

/* Progress bar */
.auth-progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  background: linear-gradient(90deg, #a855f7, #ec4899);
  animation: progress 2s ease-out;
  border-radius: 0 0 24px 24px;
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

.auth-icon-glow {
  position: absolute;
  inset: -20px;
  background: radial-gradient(circle, rgba(168, 85, 247, 0.2) 0%, transparent 70%);
  border-radius: 50%;
  animation: rotate 10s linear infinite;
}

/* Typography */
.auth-title {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  text-align: center;
  margin-bottom: 12px;
  background: linear-gradient(135deg, #fff 0%, #a78bfa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
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

/* Error */
.auth-error-container {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.auth-error-text {
  color: #fff;
  font-size: 14px;
  flex: 1;
  margin: 0;
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
  position: relative;
  overflow: hidden;
}

.auth-button.button-hover {
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