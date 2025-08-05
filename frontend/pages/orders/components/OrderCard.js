// frontend/pages/orders/components/OrderCard.js
/**
 * OrderCard компонент у стилі Glass Morphism
 * Відображає замовлення з іконкою, статистикою та кнопкою деталей
 */

import Component from '../../../shared/core/Component.js';
import { formatNumber, formatDateTime, getTimeAgo } from '../../../shared/utils/formatters.js';
import { getServiceIcon } from '../../../shared/utils/icons.js';

export default class OrderCard extends Component {
  constructor(order, options = {}) {
    super(options);

    this.state = {
      order,
      isHovered: false,
      isUpdating: false
    };

    this.onClick = options.onClick || (() => {});
    this.onAction = options.onAction || (() => {});
  }

  render() {
    const { order, isHovered, isUpdating } = this.state;

    // Розрахунок прогресу
    const progress = order.quantity ? Math.round((order.completed / order.quantity) * 100) : 0;
    const isActive = ['pending', 'processing', 'in_progress'].includes(order.status);

    // Статус індикатор
    const statusColor = this.getStatusColor(order.status);

    return `
      <div class="order-card glass-morphism ${isHovered ? 'hovered' : ''} ${isUpdating ? 'updating' : ''}" 
           data-order-id="${order.id}">
        
        <!-- Glow Effect -->
        <div class="card-glow" style="background: ${statusColor};"></div>
        
        <!-- Service Icon with Glow -->
        <div class="service-icon-container">
          <div class="icon-glow" style="background: ${statusColor};"></div>
          <div class="service-icon">
            ${this.getServiceIconSVG(order.service?.category?.key)}
          </div>
        </div>

        <!-- Status Indicator -->
        <div class="status-indicator ${isActive ? 'active' : ''}" style="background: ${statusColor};">
          <div class="status-pulse"></div>
        </div>

        <!-- Content -->
        <div class="card-content">
          <h3 class="service-name">${order.service_name}</h3>
          <div class="order-number">Order #${order.order_number || order.id.slice(0, 6)}</div>
          
          <!-- Stats Grid -->
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-value">${formatNumber(order.quantity || 0, true)}</div>
              <div class="stat-label">TARGET</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">${formatNumber(order.completed || 0, true)}</div>
              <div class="stat-label">DELIVERED</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">${progress}%</div>
              <div class="stat-label">COMPLETE</div>
            </div>
          </div>

          <!-- Time Info -->
          <div class="time-info">
            ${isActive ? 'Started' : this.getStatusText(order.status)} ${getTimeAgo(order.created_at)}
          </div>

          <!-- Action Button -->
          <button class="view-details-btn gradient-btn" data-action="details">
            View Details
          </button>
        </div>

        <!-- Progress Ring (for active orders) -->
        ${isActive ? this.renderProgressRing(progress) : ''}
      </div>
    `;
  }

  renderProgressRing(progress) {
    const radius = 70;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (progress / 100) * circumference;

    return `
      <svg class="progress-ring" width="160" height="160">
        <defs>
          <linearGradient id="progress-gradient-${this.state.order.id}" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#a855f7;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#7c3aed;stop-opacity:1" />
          </linearGradient>
        </defs>
        <circle class="progress-ring-bg"
          stroke="rgba(255,255,255,0.1)"
          stroke-width="8"
          fill="transparent"
          r="${radius}"
          cx="80"
          cy="80"
        />
        <circle class="progress-ring-fill"
          stroke="url(#progress-gradient-${this.state.order.id})"
          stroke-width="8"
          fill="transparent"
          r="${radius}"
          cx="80"
          cy="80"
          stroke-dasharray="${circumference}"
          stroke-dashoffset="${offset}"
          stroke-linecap="round"
          transform="rotate(-90 80 80)"
        />
      </svg>
    `;
  }

  getServiceIconSVG(category) {
    const icons = {
      instagram: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
        <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
        <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>
      </svg>`,
      telegram: `<svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M21.198 2.433a2.242 2.242 0 0 0-1.022.215l-8.609 3.33c-2.068.8-4.133 1.598-5.724 2.21a405.15 405.15 0 0 1-2.849 1.09c-.42.147-.99.332-1.473.901-.728.968.193 1.798.919 2.112 1.058.46 2.06.745 3.059 1.122 1.074.409 2.156.842 3.23 1.295l-.138-.03c.265.624.535 1.239.804 1.858.382.883.761 1.769 1.137 2.663.19.448.521 1.05 1.08 1.246.885.32 1.694-.244 2.122-.715l1.358-1.493c.858.64 1.708 1.271 2.558 1.921l.033.025c1.153.865 1.805 1.354 2.495 1.592.728.25 1.361.151 1.88-.253.506-.395.748-.987.818-1.486.308-2.17.63-4.335.919-6.507.316-2.378.63-4.764.867-7.158.094-.952.187-1.912.272-2.875.046-.523.153-1.308-.327-1.83a1.743 1.743 0 0 0-.965-.465z"/>
      </svg>`,
      youtube: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z"/>
        <polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02"/>
      </svg>`,
      tiktok: `<svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
      </svg>`,
      facebook: `<svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
      </svg>`,
      default: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="3"/>
        <path d="M12 1v6m0 6v6m4.22-10.22l4.24-4.24M6.34 18.66l4.24-4.24m0 4.24l-4.24 4.24M18.66 6.34l-4.24 4.24"/>
      </svg>`
    };

    return icons[category] || icons.default;
  }

  getStatusColor(status) {
    const colors = {
      pending: '#3b82f6',
      processing: '#8b5cf6',
      in_progress: '#06b6d4',
      completed: '#22c55e',
      partial: '#f59e0b',
      cancelled: '#ef4444',
      failed: '#dc2626'
    };

    return colors[status] || '#6b7280';
  }

  getStatusText(status) {
    const texts = {
      pending: 'Created',
      processing: 'Processing',
      in_progress: 'In Progress',
      completed: 'Completed',
      partial: 'Partially completed',
      cancelled: 'Cancelled',
      failed: 'Failed'
    };

    return texts[status] || status;
  }

  bindEvents() {
    const card = this.element;
    if (!card) return;

    // Hover effects
    card.addEventListener('mouseenter', () => {
      this.setState({ isHovered: true });
    });

    card.addEventListener('mouseleave', () => {
      this.setState({ isHovered: false });
    });

    // Click handler
    card.addEventListener('click', (e) => {
      // Не викликаємо onClick якщо клікнули на кнопку
      if (!e.target.closest('button')) {
        this.onClick(this.state.order);
      }
    });

    // Button click
    const detailsBtn = card.querySelector('.view-details-btn');
    if (detailsBtn) {
      detailsBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.onAction('details', this.state.order);
      });
    }
  }

  update(order) {
    // Анімація оновлення
    this.setState({ isUpdating: true });

    setTimeout(() => {
      this.setState({
        order,
        isUpdating: false
      });
    }, 300);
  }
}

// CSS для компонента
const styles = `
<style>
/* Order Card Glass Morphism */
.order-card.glass-morphism {
  position: relative;
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  padding: 32px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  cursor: pointer;
}

.order-card.glass-morphism:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.12);
  transform: translateY(-4px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.order-card.updating {
  animation: pulse 0.6s ease-out;
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.02); }
  100% { transform: scale(1); }
}

/* Card Glow */
.card-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  opacity: 0.1;
  filter: blur(100px);
  pointer-events: none;
  transition: opacity 0.3s ease;
}

.order-card:hover .card-glow {
  opacity: 0.2;
}

/* Service Icon */
.service-icon-container {
  position: relative;
  width: 80px;
  height: 80px;
  margin-bottom: 24px;
}

.icon-glow {
  position: absolute;
  inset: -20px;
  border-radius: 50%;
  opacity: 0.3;
  filter: blur(20px);
}

.service-icon {
  width: 80px;
  height: 80px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
}

.service-icon svg {
  width: 40px;
  height: 40px;
  color: white;
}

/* Status Indicator */
.status-indicator {
  position: absolute;
  top: 32px;
  right: 32px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-indicator.active .status-pulse {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  background: inherit;
  opacity: 0.4;
  animation: statusPulse 2s ease-out infinite;
}

@keyframes statusPulse {
  0% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1.5); opacity: 0; }
  100% { transform: scale(1.5); opacity: 0; }
}

/* Content */
.card-content {
  position: relative;
  z-index: 1;
}

.service-name {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
  color: white;
}

.order-number {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 32px;
  font-family: var(--font-mono);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 32px;
}

.stat-item {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 16px;
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: white;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Time Info */
.time-info {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 24px;
}

/* View Details Button */
.view-details-btn {
  width: 100%;
  padding: 16px 24px;
  background: linear-gradient(135deg, #a855f7 0%, #7c3aed 100%);
  border: none;
  border-radius: 16px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.view-details-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 0.6s ease;
}

.view-details-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(168, 85, 247, 0.4);
}

.view-details-btn:hover::before {
  left: 100%;
}

/* Progress Ring */
.progress-ring {
  position: absolute;
  top: 50%;
  right: -80px;
  transform: translateY(-50%);
  opacity: 0.3;
}

/* Responsive */
@media (max-width: 480px) {
  .order-card.glass-morphism {
    padding: 24px;
  }

  .stats-grid {
    gap: 12px;
  }

  .stat-value {
    font-size: 20px;
  }

  .progress-ring {
    display: none;
  }
}
</style>
`;

// Додаємо стилі
if (!document.getElementById('order-card-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'order-card-styles';
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}