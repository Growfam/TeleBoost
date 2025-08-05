// frontend/shared/utils/formatters.js (додаток до існуючого файлу)
/**
 * Форматери для замовлень
 * Додаткові функції для форматування даних
 */

/**
 * Форматування чисел з скороченням
 */
export function formatNumber(num, short = false) {
  if (!num) return '0';

  if (short && num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  } else if (short && num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }

  return num.toLocaleString('uk-UA');
}

/**
 * Форматування ціни
 */
export function formatPrice(amount, currency = 'UAH') {
  if (!amount) return '₴0';

  const symbols = {
    UAH: '₴',
    USD: '$',
    EUR: '€'
  };

  const symbol = symbols[currency] || currency;
  return `${symbol}${amount.toFixed(2)}`;
}

/**
 * Форматування дати та часу
 */
export function formatDateTime(dateString) {
  if (!dateString) return '';

  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  // Сьогодні
  if (diffDays === 0) {
    return `Сьогодні, ${date.toLocaleTimeString('uk-UA', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })}`;
  }

  // Вчора
  if (diffDays === 1) {
    return `Вчора, ${date.toLocaleTimeString('uk-UA', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })}`;
  }

  // Цього тижня
  if (diffDays < 7) {
    return `${diffDays} днів тому`;
  }

  // Інші дати
  return date.toLocaleDateString('uk-UA', {
    day: 'numeric',
    month: 'short',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * Отримати час тому
 */
export function getTimeAgo(dateString) {
  if (!dateString) return '';

  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;

  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) {
    return `${days} ${pluralize(days, 'день', 'дні', 'днів')} тому`;
  } else if (hours > 0) {
    return `${hours} ${pluralize(hours, 'годину', 'години', 'годин')} тому`;
  } else if (minutes > 0) {
    return `${minutes} ${pluralize(minutes, 'хвилину', 'хвилини', 'хвилин')} тому`;
  } else {
    return 'щойно';
  }
}

/**
 * Pluralize українською
 */
function pluralize(count, one, few, many) {
  const lastDigit = count % 10;
  const lastTwoDigits = count % 100;

  if (lastTwoDigits >= 11 && lastTwoDigits <= 19) {
    return many;
  } else if (lastDigit === 1) {
    return one;
  } else if (lastDigit >= 2 && lastDigit <= 4) {
    return few;
  } else {
    return many;
  }
}

// frontend/shared/utils/constants.js (додаток до існуючого файлу)
/**
 * Константи для замовлень
 */

export const ORDER_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  PARTIAL: 'partial',
  CANCELLED: 'cancelled',
  FAILED: 'failed'
};

export const ORDER_STATUS_LABELS = {
  [ORDER_STATUS.PENDING]: 'Очікує',
  [ORDER_STATUS.PROCESSING]: 'Обробка',
  [ORDER_STATUS.IN_PROGRESS]: 'Виконується',
  [ORDER_STATUS.COMPLETED]: 'Виконано',
  [ORDER_STATUS.PARTIAL]: 'Частково',
  [ORDER_STATUS.CANCELLED]: 'Скасовано',
  [ORDER_STATUS.FAILED]: 'Помилка'
};

export const SERVICE_CATEGORIES = {
  TELEGRAM: 'telegram',
  INSTAGRAM: 'instagram',
  YOUTUBE: 'youtube',
  TIKTOK: 'tiktok',
  FACEBOOK: 'facebook',
  TWITTER: 'twitter'
};

// frontend/shared/utils/helpers.js
/**
 * Допоміжні функції
 */

/**
 * Debounce функція
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle функція
 */
export function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Deep clone об'єкта
 */
export function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') return obj;
  if (obj instanceof Date) return new Date(obj.getTime());
  if (obj instanceof Array) return obj.map(item => deepClone(item));
  if (obj instanceof Object) {
    const clonedObj = {};
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        clonedObj[key] = deepClone(obj[key]);
      }
    }
    return clonedObj;
  }
}

/**
 * Generate unique ID
 */
export function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// frontend/shared/utils/icons.js
/**
 * Іконки для сервісів
 */

export function getServiceIcon(category) {
  const icons = {
    telegram: `<svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M21.198 2.433a2.242 2.242 0 0 0-1.022.215l-8.609 3.33c-2.068.8-4.133 1.598-5.724 2.21a405.15 405.15 0 0 1-2.849 1.09c-.42.147-.99.332-1.473.901-.728.968.193 1.798.919 2.112 1.058.46 2.06.745 3.059 1.122 1.074.409 2.156.842 3.23 1.295l-.138-.03c.265.624.535 1.239.804 1.858.382.883.761 1.769 1.137 2.663.19.448.521 1.05 1.08 1.246.885.32 1.694-.244 2.122-.715l1.358-1.493c.858.64 1.708 1.271 2.558 1.921l.033.025c1.153.865 1.805 1.354 2.495 1.592.728.25 1.361.151 1.88-.253.506-.395.748-.987.818-1.486.308-2.17.63-4.335.919-6.507.316-2.378.63-4.764.867-7.158.094-.952.187-1.912.272-2.875.046-.523.153-1.308-.327-1.83a1.743 1.743 0 0 0-.965-.465z"/>
    </svg>`,

    instagram: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
      <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
      <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>
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

    twitter: `<svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/>
    </svg>`,

    default: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="3" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/>
    </svg>`
  };

  return icons[category] || icons.default;
}