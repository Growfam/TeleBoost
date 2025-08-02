// frontend/pages/home/components/ServicesGrid.js
/**
 * Компонент сетки популярных сервисов
 */

import { getIcon } from '../../../shared/ui/svg.js';

export default class ServicesGrid {
  constructor(options = {}) {
    this.state = {
      services: options.services || [],
      isLoading: options.isLoading || false,
      selectedService: null
    };

    this.callbacks = {
      onServiceClick: options.onServiceClick || (() => {})
    };

    this.element = null;
  }

  /**
   * Рендер компонента
   */
  render() {
    if (this.state.isLoading) {
      return this.renderSkeleton();
    }

    if (this.state.services.length === 0) {
      return this.renderEmpty();
    }

    return `
      <div class="services-grid" id="services-grid">
        ${this.state.services.map(service => this.renderServiceCard(service)).join('')}
      </div>
    `;
  }

  /**
   * Рендер карточки сервиса
   */
  renderServiceCard(service) {
    const icon = this.getServiceIcon(service.name);
    const isPopular = this.isPopularService(service);

    return `
      <div class="service-card glass-card ${isPopular ? 'popular pulse' : ''}" 
           data-service-id="${service.id}"
           data-service-name="${service.name}">
        ${isPopular ? '<div class="service-badge">ХИТ</div>' : ''}
        <div class="service-icon-wrapper">
          <div class="service-icon">
            ${icon}
          </div>
        </div>
        <div class="service-info">
          <div class="service-name">${this.formatServiceName(service.name)}</div>
          <div class="service-price">от $${this.formatPrice(service.rate)}</div>
          <div class="service-meta">
            <span class="service-min">${service.min.toLocaleString('ru-RU')}</span>
            <span class="service-separator">—</span>
            <span class="service-max">${service.max.toLocaleString('ru-RU')}</span>
          </div>
        </div>
        <div class="service-hover-effect"></div>
      </div>
    `;
  }

  /**
   * Получить иконку для сервиса
   */
  getServiceIcon(serviceName) {
    const name = serviceName.toLowerCase();

    if (name.includes('подписчик') || name.includes('subscriber') || name.includes('member')) {
      return getIcon('subscribers', 'service-icon-svg', 40);
    } else if (name.includes('просмотр') || name.includes('view')) {
      return getIcon('views', 'service-icon-svg', 40);
    } else if (name.includes('реакц') || name.includes('reaction') || name.includes('like')) {
      return getIcon('reactions', 'service-icon-svg', 40);
    } else if (name.includes('бот') || name.includes('bot')) {
      return getIcon('botStart', 'service-icon-svg', 40);
    } else if (name.includes('коммент') || name.includes('comment')) {
      return getIcon('telegram', 'service-icon-svg', 40);
    } else {
      return getIcon('telegram', 'service-icon-svg', 40);
    }
  }

  /**
   * Форматирование имени сервиса
   */
  formatServiceName(name) {
    // Убираем префиксы типа "Telegram: "
    let formatted = name.replace(/^(Telegram|Телеграм):\s*/i, '');

    // Сокращаем длинные названия
    if (formatted.length > 30) {
      formatted = formatted.substring(0, 27) + '...';
    }

    return formatted;
  }

  /**
   * Форматирование цены
   */
  formatPrice(rate) {
    // rate указан за 1000, показываем минимальную цену
    const minPrice = rate / 1000;
    return minPrice < 0.01 ? '0.01' : minPrice.toFixed(2);
  }

  /**
   * Проверка популярности сервиса
   */
  isPopularService(service) {
    const popularKeywords = ['подписчик', 'subscriber', 'member', 'просмотр', 'view'];
    return popularKeywords.some(keyword =>
      service.name.toLowerCase().includes(keyword)
    );
  }

  /**
   * Рендер skeleton loader
   */
  renderSkeleton() {
    return `
      <div class="services-grid services-skeleton">
        ${Array(4).fill(0).map(() => `
          <div class="skeleton-service-card">
            <div class="skeleton-icon"></div>
            <div class="skeleton-line" style="width: 70%;"></div>
            <div class="skeleton-line" style="width: 50%;"></div>
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
          ${getIcon('services', '', 64)}
        </div>
        <div class="empty-state-text">Сервисы временно недоступны</div>
        <div class="empty-state-subtext">Попробуйте обновить страницу</div>
      </div>
    `;
  }

  /**
   * Инициализация после рендера
   */
  init() {
    this.element = document.getElementById('services-grid');
    if (!this.element) return;

    // Добавляем обработчики на карточки
    const cards = this.element.querySelectorAll('.service-card');
    cards.forEach((card, index) => {
      card.addEventListener('click', (e) => {
        const serviceId = card.dataset.serviceId;
        const service = this.state.services.find(s => s.id == serviceId);

        if (service) {
          this.animateCard(card);
          this.callbacks.onServiceClick(service);
        }
      });

      // Добавляем задержку анимации появления
      card.style.animationDelay = `${index * 0.1}s`;
    });
  }

  /**
   * Обновление компонента
   */
  update(newState) {
    Object.assign(this.state, newState);

    // Перерендериваем компонент
    if (this.element) {
      const parent = this.element.parentElement;
      parent.innerHTML = this.render();
      this.init();
    }
  }

  /**
   * Анимация карточки при клике
   */
  animateCard(card) {
    card.classList.add('service-card-click');
    setTimeout(() => {
      card.classList.remove('service-card-click');
    }, 300);
  }

  /**
   * Уничтожение компонента
   */
  destroy() {
    if (this.element) {
      this.element.remove();
    }
  }
}

// Дополнительные стили для компонента
const styles = `
<style>
.services-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.service-card {
  position: relative;
  padding: 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
  animation: slideUp 0.6s ease-out both;
}

.service-card:hover {
  transform: translateY(-5px);
  background: var(--glass-bg-hover);
  border-color: rgba(var(--primary-rgb), 0.5);
}

.service-card.popular {
  background: linear-gradient(135deg, 
    rgba(var(--primary-rgb), 0.05) 0%, 
    rgba(var(--secondary-rgb), 0.05) 100%
  );
  border-color: rgba(var(--primary-rgb), 0.3);
}

.service-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: var(--gradient-primary);
  color: white;
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  z-index: 2;
}

.service-icon-wrapper {
  width: 60px;
  height: 60px;
  margin: 0 auto 12px;
  background: var(--glass-bg-active);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all 0.3s ease;
}

.service-card:hover .service-icon-wrapper {
  background: rgba(var(--primary-rgb), 0.1);
  transform: scale(1.1);
}

.service-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-light);
}

.service-icon-svg {
  width: 40px;
  height: 40px;
  transition: all 0.3s ease;
}

.service-info {
  position: relative;
  z-index: 1;
}

.service-name {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--text-primary);
  line-height: 1.3;
}

.service-price {
  font-size: 18px;
  font-weight: 700;
  color: var(--primary-light);
  margin-bottom: 8px;
}

.service-meta {
  font-size: 12px;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.service-separator {
  opacity: 0.5;
}

.service-hover-effect {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  background: radial-gradient(circle, rgba(var(--primary-rgb), 0.2) 0%, transparent 70%);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  transition: all 0.5s ease;
  pointer-events: none;
}

.service-card:hover .service-hover-effect {
  width: 200px;
  height: 200px;
}

.service-card-click {
  animation: cardClick 0.3s ease;
}

@keyframes cardClick {
  0% { transform: scale(1); }
  50% { transform: scale(0.95); }
  100% { transform: scale(1); }
}

/* Skeleton стили */
.skeleton-service-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
}

.skeleton-icon {
  width: 60px;
  height: 60px;
  background: var(--glass-bg-active);
  border-radius: var(--radius-lg);
  margin-bottom: 4px;
}

/* Mobile responsive */
@media (max-width: 380px) {
  .services-grid {
    grid-template-columns: 1fr;
  }
}

/* Анимация пульсации для популярных */
.popular.pulse .service-icon-wrapper {
  animation: iconPulse 2s ease-in-out infinite;
}

@keyframes iconPulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(var(--primary-rgb), 0.4);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 0 10px rgba(var(--primary-rgb), 0);
  }
}
</style>
`;

// Добавляем стили в документ
if (!document.getElementById('services-grid-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'services-grid-styles';
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}