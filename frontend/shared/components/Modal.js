// frontend/shared/components/Modal.js
/**
 * Modal компонент для TeleBoost
 * Переписаний з React на Vanilla JS
 */

export default class Modal {
  constructor(options = {}) {
    this.options = {
      isOpen: options.isOpen || false,
      onClose: options.onClose || (() => {}),
      title: options.title || '',
      content: options.content || '',
      footer: options.footer || null,
      size: options.size || 'medium', // small, medium, large
      showCloseButton: options.showCloseButton !== false,
      closeOnOverlay: options.closeOnOverlay !== false,
      closeOnEsc: options.closeOnEsc !== false,
      className: options.className || '',
      preventScroll: options.preventScroll !== false,
      onOpen: options.onOpen || (() => {}),
      onAfterOpen: options.onAfterOpen || (() => {}),
      onAfterClose: options.onAfterClose || (() => {})
    };

    this.element = null;
    this.previousActiveElement = null;
    this.isActive = false;
    this.isClosing = false;
    this.escHandler = null;
  }

  /**
   * Рендер модального вікна
   */
  render() {
    const sizeClass = `modal-${this.options.size}`;

    return `
      <div class="modal-overlay ${this.options.className}" id="modal-overlay">
        <div class="modal ${sizeClass}" id="modal" role="dialog" aria-modal="true" ${this.options.title ? `aria-labelledby="modal-title"` : ''}>
          <div class="modal-glow-effect"></div>
          
          ${(this.options.title || this.options.showCloseButton) ? `
            <div class="modal-header">
              ${this.options.title ? `<h2 id="modal-title" class="modal-title">${this.options.title}</h2>` : ''}
              ${this.options.showCloseButton ? `
                <button class="modal-close-button" id="modal-close" aria-label="Close modal" type="button">
                  ✕
                </button>
              ` : ''}
            </div>
          ` : ''}
          
          <div class="modal-body">
            ${this.options.content}
          </div>
          
          ${this.options.footer ? `
            <div class="modal-footer">
              ${this.options.footer}
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  /**
   * Відкрити модальне вікно
   */
  open() {
    if (this.element || this.isActive) return;

    // Зберігаємо активний елемент
    this.previousActiveElement = document.activeElement;

    // Виклик callback
    this.options.onOpen();

    // Створюємо елемент
    const div = document.createElement('div');
    div.innerHTML = this.render();
    this.element = div.firstElementChild;

    // Додаємо в DOM
    document.body.appendChild(this.element);

    // Забороняємо скрол
    if (this.options.preventScroll) {
      document.body.style.overflow = 'hidden';
    }

    // Додаємо обробники
    this.attachEventListeners();

    // Анімація відкриття
    requestAnimationFrame(() => {
      this.element.classList.add('modal-active');
      const modal = this.element.querySelector('.modal');
      if (modal) {
        modal.classList.add('modal-active');
      }
      this.isActive = true;
      this.options.onAfterOpen();
    });
  }

  /**
   * Закрити модальне вікно
   */
  close() {
    if (!this.element || this.isClosing) return;

    this.isClosing = true;
    this.isActive = false;

    // Анімація закриття
    this.element.classList.remove('modal-active');
    const modal = this.element.querySelector('.modal');
    if (modal) {
      modal.classList.remove('modal-active');
    }

    // Видаляємо після анімації
    setTimeout(() => {
      this.cleanup();
      this.options.onAfterClose();
    }, 300);
  }

  /**
   * Очистка
   */
  cleanup() {
    // Відновлюємо скрол
    if (this.options.preventScroll) {
      document.body.style.overflow = '';
    }

    // Видаляємо обробники
    this.detachEventListeners();

    // Видаляємо елемент
    if (this.element) {
      this.element.remove();
      this.element = null;
    }

    // Відновлюємо фокус
    if (this.previousActiveElement) {
      this.previousActiveElement.focus();
    }

    this.isClosing = false;
  }

  /**
   * Додати обробники подій
   */
  attachEventListeners() {
    // Overlay click
    if (this.options.closeOnOverlay) {
      this.element.addEventListener('click', (e) => {
        if (e.target === this.element) {
          this.close();
          this.options.onClose();
        }
      });
    }

    // Close button
    const closeButton = this.element.querySelector('#modal-close');
    if (closeButton) {
      closeButton.addEventListener('click', () => {
        this.close();
        this.options.onClose();
      });

      // Hover ефект
      closeButton.addEventListener('mouseenter', () => {
        closeButton.classList.add('close-hover');
      });
      closeButton.addEventListener('mouseleave', () => {
        closeButton.classList.remove('close-hover');
      });
    }

    // ESC key
    if (this.options.closeOnEsc) {
      this.escHandler = (e) => {
        if (e.key === 'Escape') {
          this.close();
          this.options.onClose();
        }
      };
      document.addEventListener('keydown', this.escHandler);
    }
  }

  /**
   * Видалити обробники подій
   */
  detachEventListeners() {
    if (this.escHandler) {
      document.removeEventListener('keydown', this.escHandler);
      this.escHandler = null;
    }
  }

  /**
   * Оновити опції
   */
  update(options) {
    Object.assign(this.options, options);
    
    if (this.element && this.isActive) {
      // Оновлюємо контент
      const body = this.element.querySelector('.modal-body');
      if (body && options.content !== undefined) {
        body.innerHTML = options.content;
      }

      // Оновлюємо заголовок
      const title = this.element.querySelector('.modal-title');
      if (title && options.title !== undefined) {
        title.textContent = options.title;
      }

      // Оновлюємо footer
      const footer = this.element.querySelector('.modal-footer');
      if (options.footer !== undefined) {
        if (options.footer && !footer) {
          // Додаємо footer
          const modal = this.element.querySelector('.modal');
          const footerDiv = document.createElement('div');
          footerDiv.className = 'modal-footer';
          footerDiv.innerHTML = options.footer;
          modal.appendChild(footerDiv);
        } else if (!options.footer && footer) {
          // Видаляємо footer
          footer.remove();
        } else if (footer) {
          // Оновлюємо footer
          footer.innerHTML = options.footer;
        }
      }
    }
  }

  /**
   * Перевірити чи відкрито
   */
  isOpen() {
    return this.isActive;
  }

  /**
   * Знищити компонент
   */
  destroy() {
    if (this.isActive) {
      this.close();
    }
  }
}

/**
 * Modal Button компонент
 */
export class ModalButton {
  constructor(options = {}) {
    this.options = {
      children: options.children || '',
      variant: options.variant || 'primary',
      onClick: options.onClick || (() => {}),
      disabled: options.disabled || false
    };
  }

  render() {
    const variantClass = this.options.variant === 'primary' ? 'modal-btn-primary' : 'modal-btn-secondary';
    
    return `
      <button 
        class="modal-btn ${variantClass}" 
        ${this.options.disabled ? 'disabled' : ''}
        type="button"
      >
        ${this.options.children}
      </button>
    `;
  }

  attachEvents(element) {
    if (!this.options.disabled) {
      element.addEventListener('click', this.options.onClick);
      
      element.addEventListener('mouseenter', () => {
        element.classList.add('btn-hover');
      });
      
      element.addEventListener('mouseleave', () => {
        element.classList.remove('btn-hover');
      });
    }
  }
}

/**
 * Confirm Modal компонент
 */
export class ConfirmModal extends Modal {
  constructor(options = {}) {
    const footer = `
      <button class="modal-btn modal-btn-secondary" id="confirm-cancel">
        Скасувати
      </button>
      <button class="modal-btn modal-btn-primary" id="confirm-ok">
        Підтвердити
      </button>
    `;

    super({
      ...options,
      title: options.title || 'Підтвердження оплати',
      footer: footer
    });

    this.onConfirm = options.onConfirm || (() => {});
    this.amount = options.amount || 100;
    this.currency = options.currency || 'USDT';

    // Оновлюємо контент
    this.options.content = `
      <p class="modal-text">Ви збираєтесь поповнити баланс на суму:</p>
      <div class="modal-highlight">${this.amount.toFixed(2)} ${this.currency}</div>
      <div class="modal-subtitle">Комісія: 0%</div>
    `;
  }

  attachEventListeners() {
    super.attachEventListeners();

    // Кнопка підтвердження
    const confirmBtn = this.element?.querySelector('#confirm-ok');
    if (confirmBtn) {
      confirmBtn.addEventListener('click', () => {
        this.onConfirm();
        this.close();
      });
    }

    // Кнопка скасування
    const cancelBtn = this.element?.querySelector('#confirm-cancel');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => {
        this.close();
        this.options.onClose();
      });
    }
  }
}

// Стилі компонента
const styles = `
<style>
/* Animations */
@keyframes rotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { transform: scale(0.9) translateY(20px); opacity: 0; }
  to { transform: scale(1) translateY(0); opacity: 1; }
}

/* Modal Overlay */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease;
}

.modal-overlay.modal-active {
  opacity: 1;
  visibility: visible;
}

/* Modal */
.modal {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  padding: 32px;
  width: 100%;
  max-height: 90vh;
  overflow: auto;
  transform: scale(0.9) translateY(20px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
}

.modal.modal-active {
  transform: scale(1) translateY(0);
}

/* Size variants */
.modal-small {
  max-width: 320px;
  padding: 24px;
}

.modal-medium {
  max-width: 430px;
}

.modal-large {
  max-width: 600px;
  padding: 40px;
}

/* Glow effect */
.modal-glow-effect {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(168, 85, 247, 0.1) 0%, transparent 70%);
  animation: rotate 20s linear infinite;
  pointer-events: none;
}

/* Header */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  position: relative;
  z-index: 1;
}

.modal-title {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #fff, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
  line-height: 1.2;
}

/* Close button */
.modal-close-button {
  width: 36px;
  height: 36px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 20px;
  color: #fff;
  outline: none;
  flex-shrink: 0;
}

.modal-close-button.close-hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.3);
  transform: rotate(90deg);
}

/* Body */
.modal-body {
  margin-bottom: 24px;
  position: relative;
  z-index: 1;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.6;
}

/* Footer */
.modal-footer {
  display: flex;
  gap: 12px;
  position: relative;
  z-index: 1;
}

/* Buttons */
.modal-btn {
  flex: 1;
  padding: 12px 24px;
  border: none;
  border-radius: 12px;
  font-weight: 600;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  outline: none;
  font-family: inherit;
}

.modal-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-btn-primary {
  background: linear-gradient(135deg, #a855f7, #6366f1);
  color: #fff;
}

.modal-btn-primary.btn-hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(168, 85, 247, 0.4);
}

.modal-btn-secondary {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
}

.modal-btn-secondary.btn-hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-1px);
}

/* Content helpers */
.modal-text {
  color: rgba(255, 255, 255, 0.8);
  font-size: 16px;
  margin-bottom: 16px;
}

.modal-highlight {
  font-size: 32px;
  font-weight: 700;
  text-align: center;
  margin: 20px 0;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.modal-subtitle {
  text-align: center;
  opacity: 0.7;
  font-size: 14px;
  margin-top: -10px;
  margin-bottom: 20px;
}

/* Scrollbar */
.modal::-webkit-scrollbar {
  width: 8px;
}

.modal::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.modal::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.modal::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>
`;

// Додаємо стилі при завантаженні
if (!document.getElementById('modal-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'modal-styles';
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}