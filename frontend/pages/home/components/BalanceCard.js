// frontend/pages/home/components/BalanceCard.js
/**
 * Компонент карточки баланса
 */

import { getIcon } from '../../../shared/ui/svg.js';

export default class BalanceCard {
  constructor(options = {}) {
    this.state = {
      balance: options.balance || 0,
      currency: options.currency || 'USD',
      isLoading: false,
      previousBalance: options.balance || 0
    };

    this.callbacks = {
      onDeposit: options.onDeposit || (() => {}),
      onHistory: options.onHistory || (() => {})
    };

    this.element = null;
    this.animationTimeout = null;
  }

  /**
   * Рендер компонента
   */
  render() {
    return `
      <div class="balance-card glass-card ${this.state.isLoading ? 'loading' : ''}" id="balance-card">
        <div class="balance-card-content">
          <div class="balance-label">Ваш баланс</div>
          <div class="balance-amount ${this.getBalanceClass()}" id="balance-amount">
            ${this.formatBalance()}
          </div>
          <div class="balance-change" id="balance-change" style="display: none;">
            <span class="change-icon"></span>
            <span class="change-amount"></span>
          </div>
          <div class="balance-actions">
            <button class="btn btn-primary balance-btn" id="deposit-btn">
              <span class="btn-icon">${getIcon('plus', '', 20)}</span>
              <span>Пополнить</span>
            </button>
            <button class="btn btn-secondary balance-btn" id="history-btn">
              <span class="btn-icon">${getIcon('history', '', 20)}</span>
              <span>История</span>
            </button>
          </div>
        </div>
        ${this.renderBalancePattern()}
      </div>
    `;
  }

  /**
   * Паттерн для фона карточки
   */
  renderBalancePattern() {
    return `
      <div class="balance-pattern">
        <svg width="100%" height="100%" style="position: absolute; top: 0; left: 0; opacity: 0.1;">
          <defs>
            <pattern id="balance-pattern" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
              <circle cx="20" cy="20" r="1" fill="currentColor" opacity="0.5"/>
              <circle cx="0" cy="0" r="1" fill="currentColor" opacity="0.5"/>
              <circle cx="40" cy="0" r="1" fill="currentColor" opacity="0.5"/>
              <circle cx="0" cy="40" r="1" fill="currentColor" opacity="0.5"/>
              <circle cx="40" cy="40" r="1" fill="currentColor" opacity="0.5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#balance-pattern)"/>
        </svg>
      </div>
    `;
  }

  /**
   * Инициализация после рендера
   */
  init() {
    this.element = document.getElementById('balance-card');
    if (!this.element) return;

    // Добавляем обработчики
    const depositBtn = document.getElementById('deposit-btn');
    const historyBtn = document.getElementById('history-btn');

    if (depositBtn) {
      depositBtn.addEventListener('click', () => {
        this.animateButton(depositBtn);
        this.callbacks.onDeposit();
      });
    }

    if (historyBtn) {
      historyBtn.addEventListener('click', () => {
        this.animateButton(historyBtn);
        this.callbacks.onHistory();
      });
    }
  }

  /**
   * Обновление компонента
   */
  update(newState) {
    const oldBalance = this.state.balance;
    Object.assign(this.state, newState);

    // Обновляем баланс с анимацией
    if (newState.balance !== undefined && newState.balance !== oldBalance) {
      this.animateBalanceChange(oldBalance, newState.balance);
    }

    // Обновляем кнопки если изменилось состояние загрузки
    if (newState.isLoading !== undefined) {
      this.updateLoadingState();
    }
  }

  /**
   * Анимация изменения баланса
   */
  animateBalanceChange(oldValue, newValue) {
    const amountElement = document.getElementById('balance-amount');
    const changeElement = document.getElementById('balance-change');

    if (!amountElement || !changeElement) return;

    const difference = newValue - oldValue;
    const isIncrease = difference > 0;

    // Показываем изменение
    const changeIcon = changeElement.querySelector('.change-icon');
    const changeAmount = changeElement.querySelector('.change-amount');

    changeIcon.innerHTML = getIcon(isIncrease ? 'arrowUp' : 'arrowDown', '', 16);
    changeAmount.textContent = `${isIncrease ? '+' : ''}${difference.toFixed(2)} ${this.state.currency}`;

    changeElement.style.display = 'flex';
    changeElement.className = `balance-change ${isIncrease ? 'increase' : 'decrease'} animate-fadeInUp`;

    // Анимируем число
    this.animateValue(amountElement, oldValue, newValue, 1000);

    // Добавляем пульсацию
    amountElement.classList.add('pulse');

    // Скрываем изменение через 3 секунды
    clearTimeout(this.animationTimeout);
    this.animationTimeout = setTimeout(() => {
      changeElement.style.display = 'none';
      amountElement.classList.remove('pulse');
    }, 3000);
  }

  /**
   * Анимация числового значения
   */
  animateValue(element, start, end, duration) {
    const startTime = performance.now();

    const update = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      const currentValue = start + (end - start) * progress;
      element.textContent = this.formatBalance(currentValue);

      if (progress < 1) {
        requestAnimationFrame(update);
      }
    };

    requestAnimationFrame(update);
  }

  /**
   * Форматирование баланса
   */
  formatBalance(value = this.state.balance) {
    return `${this.state.currency} ${value.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
  }

  /**
   * Получить класс для баланса
   */
  getBalanceClass() {
    if (this.state.balance === 0) return 'balance-zero';
    if (this.state.balance < 10) return 'balance-low';
    return '';
  }

  /**
   * Анимация кнопки
   */
  animateButton(button) {
    button.classList.add('btn-click');
    setTimeout(() => {
      button.classList.remove('btn-click');
    }, 300);
  }

  /**
   * Обновление состояния загрузки
   */
  updateLoadingState() {
    if (this.element) {
      if (this.state.isLoading) {
        this.element.classList.add('loading');
      } else {
        this.element.classList.remove('loading');
      }
    }
  }

  /**
   * Уничтожение компонента
   */
  destroy() {
    clearTimeout(this.animationTimeout);
    if (this.element) {
      this.element.remove();
    }
  }
}

// Дополнительные стили для компонента
const styles = `
<style>
.balance-card {
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

.balance-card-content {
  position: relative;
  z-index: 1;
}

.balance-label {
  font-size: 14px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.balance-amount {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 8px;
  background: linear-gradient(135deg, #fff 0%, #e9d5ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  transition: all 0.3s ease;
}

.balance-amount.balance-zero {
  opacity: 0.5;
}

.balance-amount.balance-low {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.balance-change {
  display: none;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 20px;
}

.balance-change.increase {
  color: var(--success);
}

.balance-change.decrease {
  color: var(--error);
}

.change-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
}

.balance-actions {
  display: flex;
  gap: 12px;
}

.balance-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
}

.btn-click {
  animation: buttonClick 0.3s ease;
}

@keyframes buttonClick {
  0% { transform: scale(1); }
  50% { transform: scale(0.95); }
  100% { transform: scale(1); }
}

.balance-pattern {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  color: var(--primary);
  pointer-events: none;
}

.balance-card.loading::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  100% { left: 100%; }
}
</style>
`;

// Добавляем стили в документ
if (!document.getElementById('balance-card-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'balance-card-styles';
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}