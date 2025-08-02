// frontend/pages/home/components/RecentOrders.js
/**
 * Компонент последних заказов
 */

import { getIcon } from '../../../shared/ui/svg.js';

export default class RecentOrders {
  constructor(options = {}) {
    this.state = {
      orders: options.orders || [],
      isLoading: options.isLoading || false,
      maxVisible: options.maxVisible || 5
    };

    this.callbacks = {
      onOrderClick: options.onOrderClick || (() => {}),
      onViewAll: options.onViewAll || (() => {})
    };

    this.element = null;
    this.updateInterval = null;
  }

  /**
   * Рендер компонента
   */
  render() {
    if (this.state.isLoading) {
      return this.renderSkeleton();
    }

    if (this.state.orders.length === 0) {
      return this.renderEmpty();
    }

    const visibleOrders = this.state.orders.slice(0, this.state.maxVisible);

    return `
      <div class="recent-orders" id="recent-orders">
        <div class="orders-list">
          ${visibleOrders.map((order, index) => this.renderOrderItem(order, index)).join('')}
        </div>
        ${this.state.orders.length > this.state.maxVisible ? this.renderViewAllButton() : ''}
      </div>
    `;
  }

  /**
   * Рендер элемента заказа
   */
  renderOrderItem(order, index) {
    const status = this.getOrderStatus(order.status);
    const icon = this.getServiceIcon(order.service_name);
    const timeAgo = this.getTimeAgo(order.created_at);

    return `
      <div class="order-item glass ${status.class}" 
           data-order-id="${order.id}"
           style="animation-delay: ${index * 0.1}s">
        <div class="order-icon">
          ${icon}
        </div>
        <div class="order-info">
          <div class="order-header">
            <div class="order-id">#${order.order_number || order.id.slice(0, 8)}</div>
            <div class="order-time">${timeAgo}</div>
          </div>
          <div class="order-service">${this.formatServiceName(order.service_name)}</div>
          <div class="order-details">
            <span class="order-quantity">${order.quantity.toLocaleString('ru-RU')}</span>
            <span class="order-separator">•</span>
            <span class="order-link">${this.formatLink(order.link)}</span>
          </div>
        </div>
        <div class="order-status-wrapper">
          <div class="order-status ${status.class}">
            <span class="status-icon">${status.icon}</span>
            <span class="status-text">${status.text}</span>
          </div>
          ${this.renderProgress(order)}
        </div>
      </div>
    `;
  }

  /**
   * Рендер прогресса заказа
   */
  renderProgress(order) {
    if (!['in_progress', 'processing'].includes(order.status)) {
      return '';
    }

    const progress = order.progress || 0;

    return `
      <div class="order-progress">
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${progress}%"></div>
        </div>
        <div class="progress-text">${progress}%</div>
      </div>
    `;
  }

  /**
   * Получить статус заказа
   */
  getOrderStatus(status) {
    const statuses = {
      'pending': {
        text: 'Ожидание',
        class: 'status-pending',
        icon: getIcon('loading', 'status-icon-svg', 16)
      },
      'processing': {
        text: 'Обработка',
        class: 'status-processing',
        icon: getIcon('loading', 'status-icon-svg animate-spin', 16)
      },
      'in_progress': {
        text: 'Выполняется',
        class: 'status-progress',
        icon: getIcon('loading', 'status-icon-svg animate-spin', 16)
      },
      'completed': {
        text: 'Выполнен',
        class: 'status-completed',
        icon: getIcon('success', 'status-icon-svg', 16)
      },
      'partial': {
        text: 'Частично',
        class: 'status-partial',
        icon: getIcon('warning', 'status-icon-svg', 16)
      },
      'cancelled': {
        text: 'Отменен',
        class: 'status-cancelled',
        icon: getIcon('close', 'status-icon-svg', 16)
      },
      'failed': {
        text: 'Ошибка',
        class: 'status-failed',
        icon: getIcon('error', 'status-icon-svg', 16)
      }
    };

    return statuses[status] || statuses['pending'];
  }

  /**
   * Получить иконку сервиса
   */
  getServiceIcon(serviceName) {
    const name = serviceName.toLowerCase();

    if (name.includes('подписчик') || name.includes('subscriber')) {
      return getIcon('subscribers', 'order-icon-svg', 24);
    } else if (name.includes('просмотр') || name.includes('view')) {
      return getIcon('views', 'order-icon-svg', 24);
    } else if (name.includes('реакц') || name.includes('like')) {
      return getIcon('reactions', 'order-icon-svg', 24);
    } else {
      return getIcon('telegram', 'order-icon-svg', 24);
    }
  }

  /**
   * Форматирование имени сервиса
   */
  formatServiceName(name) {
    let formatted = name.replace(/^(Telegram|Телеграм):\s*/i, '');
    if (formatted.length > 40) {
      formatted = formatted.substring(0, 37) + '...';
    }
    return formatted;
  }

  /**
   * Форматирование ссылки
   */
  formatLink(link) {
    try {
      const url = new URL(link);
      const path = url.pathname + url.search;
      return path.length > 25 ? path.substring(0, 22) + '...' : path;
    } catch {
      return link.length > 25 ? link.substring(0, 22) + '...' : link;
    }
  }

  /**
   * Получить время назад
   */
  getTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'только что';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} мин назад`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} ч назад`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)} д назад`;

    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
  }

  /**
   * Рендер кнопки "Показать все"
   */
  renderViewAllButton() {
    return `
      <button class="view-all-button glass" id="view-all-orders">
        <span>Показать все заказы</span>
        <span class="view-all-icon">${getIcon('arrowRight', '', 20)}</span>
      </button>
    `;
  }

  /**
   * Рендер skeleton loader
   */
  renderSkeleton() {
    return `
      <div class="orders-skeleton">
        ${Array(3).fill(0).map(() => `
          <div class="skeleton-order-item">
            <div class="skeleton-icon"></div>
            <div class="skeleton-content">
              <div class="skeleton-line" style="width: 30%;"></div>
              <div class="skeleton-line" style="width: 70%;"></div>
              <div class="skeleton-line" style="width: 50%;"></div>
            </div>
            <div class="skeleton-status"></div>
          </div>
        `).join('')}
      </div>
    `;
  }

  /**
   * Рендер пустого состояния
   */
  renderEmpty() {
    return `
      <div class="empty-state">
        <div class="empty-state-icon">
          ${getIcon('orders', '', 64)}
        </div>
        <div class="empty-state-text">Нет активных заказов</div>
        <div class="empty-state-subtext">Создайте свой первый заказ</div>
        <button class="btn btn-primary" onclick="window.location.href='/services'">
          <span>Перейти к услугам</span>
        </button>
      </div>
    `;
  }

  /**
   * Инициализация после рендера
   */
  init() {
    this.element = document.getElementById('recent-orders');
    if (!this.element) return;

    // Обработчики для заказов
    const orderItems = this.element.querySelectorAll('.order-item');
    orderItems.forEach(item => {
      item.addEventListener('click', () => {
        const orderId = item.dataset.orderId;
        const order = this.state.orders.find(o => o.id === orderId);
        if (order) {
          this.callbacks.onOrderClick(order);
        }
      });
    });

    // Обработчик для кнопки "Показать все"
    const viewAllBtn = document.getElementById('view-all-orders');
    if (viewAllBtn) {
      viewAllBtn.addEventListener('click', () => {
        this.callbacks.onViewAll();
      });
    }

    // Запускаем обновление времени
    this.startTimeUpdates();
  }

  /**
   * Обновление компонента
   */
  update(newState) {
    Object.assign(this.state, newState);

    if (this.element) {
      const parent = this.element.parentElement;
      parent.innerHTML = this.render();
      this.init();
    }
  }

  /**
   * Запуск обновления времени
   */
  startTimeUpdates() {
    this.stopTimeUpdates();

    this.updateInterval = setInterval(() => {
      const timeElements = this.element.querySelectorAll('.order-time');
      timeElements.forEach((el, index) => {
        if (this.state.orders[index]) {
          el.textContent = this.getTimeAgo(this.state.orders[index].created_at);
        }
      });
    }, 60000); // Обновляем каждую минуту
  }

  /**
   * Остановка обновления времени
   */
  stopTimeUpdates() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }
  }

  /**
   * Уничтожение компонента
   */
  destroy() {
    this.stopTimeUpdates();
    if (this.element) {
      this.element.remove();
    }
  }
}

// Дополнительные стили для компонента
const styles = `
<style>
.recent-orders {
  animation: slideUp 0.6s ease-out both;
}

.orders-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.order-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--blur-md));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.3s ease;
  animation: slideUp 0.6s ease-out both;
}

.order-item:hover {
  background: var(--glass-bg-hover);
  transform: translateX(5px);
  border-color: var(--glass-border-hover);
}

.order-icon {
  width: 40px;
  height: 40px;
  background: var(--glass-bg-active);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--primary-light);
}

.order-icon-svg {
  width: 24px;
  height: 24px;
}

.order-info {
  flex: 1;
  min-width: 0;
}

.order-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.order-id {
  font-size: 13px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.order-time {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-left: auto;
}

.order-service {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.order-details {
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.order-separator {
  opacity: 0.5;
}

.order-status-wrapper {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  flex-shrink: 0;
}

.order-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.status-icon-svg {
  width: 16px;
  height: 16px;
}

.status-pending {
  background: var(--glass-bg-active);
  color: var(--text-secondary);
}

.status-processing,
.status-progress {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
}

.status-completed {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.status-partial {
  background: rgba(251, 191, 36, 0.2);
  color: #f59e0b;
}

.status-cancelled,
.status-failed {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.order-progress {
  width: 100px;
  font-size: 11px;
  color: var(--text-tertiary);
}

.progress-bar {
  height: 4px;
  background: var(--glass-bg-active);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 4px;
}

.progress-fill {
  height: 100%;
  background: var(--gradient-primary);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-text {
  text-align: center;
}

.view-all-button {
  width: 100%;
  padding: 16px;
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  color: var(--primary-light);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.view-all-button:hover {
  background: var(--glass-bg-hover);
  border-color: var(--primary);
  transform: translateY(-2px);
}

.view-all-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.3s ease;
}

.view-all-button:hover .view-all-icon {
  transform: translateX(4px);
}

/* Skeleton стили */
.skeleton-order-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
}

.skeleton-icon {
  width: 40px;
  height: 40px;
  background: var(--glass-bg-active);
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.skeleton-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.skeleton-status {
  width: 80px;
  height: 28px;
  background: var(--glass-bg-active);
  border-radius: var(--radius-md);
}

/* Mobile responsive */
@media (max-width: 380px) {
  .order-item {
    padding: 12px;
    gap: 12px;
  }

  .order-details {
    font-size: 12px;
  }

  .order-status {
    padding: 4px 10px;
  }
}
</style>
`;

// Добавляем стили в документ
if (!document.getElementById('recent-orders-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'recent-orders-styles';
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}