// frontend/shared/components/Navigation.js
/**
 * Navigation компонент для TeleBoost
 * Переписаний з React на Vanilla JS
 */

import { getIcon } from '../ui/svg.js';

export default class Navigation {
  constructor(options = {}) {
    this.state = {
      activeItem: options.activeItem || 'home',
      mounted: false
    };

    this.options = {
      onNavigate: options.onNavigate || (() => {}),
      notifications: options.notifications || { orders: 0, profile: false }
    };

    this.element = null;
    this.indicatorStyle = {};
    this.itemRefs = {};

    // Конфігурація навігації
    this.navigationItems = [
      { id: 'home', label: 'Головна', icon: 'home', path: '/' },
      { id: 'services', label: 'Послуги', icon: 'services', path: '/services' },
      { id: 'orders', label: 'Замовлення', icon: 'orders', path: '/orders' },
      { id: 'balance', label: 'Баланс', icon: 'balance', path: '/balance' },
      { id: 'profile', label: 'Профіль', icon: 'profile', path: '/profile' }
    ];
  }

  /**
   * Рендер компонента
   */
  render() {
    return `
      <nav class="main-navigation" id="main-navigation" role="navigation" aria-label="Main navigation">
        <div class="nav-indicator" id="nav-indicator" aria-hidden="true"></div>
        
        ${this.navigationItems.map(item => this.renderNavItem(item)).join('')}
      </nav>
    `;
  }

  /**
   * Рендер елемента навігації
   */
  renderNavItem(item) {
    const isActive = this.state.activeItem === item.id;
    const showBadge = item.id === 'orders' && this.options.notifications.orders > 0;
    const showDot = item.id === 'profile' && this.options.notifications.profile;

    return `
      <button 
        class="nav-item ${isActive ? 'nav-item-active' : ''}" 
        id="nav-${item.id}"
        data-nav-id="${item.id}"
        aria-label="${item.label}"
        ${isActive ? 'aria-current="page"' : ''}
      >
        <span class="nav-icon ${isActive ? 'nav-icon-active' : ''}">
          ${getIcon(item.icon, '', 24)}
        </span>
        <span class="nav-label">${item.label}</span>
        
        ${showBadge ? `
          <span class="nav-badge" aria-label="${this.options.notifications.orders} new items">
            ${this.options.notifications.orders}
          </span>
        ` : ''}
        
        ${showDot ? '<span class="nav-dot" aria-label="New notification"></span>' : ''}
      </button>
    `;
  }

  /**
   * Ініціалізація після рендера
   */
  init() {
    this.element = document.getElementById('main-navigation');
    if (!this.element) return;

    // Зберігаємо референції на елементи
    this.navigationItems.forEach(item => {
      this.itemRefs[item.id] = document.getElementById(`nav-${item.id}`);
    });

    // Додаємо обробники кліків
    this.navigationItems.forEach(item => {
      const element = this.itemRefs[item.id];
      if (element) {
        element.addEventListener('click', () => this.handleNavigate(item));
      }
    });

    // Ініціалізуємо позицію індикатора
    setTimeout(() => {
      this.updateIndicator(this.state.activeItem);
      this.element.classList.add('navigation-mounted');
    }, 10);

    // Слухаємо зміну розміру вікна
    window.addEventListener('resize', () => this.updateIndicator(this.state.activeItem));
  }

  /**
   * Обробка навігації
   */
  handleNavigate(item) {
    this.state.activeItem = item.id;
    this.updateActiveState();
    this.updateIndicator(item.id);
    this.options.onNavigate(item);
  }

  /**
   * Оновлення активного стану
   */
  updateActiveState() {
    this.navigationItems.forEach(item => {
      const element = this.itemRefs[item.id];
      if (element) {
        if (item.id === this.state.activeItem) {
          element.classList.add('nav-item-active');
          element.setAttribute('aria-current', 'page');
          
          const icon = element.querySelector('.nav-icon');
          if (icon) icon.classList.add('nav-icon-active');
        } else {
          element.classList.remove('nav-item-active');
          element.removeAttribute('aria-current');
          
          const icon = element.querySelector('.nav-icon');
          if (icon) icon.classList.remove('nav-icon-active');
        }
      }
    });
  }

  /**
   * Оновлення позиції індикатора
   */
  updateIndicator(itemId) {
    const itemElement = this.itemRefs[itemId];
    const indicator = document.getElementById('nav-indicator');
    
    if (itemElement && this.element && indicator) {
      const navRect = this.element.getBoundingClientRect();
      const itemRect = itemElement.getBoundingClientRect();
      
      indicator.style.left = `${itemRect.left - navRect.left}px`;
      indicator.style.width = `${itemRect.width}px`;
    }
  }

  /**
   * Оновлення компонента
   */
  update(options) {
    if (options.activeItem !== undefined) {
      this.state.activeItem = options.activeItem;
      this.updateActiveState();
      this.updateIndicator(options.activeItem);
    }

    if (options.notifications !== undefined) {
      this.options.notifications = options.notifications;
      this.updateNotifications();
    }
  }

  /**
   * Оновлення нотифікацій
   */
  updateNotifications() {
    // Оновлюємо badge для orders
    const ordersElement = this.itemRefs['orders'];
    if (ordersElement) {
      const badge = ordersElement.querySelector('.nav-badge');
      const shouldShowBadge = this.options.notifications.orders > 0;

      if (shouldShowBadge && !badge) {
        // Додаємо badge
        const newBadge = document.createElement('span');
        newBadge.className = 'nav-badge';
        newBadge.setAttribute('aria-label', `${this.options.notifications.orders} new items`);
        newBadge.textContent = this.options.notifications.orders;
        ordersElement.appendChild(newBadge);
      } else if (shouldShowBadge && badge) {
        // Оновлюємо badge
        badge.textContent = this.options.notifications.orders;
        badge.setAttribute('aria-label', `${this.options.notifications.orders} new items`);
      } else if (!shouldShowBadge && badge) {
        // Видаляємо badge
        badge.remove();
      }
    }

    // Оновлюємо dot для profile
    const profileElement = this.itemRefs['profile'];
    if (profileElement) {
      const dot = profileElement.querySelector('.nav-dot');
      const shouldShowDot = this.options.notifications.profile;

      if (shouldShowDot && !dot) {
        // Додаємо dot
        const newDot = document.createElement('span');
        newDot.className = 'nav-dot';
        newDot.setAttribute('aria-label', 'New notification');
        profileElement.appendChild(newDot);
      } else if (!shouldShowDot && dot) {
        // Видаляємо dot
        dot.remove();
      }
    }
  }

  /**
   * Знищення компонента
   */
  destroy() {
    window.removeEventListener('resize', () => this.updateIndicator(this.state.activeItem));
    if (this.element) {
      this.element.remove();
    }
  }
}

/**
 * Compact Navigation без лейблів
 */
export class NavigationCompact extends Navigation {
  constructor(options) {
    super(options);
    this.compact = true;
  }

  renderNavItem(item) {
    const isActive = this.state.activeItem === item.id;
    const showBadge = item.id === 'orders' && this.options.notifications.orders > 0;
    const showDot = item.id === 'profile' && this.options.notifications.profile;

    return `
      <button 
        class="nav-item nav-item-compact ${isActive ? 'nav-item-active' : ''}" 
        id="nav-${item.id}"
        data-nav-id="${item.id}"
        aria-label="${item.label}"
        ${isActive ? 'aria-current="page"' : ''}
      >
        <span class="nav-icon ${isActive ? 'nav-icon-active' : ''}">
          ${getIcon(item.icon, '', 24)}
        </span>
        
        ${showBadge ? `
          <span class="nav-badge" aria-label="${this.options.notifications.orders} new items">
            ${this.options.notifications.orders}
          </span>
        ` : ''}
        
        ${showDot ? '<span class="nav-dot" aria-label="New notification"></span>' : ''}
      </button>
    `;
  }

  render() {
    return `
      <nav class="main-navigation navigation-compact" id="main-navigation" role="navigation" aria-label="Main navigation">
        <div class="nav-indicator" id="nav-indicator" aria-hidden="true"></div>
        
        ${this.navigationItems.map(item => this.renderNavItem(item)).join('')}
      </nav>
    `;
  }
}

// Стилі компонента
const styles = `
<style>
/* Animations */
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translate(-50%, 100%);
  }
  to {
    opacity: 1;
    transform: translate(-50%, 0);
  }
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

@keyframes badgePulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

/* Navigation */
.main-navigation {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(20, 20, 20, 0.9);
  backdrop-filter: blur(30px);
  -webkit-backdrop-filter: blur(30px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  padding: 4px;
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  width: auto;
  max-width: calc(100% - 40px);
  opacity: 0;
  visibility: hidden;
}

.main-navigation.navigation-mounted {
  opacity: 1;
  visibility: visible;
  animation: slideUp 0.6s ease-out;
}

/* Indicator */
.nav-indicator {
  position: absolute;
  height: calc(100% - 8px);
  background: linear-gradient(135deg, #a855f7, #6366f1);
  border-radius: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  top: 4px;
  box-shadow: 0 4px 20px rgba(168, 85, 247, 0.4);
  pointer-events: none;
}

/* Nav Item */
.nav-item {
  position: relative;
  width: 80px;
  height: 56px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  z-index: 1;
  transition: all 0.3s ease;
  color: rgba(255, 255, 255, 0.5);
  background-color: transparent;
  border: none;
  outline: none;
  -webkit-tap-highlight-color: transparent;
}

.nav-item-active {
  color: #fff;
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.nav-icon svg {
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.nav-icon-active {
  filter: drop-shadow(0 0 8px rgba(168, 85, 247, 0.6));
  transform: scale(1.1);
}

.nav-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
  transition: all 0.3s ease;
  user-select: none;
}

/* Badge */
.nav-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
  animation: badgePulse 2s ease-in-out infinite;
}

/* Dot */
.nav-dot {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 8px;
  height: 8px;
  background: #ef4444;
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgba(20, 20, 20, 0.9);
  animation: pulse 2s ease-in-out infinite;
}

/* Compact Navigation */
.navigation-compact {
  padding: 6px;
  border-radius: 18px;
}

.navigation-compact .nav-indicator {
  top: 6px;
  border-radius: 12px;
}

.nav-item-compact {
  width: 60px;
  height: 48px;
  gap: 0;
}

/* Mobile responsive */
@media (max-width: 380px) {
  .nav-item {
    width: 70px;
  }
  
  .nav-label {
    font-size: 10px;
  }
}

/* Fix for iOS Safari */
@supports (-webkit-touch-callout: none) {
  .main-navigation {
    padding-bottom: env(safe-area-inset-bottom);
  }
}
</style>
`;

// Додаємо стилі при завантаженні
if (!document.getElementById('navigation-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'navigation-styles';
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}