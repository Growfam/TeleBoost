// frontend/shared/components/Header.js
/**
 * Header компонент для TeleBoost
 * Переписаний з React на Vanilla JS
 */

export default class Header {
  constructor(options = {}) {
    this.state = {
      isMenuOpen: false,
      isMenuHovered: false,
      isLogoHovered: false
    };

    this.options = {
      onMenuClick: options.onMenuClick || (() => {}),
      showNotification: options.showNotification || false,
      userName: options.userName || 'Guest',
      balance: options.balance || 0,
      currency: options.currency || 'USDT'
    };

    this.element = null;
  }

  /**
   * Рендер компонента
   */
  render() {
    return `
      <header class="main-header" id="main-header">
        <div class="header-sweep-effect"></div>
        
        <div class="header-logo" id="header-logo">
          TeleBoost
        </div>

        <button class="menu-button" id="menu-button" aria-label="Menu" aria-expanded="${this.state.isMenuOpen}">
          ${this.options.showNotification ? '<div class="notification-badge"></div>' : ''}
          <div class="menu-line menu-line-top"></div>
          <div class="menu-line menu-line-middle"></div>
          <div class="menu-line menu-line-bottom"></div>
        </button>
      </header>
    `;
  }

  /**
   * Ініціалізація після рендера
   */
  init() {
    this.element = document.getElementById('main-header');
    if (!this.element) return;

    // Logo обробники
    const logo = document.getElementById('header-logo');
    if (logo) {
      logo.addEventListener('mouseenter', () => this.handleLogoHover(true));
      logo.addEventListener('mouseleave', () => this.handleLogoHover(false));
      logo.addEventListener('click', () => window.location.href = '/');
    }

    // Menu button обробники
    const menuButton = document.getElementById('menu-button');
    if (menuButton) {
      menuButton.addEventListener('click', () => this.handleMenuClick());
      menuButton.addEventListener('mouseenter', () => this.handleMenuHover(true));
      menuButton.addEventListener('mouseleave', () => this.handleMenuHover(false));
    }

    // Додаємо анімацію появи
    setTimeout(() => {
      this.element.classList.add('mounted');
    }, 10);
  }

  /**
   * Обробка кліку на меню
   */
  handleMenuClick() {
    this.state.isMenuOpen = !this.state.isMenuOpen;
    this.updateMenuState();
    this.options.onMenuClick(this.state.isMenuOpen);
  }

  /**
   * Обробка ховера на лого
   */
  handleLogoHover(isHovered) {
    this.state.isLogoHovered = isHovered;
    const logo = document.getElementById('header-logo');
    if (logo) {
      if (isHovered) {
        logo.classList.add('logo-hover');
      } else {
        logo.classList.remove('logo-hover');
      }
    }
  }

  /**
   * Обробка ховера на меню
   */
  handleMenuHover(isHovered) {
    this.state.isMenuHovered = isHovered;
    const menuButton = document.getElementById('menu-button');
    if (menuButton) {
      if (isHovered) {
        menuButton.classList.add('menu-hover');
      } else {
        menuButton.classList.remove('menu-hover');
      }
    }
  }

  /**
   * Оновлення стану меню
   */
  updateMenuState() {
    const menuButton = document.getElementById('menu-button');
    if (menuButton) {
      menuButton.setAttribute('aria-expanded', this.state.isMenuOpen);
      if (this.state.isMenuOpen) {
        menuButton.classList.add('menu-open');
      } else {
        menuButton.classList.remove('menu-open');
      }
    }
  }

  /**
   * Оновлення опцій
   */
  update(options) {
    Object.assign(this.options, options);
    
    // Оновлюємо notification badge
    if (this.element) {
      const menuButton = this.element.querySelector('.menu-button');
      const badge = menuButton?.querySelector('.notification-badge');
      
      if (this.options.showNotification && !badge) {
        const newBadge = document.createElement('div');
        newBadge.className = 'notification-badge';
        menuButton?.prepend(newBadge);
      } else if (!this.options.showNotification && badge) {
        badge.remove();
      }
    }
  }

  /**
   * Знищення компонента
   */
  destroy() {
    if (this.element) {
      this.element.remove();
    }
  }
}

// Стилі для компонента
const styles = `
<style>
/* Header Styles */
.main-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  margin: 0 auto;
  max-width: 430px;
  opacity: 0;
  transform: translateY(-20px);
}

.main-header.mounted {
  opacity: 1;
  transform: translateY(0);
  animation: slideIn 0.6s ease-out;
}

.header-sweep-effect {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(168, 85, 247, 0.2), transparent);
  animation: sweep 3s infinite;
  pointer-events: none;
}

.header-logo {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #a78bfa 0%, #c084fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.02em;
  cursor: pointer;
  user-select: none;
  position: relative;
  z-index: 1;
  transition: transform 0.3s ease;
}

.header-logo.logo-hover {
  transform: scale(1.05);
}

.menu-button {
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 1;
  outline: none;
}

.menu-button.menu-hover {
  background: rgba(168, 85, 247, 0.2);
  transform: scale(1.05);
  border-color: rgba(168, 85, 247, 0.3);
}

.menu-button:active {
  transform: scale(0.95);
}

.menu-line {
  width: 20px;
  height: 2px;
  background: #fff;
  border-radius: 1px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: center;
}

.menu-line-top {
  transform: translateY(-2px);
}

.menu-line-bottom {
  transform: translateY(2px);
}

/* Menu open state */
.menu-open .menu-line-top {
  transform: rotate(45deg) translateY(0);
}

.menu-open .menu-line-middle {
  opacity: 0;
  transform: scaleX(0);
}

.menu-open .menu-line-bottom {
  transform: rotate(-45deg) translateY(0);
}

/* Notification badge */
.notification-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 12px;
  height: 12px;
  background: #ef4444;
  border-radius: 50%;
  border: 2px solid rgba(0, 0, 0, 0.5);
  animation: pulse 2s ease-in-out infinite;
}

/* Animations */
@keyframes sweep {
  0% { left: -100%; }
  100% { left: 100%; }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.8;
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
`;

// Додаємо стилі при завантаженні
if (!document.getElementById('header-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'header-styles';
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}

/**
 * Extended Header with user info
 */
export class HeaderWithUserInfo extends Header {
  render() {
    return `
      <header class="main-header extended-header" id="main-header">
        <div class="header-sweep-effect"></div>
        
        <div class="header-logo" id="header-logo">
          TeleBoost
        </div>

        <div class="user-info-section">
          <div class="balance-container" id="header-balance">
            <span class="balance-icon">💰</span>
            <span class="balance-text">Balance:</span>
            <span class="balance-amount">${this.options.balance.toFixed(2)} ${this.options.currency}</span>
          </div>

          <button class="menu-button" id="menu-button" aria-label="Menu" aria-expanded="${this.state.isMenuOpen}">
            ${this.options.showNotification ? '<div class="notification-badge"></div>' : ''}
            <div class="menu-line menu-line-top"></div>
            <div class="menu-line menu-line-middle"></div>
            <div class="menu-line menu-line-bottom"></div>
          </button>
        </div>
      </header>
    `;
  }
}

// Додаткові стилі для extended header
const extendedStyles = `
<style>
.extended-header {
  padding: 16px 20px;
}

.user-info-section {
  display: flex;
  align-items: center;
  gap: 16px;
  position: relative;
  z-index: 1;
}

.balance-container {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.balance-icon {
  font-size: 16px;
}

.balance-text {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.balance-amount {
  font-size: 16px;
  font-weight: 700;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
</style>
`;

if (!document.getElementById('header-extended-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'header-extended-styles';
  styleElement.innerHTML = extendedStyles;
  document.head.appendChild(styleElement);
}