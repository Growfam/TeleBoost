// frontend/shared/components/Toast.js
/**
 * Toast компонент для TeleBoost
 * Переписаний з React на Vanilla JS
 */

// Toast types
const TOAST_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
  LOADING: 'loading'
};

// SVG Icons для toast
const ToastIcons = {
  success: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path d="M10 0C4.48 0 0 4.48 0 10s4.48 10 10 10 10-4.48 10-10S15.52 0 10 0zm-1 15l-5-5 1.41-1.41L9 12.17l7.59-7.59L18 6l-9 9z" fill="#30D158"/>
  </svg>`,

  error: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path d="M10 0C4.48 0 0 4.48 0 10s4.48 10 10 10 10-4.48 10-10S15.52 0 10 0zm1 15H9v-2h2v2zm0-4H9V5h2v6z" fill="#FF3B30"/>
  </svg>`,

  warning: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path d="M10 2a8 8 0 100 16 8 8 0 000-16zm1 11h-2v-2h2v2zm0-4h-2V5h2v4z" fill="#FF9500"/>
  </svg>`,

  info: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path d="M10 0C4.5 0 0 4.5 0 10s4.5 10 10 10 10-4.5 10-10S15.5 0 10 0zm1 15h-2v-6h2v6zm0-8h-2V5h2v2z" fill="#007AFF"/>
  </svg>`,

  loading: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" class="toast-spinner">
    <path d="M10 0C4.5 0 0 4.5 0 10h2c0-4.4 3.6-8 8-8V0z" fill="#007AFF"/>
  </svg>`
};

/**
 * Toast клас для одного повідомлення
 */
class Toast {
  constructor(options = {}) {
    this.id = options.id || Date.now() + Math.random();
    this.message = options.message || '';
    this.type = options.type || TOAST_TYPES.INFO;
    this.duration = options.duration || 3000;
    this.onClose = options.onClose || (() => {});

    this.element = null;
    this.progressInterval = null;
    this.progress = 100;
    this.removing = false;
  }

  /**
   * Рендер toast
   */
  render() {
    return `
      <div class="toast toast-${this.type} toast-entering" role="alert" aria-live="polite">
        <div class="toast-icon">
          ${ToastIcons[this.type] || ToastIcons.info}
        </div>
        <p class="toast-message">${this.message}</p>
        
        ${this.duration > 0 && this.type !== TOAST_TYPES.LOADING ? `
          <div class="toast-progress-bar" style="width: ${this.progress}%"></div>
        ` : ''}
      </div>
    `;
  }

  /**
   * Показати toast
   */
  show(container) {
    // Створюємо елемент
    const div = document.createElement('div');
    div.innerHTML = this.render();
    this.element = div.firstElementChild;

    // Додаємо click handler
    this.element.addEventListener('click', () => this.close());

    // Додаємо в контейнер
    container.appendChild(this.element);

    // Запускаємо прогрес якщо потрібно
    if (this.duration > 0 && this.type !== TOAST_TYPES.LOADING) {
      this.startProgress();

      // Автоматично закриваємо
      setTimeout(() => this.close(), this.duration);
    }
  }

  /**
   * Запустити прогрес бар
   */
  startProgress() {
    const interval = 100; // Оновлюємо кожні 100ms
    const decrement = (interval / this.duration) * 100;

    this.progressInterval = setInterval(() => {
      this.progress -= decrement;

      if (this.progress <= 0) {
        clearInterval(this.progressInterval);
        this.progress = 0;
      }

      this.updateProgress();
    }, interval);
  }

  /**
   * Оновити прогрес бар
   */
  updateProgress() {
    if (this.element) {
      const progressBar = this.element.querySelector('.toast-progress-bar');
      if (progressBar) {
        progressBar.style.width = `${this.progress}%`;
      }
    }
  }

  /**
   * Закрити toast
   */
  close() {
    if (this.removing) return;
    this.removing = true;

    // Зупиняємо прогрес
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
    }

    // Додаємо клас виходу
    if (this.element) {
      this.element.classList.remove('toast-entering');
      this.element.classList.add('toast-exiting');

      // Видаляємо після анімації
      setTimeout(() => {
        if (this.element) {
          this.element.remove();
          this.element = null;
        }
        this.onClose(this.id);
      }, 400);
    }
  }

  /**
   * Оновити toast
   */
  update(updates) {
    if (updates.message && this.element) {
      const messageEl = this.element.querySelector('.toast-message');
      if (messageEl) {
        messageEl.textContent = updates.message;
      }
    }

    if (updates.type && this.element) {
      this.element.classList.remove(`toast-${this.type}`);
      this.element.classList.add(`toast-${updates.type}`);
      this.type = updates.type;

      // Оновлюємо іконку
      const iconEl = this.element.querySelector('.toast-icon');
      if (iconEl) {
        iconEl.innerHTML = ToastIcons[updates.type] || ToastIcons.info;
      }
    }
  }
}

/**
 * ToastProvider - керує всіма toast повідомленнями
 */
export class ToastProvider {
  constructor(options = {}) {
    this.options = {
      position: options.position || 'top',
      maxToasts: options.maxToasts || 3
    };

    this.toasts = new Map();
    this.container = null;

    // Глобальний інстанс
    if (!window.toastProvider) {
      window.toastProvider = this;
    }
  }

  /**
   * Ініціалізація провайдера
   */
  init() {
    // Створюємо контейнер
    this.container = document.createElement('div');
    this.container.className = `toast-container toast-position-${this.options.position}`;
    this.container.id = 'toast-container';
    document.body.appendChild(this.container);

    // Додаємо глобальну функцію
    window.showToast = (message, type = 'info', duration = 3000) => {
      return this.addToast(message, type, duration);
    };

    // Експортуємо методи
    window.toast = {
      success: (message, duration) => this.success(message, duration),
      error: (message, duration) => this.error(message, duration),
      warning: (message, duration) => this.warning(message, duration),
      info: (message, duration) => this.info(message, duration),
      loading: (message) => this.loading(message),
      dismiss: (id) => this.removeToast(id),
      dismissAll: () => this.removeAllToasts()
    };
  }

  /**
   * Додати toast
   */
  addToast(message, type = TOAST_TYPES.INFO, duration = 3000) {
    // Обмежуємо кількість toast
    const currentToasts = Array.from(this.toasts.values());
    if (currentToasts.length >= this.options.maxToasts) {
      // Видаляємо найстаріший
      const oldestToast = currentToasts[0];
      oldestToast.close();
    }

    // Створюємо новий toast
    const toast = new Toast({
      message,
      type,
      duration,
      onClose: (id) => this.toasts.delete(id)
    });

    // Зберігаємо
    this.toasts.set(toast.id, toast);

    // Показуємо
    toast.show(this.container);

    return toast.id;
  }

  /**
   * Видалити toast
   */
  removeToast(id) {
    const toast = this.toasts.get(id);
    if (toast) {
      toast.close();
    }
  }

  /**
   * Видалити всі toasts
   */
  removeAllToasts() {
    this.toasts.forEach(toast => toast.close());
  }

  /**
   * Оновити toast
   */
  updateToast(id, updates) {
    const toast = this.toasts.get(id);
    if (toast) {
      toast.update(updates);
    }
  }

  // Helper методи
  success(message, duration) {
    return this.addToast(message, TOAST_TYPES.SUCCESS, duration);
  }

  error(message, duration) {
    return this.addToast(message, TOAST_TYPES.ERROR, duration);
  }

  warning(message, duration) {
    return this.addToast(message, TOAST_TYPES.WARNING, duration);
  }

  info(message, duration) {
    return this.addToast(message, TOAST_TYPES.INFO, duration);
  }

  loading(message) {
    return this.addToast(message, TOAST_TYPES.LOADING, 0);
  }
}

/**
 * Hook для використання toast (для сумісності)
 */
export const useToast = () => {
  if (!window.toastProvider) {
    throw new Error('ToastProvider must be initialized first');
  }

  return {
    toasts: Array.from(window.toastProvider.toasts.values()),
    addToast: window.toastProvider.addToast.bind(window.toastProvider),
    removeToast: window.toastProvider.removeToast.bind(window.toastProvider),
    removeAllToasts: window.toastProvider.removeAllToasts.bind(window.toastProvider),
    updateToast: window.toastProvider.updateToast.bind(window.toastProvider),
    success: window.toastProvider.success.bind(window.toastProvider),
    error: window.toastProvider.error.bind(window.toastProvider),
    warning: window.toastProvider.warning.bind(window.toastProvider),
    info: window.toastProvider.info.bind(window.toastProvider),
    loading: window.toastProvider.loading.bind(window.toastProvider)
  };
};

// Стилі для компонента
const styles = `
<style>
/* Animations */
@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-100%);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideUp {
  from {
    opacity: 1;
    transform: translateY(0);
  }
  to {
    opacity: 0;
    transform: translateY(-100%);
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

.toast-spinner {
  animation: spin 1s linear infinite;
}

/* Container */
.toast-container {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  pointer-events: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  max-width: 430px;
  width: 100%;
  padding: 0 20px;
}

.toast-position-top {
  top: 20px;
}

.toast-position-bottom {
  bottom: 20px;
}

/* Toast */
.toast {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
  pointer-events: all;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.toast-entering {
  animation: slideDown 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.toast-exiting {
  animation: slideUp 0.4s cubic-bezier(0.4, 0, 1, 1) forwards;
}

/* Icons */
.toast-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

/* Message */
.toast-message {
  font-size: 15px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
  letter-spacing: -0.01em;
  margin: 0;
  line-height: 1.4;
}

/* Progress bar */
.toast-progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 0 0 16px 16px;
  transition: width linear 100ms;
}

/* Type specific styles */
.toast-success {
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.2);
}

.toast-error {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.2);
}

.toast-warning {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.2);
}

.toast-info {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.2);
}

.toast-loading {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.2);
}

/* Hover effect */
.toast:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 30px rgba(0, 0, 0, 0.15);
}
</style>
`;

// Додаємо стилі при завантаженні
if (!document.getElementById('toast-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'toast-styles';
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}

export default Toast;