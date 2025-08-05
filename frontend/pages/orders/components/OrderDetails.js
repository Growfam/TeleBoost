// frontend/pages/orders/components/OrderDetails.js
/**
 * OrderDetails компонент у card-based стилі
 * Відображає детальну інформацію про замовлення з картками статистики
 */

import Component from '../../../shared/core/Component.js';
import { formatNumber, formatPrice, formatDateTime } from '../../../shared/utils/formatters.js';
import { ordersAPI } from '../services/OrdersAPI.js';

export default class OrderDetails extends Component {
  constructor(order, options = {}) {
    super(options);

    this.state = {
      order,
      isLoading: false,
      activeTab: 'overview' // overview, progress, actions
    };

    this.onAction = options.onAction || (() => {});
    this.onClose = options.onClose || (() => {});
  }

  render() {
    const { order, isLoading, activeTab } = this.state;

    if (!order) {
      return this.renderLoading();
    }

    const progress = order.quantity ? Math.round((order.completed / order.quantity) * 100) : 0;

    return `
      <div class="order-details-container">
        <!-- Header -->
        <div class="details-header glass-card">
          <div class="header-content">
            <h2 class="service-title gradient-text">${order.service_name}</h2>
            <div class="header-meta">
              <span class="order-id">Order #${order.order_number || order.id.slice(0, 8)}</span>
              <span class="status-badge ${this.getStatusClass(order.status)}">
                ${this.getStatusText(order.status)}
              </span>
            </div>
          </div>
          <button class="close-button glass-button" id="closeDetails">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <!-- Stats Cards -->
        <div class="stats-cards-grid">
          <div class="stat-card glass-card">
            <div class="stat-icon">
              ${this.getStatIcon('ordered')}
            </div>
            <div class="stat-info">
              <div class="stat-value">${formatNumber(order.quantity || 0)}</div>
              <div class="stat-label">ЗАМОВЛЕНО</div>
            </div>
          </div>

          <div class="stat-card glass-card">
            <div class="stat-icon">
              ${this.getStatIcon('completed')}
            </div>
            <div class="stat-info">
              <div class="stat-value">${formatNumber(order.completed || 0)}</div>
              <div class="stat-label">ВИКОНАНО</div>
            </div>
          </div>

          <div class="stat-card glass-card">
            <div class="stat-icon">
              ${this.getStatIcon('progress')}
            </div>
            <div class="stat-info">
              <div class="stat-value">${progress}%</div>
              <div class="stat-label">ПРОГРЕС</div>
            </div>
          </div>

          <div class="stat-card glass-card">
            <div class="stat-icon">
              ${this.getStatIcon('price')}
            </div>
            <div class="stat-info">
              <div class="stat-value">${formatPrice(order.charge || 0)}</div>
              <div class="stat-label">ВАРТІСТЬ</div>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="action-buttons">
          ${this.renderActionButtons(order)}
        </div>

        <!-- Tabs -->
        <div class="details-tabs">
          <button class="tab-button ${activeTab === 'overview' ? 'active' : ''}" data-tab="overview">
            Огляд
          </button>
          <button class="tab-button ${activeTab === 'progress' ? 'active' : ''}" data-tab="progress">
            Прогрес
          </button>
          <button class="tab-button ${activeTab === 'info' ? 'active' : ''}" data-tab="info">
            Інформація
          </button>
        </div>

        <!-- Tab Content -->
        <div class="tab-content glass-card">
          ${this.renderTabContent(activeTab, order, progress)}
        </div>
      </div>
    `;
  }

  renderLoading() {
    return `
      <div class="order-details-container">
        <div class="details-loading">
          <div class="loading-spinner"></div>
          <p>Завантаження деталей замовлення...</p>
        </div>
      </div>
    `;
  }

  renderActionButtons(order) {
    const buttons = [];

    if (['pending', 'processing', 'in_progress'].includes(order.status)) {
      buttons.push(`
        <button class="action-button cancel-button" data-action="cancel">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <span>Скасувати</span>
        </button>
      `);

      buttons.push(`
        <button class="action-button pause-button" data-action="pause">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="6" y="4" width="4" height="16"/>
            <rect x="14" y="4" width="4" height="16"/>
          </svg>
          <span>Призупинити</span>
        </button>
      `);
    } else if (order.status === 'completed') {
      buttons.push(`
        <button class="action-button primary-button" data-action="repeat">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
          </svg>
          <span>Повторити</span>
        </button>
      `);

      if (order.service?.refill) {
        buttons.push(`
          <button class="action-button secondary-button" data-action="refill">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
              <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
              <line x1="12" y1="22.08" x2="12" y2="12"/>
            </svg>
            <span>Поповнити</span>
          </button>
        `);
      }
    } else {
      buttons.push(`
        <button class="action-button primary-button" data-action="accelerate">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          <span>Прискорити</span>
        </button>
      `);
    }

    return buttons.join('');
  }

  renderTabContent(tab, order, progress) {
    switch (tab) {
      case 'overview':
        return this.renderOverviewTab(order);
      case 'progress':
        return this.renderProgressTab(order, progress);
      case 'info':
        return this.renderInfoTab(order);
      default:
        return '';
    }
  }

  renderOverviewTab(order) {
    return `
      <div class="tab-panel overview-panel">
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">Посилання</span>
            <a href="${order.link}" target="_blank" class="info-value link-value">
              ${order.link}
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                <polyline points="15 3 21 3 21 9"/>
                <line x1="10" y1="14" x2="21" y2="3"/>
              </svg>
            </a>
          </div>

          <div class="info-item">
            <span class="info-label">Категорія</span>
            <span class="info-value">${order.service?.category?.name || 'Інше'}</span>
          </div>

          <div class="info-item">
            <span class="info-label">Створено</span>
            <span class="info-value">${formatDateTime(order.created_at)}</span>
          </div>

          <div class="info-item">
            <span class="info-label">Оновлено</span>
            <span class="info-value">${formatDateTime(order.updated_at)}</span>
          </div>

          ${order.external_id ? `
            <div class="info-item">
              <span class="info-label">External ID</span>
              <span class="info-value mono">${order.external_id}</span>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  renderProgressTab(order, progress) {
    const isActive = ['pending', 'processing', 'in_progress'].includes(order.status);

    return `
      <div class="tab-panel progress-panel">
        <!-- Progress Bar -->
        <div class="progress-section">
          <div class="progress-header">
            <span>Загальний прогрес</span>
            <span class="progress-percentage">${progress}%</span>
          </div>
          <div class="progress-bar-container">
            <div class="progress-bar-fill" style="width: ${progress}%">
              ${isActive ? '<div class="progress-shimmer"></div>' : ''}
            </div>
          </div>
        </div>

        <!-- Progress Stats -->
        <div class="progress-stats">
          <div class="progress-stat">
            <span class="stat-label">Початкова кількість</span>
            <span class="stat-value">${formatNumber(order.start_count || 0)}</span>
          </div>
          <div class="progress-stat">
            <span class="stat-label">Поточна кількість</span>
            <span class="stat-value">${formatNumber((order.start_count || 0) + (order.completed || 0))}</span>
          </div>
          <div class="progress-stat">
            <span class="stat-label">Залишилось</span>
            <span class="stat-value">${formatNumber(order.remains || 0)}</span>
          </div>
        </div>

        ${isActive ? `
          <div class="speed-estimate">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
            <span>Орієнтовний час завершення: ~3 години</span>
          </div>
        ` : ''}
      </div>
    `;
  }

  renderInfoTab(order) {
    return `
      <div class="tab-panel info-panel">
        <div class="service-info">
          <h4>Інформація про сервіс</h4>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">Назва сервісу</span>
              <span class="info-value">${order.service_name}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Тип сервісу</span>
              <span class="info-value">${order.service_type || 'default'}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Мін. замовлення</span>
              <span class="info-value">${formatNumber(order.service?.min || 0)}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Макс. замовлення</span>
              <span class="info-value">${formatNumber(order.service?.max || 0)}</span>
            </div>
          </div>
        </div>

        ${order.metadata?.parameters ? `
          <div class="additional-params">
            <h4>Додаткові параметри</h4>
            <div class="params-list">
              ${Object.entries(order.metadata.parameters)
                .filter(([key, value]) => value)
                .map(([key, value]) => `
                  <div class="param-item">
                    <span class="param-key">${this.formatParamKey(key)}</span>
                    <span class="param-value">${value}</span>
                  </div>
                `).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }

  getStatIcon(type) {
    const icons = {
      ordered: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <line x1="9" y1="9" x2="15" y2="15"/>
        <line x1="15" y1="9" x2="9" y2="15"/>
      </svg>`,
      completed: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="m9 12 2 2 4-4"/>
      </svg>`,
      progress: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 1 1-6.219-8.56" stroke-linecap="round"/>
      </svg>`,
      price: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="12" y1="1" x2="12" y2="23"/>
        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
      </svg>`
    };

    return icons[type] || '';
  }

  getStatusClass(status) {
    return `status-${status}`;
  }

  getStatusText(status) {
    const texts = {
      pending: 'Очікує',
      processing: 'Обробка',
      in_progress: 'Виконується',
      completed: 'Виконано',
      partial: 'Частково',
      cancelled: 'Скасовано',
      failed: 'Помилка'
    };

    return texts[status] || status;
  }

  formatParamKey(key) {
    const labels = {
      dripfeed: 'Drip Feed',
      runs: 'Кількість запусків',
      interval: 'Інтервал',
      comments: 'Коментарі',
      answer_number: 'Номер відповіді',
      username: 'Користувач',
      min: 'Мінімум',
      max: 'Максимум',
      posts: 'Кількість постів',
      delay: 'Затримка'
    };

    return labels[key] || key;
  }

  bindEvents() {
    // Close button
    const closeBtn = this.element?.querySelector('#closeDetails');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.onClose());
    }

    // Action buttons
    this.element?.querySelectorAll('.action-button').forEach(btn => {
      btn.addEventListener('click', async () => {
        const action = btn.dataset.action;

        if (this.state.isLoading) return;

        this.setState({ isLoading: true });
        btn.disabled = true;

        try {
          await this.onAction(action, this.state.order);
        } finally {
          this.setState({ isLoading: false });
          btn.disabled = false;
        }
      });
    });

    // Tab buttons
    this.element?.querySelectorAll('.tab-button').forEach(btn => {
      btn.addEventListener('click', () => {
        this.setState({ activeTab: btn.dataset.tab });
      });
    });
  }

  async refresh() {
    try {
      this.setState({ isLoading: true });
      const response = await ordersAPI.get(this.state.order.id);

      if (response.order) {
        this.setState({
          order: response.order,
          isLoading: false
        });
      }
    } catch (error) {
      console.error('Error refreshing order:', error);
      this.setState({ isLoading: false });
    }
  }
}

// CSS для компонента
const styles = `
<style>
/* Order Details Container */
.order-details-container {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
}

/* Header */
.details-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px;
  margin-bottom: 24px;
  border-radius: 20px;
}

.header-content {
  flex: 1;
}

.service-title {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 12px;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.order-id {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  font-family: var(--font-mono);
}

.status-badge {
  padding: 6px 12px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.close-button {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.close-button:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: scale(1.1);
}

/* Stats Cards Grid */
.stats-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  padding: 20px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.08);
}

.stat-icon {
  width: 48px;
  height: 48px;
  background: rgba(168, 85, 247, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon svg {
  width: 24px;
  height: 24px;
  color: #a855f7;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: white;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Action Buttons */
.action-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.action-button {
  flex: 1;
  min-width: 150px;
  padding: 12px 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.05);
  color: white;
}

.action-button:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-1px);
}

.action-button.primary-button {
  background: linear-gradient(135deg, #a855f7 0%, #7c3aed 100%);
  border-color: transparent;
}

.action-button.primary-button:hover {
  box-shadow: 0 8px 20px rgba(168, 85, 247, 0.3);
}

.action-button.cancel-button {
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.action-button.pause-button {
  border-color: rgba(245, 158, 11, 0.3);
  color: #f59e0b;
}

.action-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Tabs */
.details-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  background: rgba(255, 255, 255, 0.03);
  padding: 4px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.tab-button {
  flex: 1;
  padding: 12px 20px;
  background: transparent;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.3s ease;
}

.tab-button:hover {
  color: white;
  background: rgba(255, 255, 255, 0.05);
}

.tab-button.active {
  background: rgba(168, 85, 247, 0.2);
  color: white;
}

/* Tab Content */
.tab-content {
  padding: 24px;
  border-radius: 20px;
  min-height: 200px;
}

.tab-panel {
  animation: fadeIn 0.3s ease;
}

/* Info Grid */
.info-grid {
  display: grid;
  gap: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.info-item:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
}

.info-value {
  font-size: 14px;
  color: white;
  font-weight: 500;
  text-align: right;
}

.info-value.link-value {
  color: #a855f7;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 4px;
}

.info-value.link-value:hover {
  color: #c084fc;
}

.info-value.mono {
  font-family: var(--font-mono);
}

/* Progress Panel */
.progress-section {
  margin-bottom: 32px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
}

.progress-percentage {
  font-weight: 700;
  color: #a855f7;
}

.progress-bar-container {
  height: 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #7c3aed 0%, #a855f7 100%);
  border-radius: 6px;
  transition: width 0.5s ease;
  position: relative;
  overflow: hidden;
}

.progress-shimmer {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: shimmer 2s infinite;
}

.progress-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.progress-stat {
  text-align: center;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.speed-estimate {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  background: rgba(168, 85, 247, 0.1);
  border-radius: 12px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
}

/* Info Panel */
.service-info,
.additional-params {
  margin-bottom: 24px;
}

.service-info:last-child,
.additional-params:last-child {
  margin-bottom: 0;
}

.service-info h4,
.additional-params h4 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: rgba(255, 255, 255, 0.9);
}

.params-list {
  display: grid;
  gap: 12px;
}

.param-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 14px;
}

.param-key {
  color: rgba(255, 255, 255, 0.5);
}

.param-value {
  color: white;
  font-weight: 500;
}

/* Loading State */
.details-loading {
  padding: 60px 20px;
  text-align: center;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  margin: 0 auto 20px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top: 3px solid #a855f7;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* Status Colors */
.status-pending,
.status-processing,
.status-in_progress {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
}

.status-completed {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.status-partial {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.status-cancelled,
.status-failed {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 480px) {
  .stats-cards-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .action-buttons {
    flex-direction: column;
  }

  .action-button {
    width: 100%;
  }

  .progress-stats {
    grid-template-columns: 1fr;
  }
}
</style>
`;

// Додаємо стилі
if (!document.getElementById('order-details-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'order-details-styles';
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}