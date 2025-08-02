// frontend/shared/components/Loader.js
/**
 * Loader компонент для TeleBoost
 * Переписаний з React на Vanilla JS
 */

export default class Loader {
  constructor(options = {}) {
    this.options = {
      fullScreen: options.fullScreen !== false,
      text: options.text || 'Loading...',
      showProgress: options.showProgress || false,
      progress: options.progress || 0,
      size: options.size || 'medium',
      dots: options.dots || 4
    };

    this.element = null;
    this.container = null;
  }

  /**
   * Рендер компонента
   */
  render() {
    if (!this.options.fullScreen) {
      return '';
    }

    const dots = Array.from({ length: this.options.dots }, (_, i) => `
      <div class="loader-dot" style="animation-delay: ${i * 0.15}s;"></div>
    `).join('');

    return `
      <div class="loader-container" id="loader-container">
        <div class="loader-wrapper">
          <div class="loader-dots-container loader-size-${this.options.size}">
            ${dots}
          </div>
          
          ${this.options.text ? `
            <div class="loader-text">${this.options.text}</div>
          ` : ''}
          
          ${this.options.showProgress ? `
            <div class="loader-progress-container">
              <div class="loader-progress-bar" style="width: ${Math.min(100, Math.max(0, this.options.progress))}%"></div>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  /**
   * Показати loader
   */
  show(container = document.body) {
    this.container = container;
    
    // Створюємо елемент
    const div = document.createElement('div');
    div.innerHTML = this.render();
    this.element = div.firstElementChild;
    
    // Додаємо в DOM
    container.appendChild(this.element);
    
    // Анімація появи
    requestAnimationFrame(() => {
      this.element?.classList.add('loader-active');
    });
  }

  /**
   * Сховати loader
   */
  hide() {
    if (this.element) {
      this.element.classList.remove('loader-active');
      setTimeout(() => {
        this.element?.remove();
        this.element = null;
      }, 300);
    }
  }

  /**
   * Оновити прогрес
   */
  updateProgress(progress) {
    this.options.progress = progress;
    if (this.element) {
      const progressBar = this.element.querySelector('.loader-progress-bar');
      if (progressBar) {
        progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
      }
    }
  }

  /**
   * Оновити текст
   */
  updateText(text) {
    this.options.text = text;
    if (this.element) {
      const textElement = this.element.querySelector('.loader-text');
      if (textElement) {
        textElement.textContent = text;
      }
    }
  }
}

/**
 * Inline Loader компонент
 */
export class InlineLoader {
  constructor(options = {}) {
    this.options = {
      text: options.text || 'Loading',
      dots: options.dots || 3
    };
    this.element = null;
  }

  render() {
    const dots = Array.from({ length: this.options.dots }, (_, i) => `
      <div class="inline-loader-dot" style="animation-delay: ${i * 0.15}s;"></div>
    `).join('');

    return `
      <div class="inline-loader-container">
        <div class="inline-loader-dots">
          ${dots}
        </div>
        ${this.options.text ? `<span class="inline-loader-text">${this.options.text}</span>` : ''}
      </div>
    `;
  }

  mount(container) {
    const div = document.createElement('div');
    div.innerHTML = this.render();
    this.element = div.firstElementChild;
    container.appendChild(this.element);
  }

  destroy() {
    if (this.element) {
      this.element.remove();
    }
  }
}

/**
 * Button Loader компонент
 */
export class ButtonLoader {
  constructor(options = {}) {
    this.options = {
      text: options.text || ''
    };
  }

  render() {
    return `
      <div class="button-loader-container">
        <div class="button-loader-dots">
          <div class="button-loader-dot" style="animation-delay: 0s;"></div>
          <div class="button-loader-dot" style="animation-delay: 0.1s;"></div>
          <div class="button-loader-dot" style="animation-delay: 0.2s;"></div>
        </div>
        ${this.options.text ? `<span class="button-loader-text">${this.options.text}</span>` : ''}
      </div>
    `;
  }
}

/**
 * Skeleton Loader компонент
 */
export class SkeletonLoader {
  constructor(options = {}) {
    this.options = {
      height: options.height || '20px',
      width: options.width || '100%',
      borderRadius: options.borderRadius || '12px'
    };
  }

  render() {
    return `
      <div class="skeleton-loader" style="height: ${this.options.height}; width: ${this.options.width}; border-radius: ${this.options.borderRadius};">
        <div class="skeleton-shimmer"></div>
      </div>
    `;
  }
}

/**
 * Loading Overlay компонент
 */
export class LoadingOverlay {
  constructor(options = {}) {
    this.options = {
      visible: options.visible || false,
      text: options.text || 'Loading...',
      blur: options.blur !== false
    };
    
    this.element = null;
  }

  render() {
    if (!this.options.visible) return '';

    const dots = Array.from({ length: 4 }, (_, i) => `
      <div class="loader-dot" style="animation-delay: ${i * 0.15}s;"></div>
    `).join('');

    return `
      <div class="loading-overlay ${this.options.blur ? 'with-blur' : ''}" id="loading-overlay">
        <div class="loader-wrapper">
          <div class="loader-dots-container">
            ${dots}
          </div>
          ${this.options.text ? `<div class="loader-text">${this.options.text}</div>` : ''}
        </div>
      </div>
    `;
  }

  show(container = document.body) {
    const div = document.createElement('div');
    div.innerHTML = this.render();
    this.element = div.firstElementChild;
    container.appendChild(this.element);
    
    requestAnimationFrame(() => {
      this.element?.classList.add('overlay-active');
    });
  }

  hide() {
    if (this.element) {
      this.element.classList.remove('overlay-active');
      setTimeout(() => {
        this.element?.remove();
        this.element = null;
      }, 300);
    }
  }
}

// Стилі для компонентів
const styles = `
<style>
/* Animations */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

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

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes morph {
  0%, 100% {
    transform: scale(1) translateY(0);
    filter: blur(0);
    opacity: 1;
  }
  50% {
    transform: scale(1.5) translateY(-20px);
    filter: blur(2px);
    opacity: 0.7;
  }
}

@keyframes morphSmall {
  0%, 100% {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
  50% {
    transform: scale(1.3) translateY(-8px);
    opacity: 0.6;
  }
}

@keyframes morphButton {
  0%, 100% {
    transform: scale(1);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.2);
    opacity: 1;
  }
}

@keyframes shimmer {
  0% { left: -100%; }
  100% { left: 200%; }
}

/* Main Loader */
.loader-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  z-index: 9999;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease-out;
}

.loader-container.loader-active {
  opacity: 1;
  visibility: visible;
}

.loader-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.loader-dots-container {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.loader-dot {
  width: 16px;
  height: 16px;
  background: linear-gradient(135deg, #a855f7, #ec4899);
  border-radius: 50%;
  animation: morph 1.5s ease-in-out infinite;
  position: relative;
  box-shadow: 0 0 20px rgba(168, 85, 247, 0.5);
}

/* Size variants */
.loader-size-small .loader-dot {
  width: 12px;
  height: 12px;
}

.loader-size-large .loader-dot {
  width: 20px;
  height: 20px;
}

.loader-text {
  font-size: 14px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.8);
  letter-spacing: 0.5px;
  animation: pulse 2s ease-in-out infinite;
}

.loader-progress-container {
  width: 200px;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}

.loader-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #a855f7, #ec4899);
  border-radius: 2px;
  transition: width 0.3s ease-out;
  box-shadow: 0 0 10px rgba(168, 85, 247, 0.5);
}

/* Inline Loader */
.inline-loader-container {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.inline-loader-dots {
  display: flex;
  gap: 6px;
}

.inline-loader-dot {
  width: 8px;
  height: 8px;
  background: linear-gradient(135deg, #a855f7, #ec4899);
  border-radius: 50%;
  animation: morphSmall 1.5s ease-in-out infinite;
}

.inline-loader-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

/* Button Loader */
.button-loader-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.button-loader-dots {
  display: flex;
  gap: 4px;
}

.button-loader-dot {
  width: 6px;
  height: 6px;
  background: #fff;
  border-radius: 50%;
  animation: morphButton 1.2s ease-in-out infinite;
}

.button-loader-text {
  margin-left: 8px;
  color: #fff;
}

/* Skeleton Loader */
.skeleton-loader {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  overflow: hidden;
  position: relative;
}

.skeleton-shimmer {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
  animation: shimmer 2s infinite;
}

/* Loading Overlay */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease;
}

.loading-overlay.with-blur {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
}

.loading-overlay.overlay-active {
  opacity: 1;
  visibility: visible;
}

/* Pulse animation */
@keyframes pulse {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 0.4; }
}
</style>
`;

// Додаємо стилі при завантаженні
if (!document.getElementById('loader-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'loader-styles';
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}