// frontend/shared/utils/formatters.js
/**
 * Форматери для TeleBoost
 * Функції для форматування різних типів даних
 */

import { LOCALE } from './constants.js';

/**
 * Форматування чисел з скороченням
 */
export function formatNumber(num, short = false) {
  if (!num && num !== 0) return '0';

  const number = parseFloat(num);

  if (short && number >= 1000000) {
    return (number / 1000000).toFixed(1) + 'M';
  } else if (short && number >= 1000) {
    return (number / 1000).toFixed(1) + 'K';
  }

  return number.toLocaleString('uk-UA');
}

/**
 * Форматування ціни
 */
export function formatPrice(amount, currency = LOCALE.CURRENCY) {
  if (!amount && amount !== 0) return `${LOCALE.CURRENCY_SYMBOL}0`;

  const symbols = {
    UAH: '₴',
    USD: '$',
    EUR: '€',
    GBP: '£'
  };

  const symbol = symbols[currency] || currency;
  const formatted = parseFloat(amount).toFixed(2);

  return `${symbol}${formatted}`;
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
    return `${diffDays} ${pluralize(diffDays, 'день', 'дні', 'днів')} тому`;
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
 * Форматування дати
 */
export function formatDate(dateString) {
  if (!dateString) return '';

  const date = new Date(dateString);
  return date.toLocaleDateString('uk-UA', {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  });
}

/**
 * Форматування часу
 */
export function formatTime(dateString) {
  if (!dateString) return '';

  const date = new Date(dateString);
  return date.toLocaleTimeString('uk-UA', {
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
  const weeks = Math.floor(days / 7);
  const months = Math.floor(days / 30);
  const years = Math.floor(days / 365);

  if (years > 0) {
    return `${years} ${pluralize(years, 'рік', 'роки', 'років')} тому`;
  } else if (months > 0) {
    return `${months} ${pluralize(months, 'місяць', 'місяці', 'місяців')} тому`;
  } else if (weeks > 0) {
    return `${weeks} ${pluralize(weeks, 'тиждень', 'тижні', 'тижнів')} тому`;
  } else if (days > 0) {
    return `${days} ${pluralize(days, 'день', 'дні', 'днів')} тому`;
  } else if (hours > 0) {
    return `${hours} ${pluralize(hours, 'годину', 'години', 'годин')} тому`;
  } else if (minutes > 0) {
    return `${minutes} ${pluralize(minutes, 'хвилину', 'хвилини', 'хвилин')} тому`;
  } else if (seconds > 0) {
    return `${seconds} ${pluralize(seconds, 'секунду', 'секунди', 'секунд')} тому`;
  } else {
    return 'щойно';
  }
}

/**
 * Форматування тривалості
 */
export function formatDuration(seconds) {
  if (!seconds || seconds < 0) return '0 сек';

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const parts = [];
  if (hours > 0) parts.push(`${hours} год`);
  if (minutes > 0) parts.push(`${minutes} хв`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs} сек`);

  return parts.join(' ');
}

/**
 * Pluralize українською
 */
export function pluralize(count, one, few, many) {
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

/**
 * Форматування відсотків
 */
export function formatPercent(value, decimals = 0) {
  if (!value && value !== 0) return '0%';
  return `${parseFloat(value).toFixed(decimals)}%`;
}

/**
 * Форматування розміру файлу
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Форматування телефону
 */
export function formatPhone(phone) {
  if (!phone) return '';

  // Видаляємо всі не-цифри
  const cleaned = phone.replace(/\D/g, '');

  // Форматуємо як +380 XX XXX XX XX
  if (cleaned.startsWith('380') && cleaned.length === 12) {
    return `+${cleaned.slice(0, 3)} ${cleaned.slice(3, 5)} ${cleaned.slice(5, 8)} ${cleaned.slice(8, 10)} ${cleaned.slice(10)}`;
  }

  // Інші формати повертаємо як є
  return phone;
}

/**
 * Обрізати текст
 */
export function truncate(text, length = 50, suffix = '...') {
  if (!text) return '';
  if (text.length <= length) return text;
  return text.slice(0, length - suffix.length) + suffix;
}

/**
 * Форматування URL
 */
export function formatUrl(url) {
  if (!url) return '';

  try {
    const urlObj = new URL(url);
    return urlObj.hostname + (urlObj.pathname !== '/' ? urlObj.pathname : '');
  } catch {
    return url;
  }
}

/**
 * Капіталізація першої літери
 */
export function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

/**
 * Форматування списку
 */
export function formatList(items, separator = ', ', lastSeparator = ' та ') {
  if (!items || items.length === 0) return '';
  if (items.length === 1) return items[0];
  if (items.length === 2) return items.join(lastSeparator);

  const lastItem = items[items.length - 1];
  const otherItems = items.slice(0, -1);

  return otherItems.join(separator) + lastSeparator + lastItem;
}

/**
 * Форматування банківської картки
 */
export function formatCardNumber(cardNumber) {
  if (!cardNumber) return '';

  const cleaned = cardNumber.replace(/\s/g, '');
  const groups = cleaned.match(/.{1,4}/g) || [];

  return groups.join(' ');
}

/**
 * Маскування даних
 */
export function maskData(data, visibleStart = 4, visibleEnd = 4) {
  if (!data || data.length <= visibleStart + visibleEnd) return data;

  const start = data.slice(0, visibleStart);
  const end = data.slice(-visibleEnd);
  const masked = '*'.repeat(Math.max(4, data.length - visibleStart - visibleEnd));

  return start + masked + end;
}

/**
 * Форматування статусу
 */
export function formatStatus(status) {
  if (!status) return '';

  return status
    .split('_')
    .map(word => capitalize(word))
    .join(' ');
}

// Експортуємо всі функції
export default {
  formatNumber,
  formatPrice,
  formatDateTime,
  formatDate,
  formatTime,
  getTimeAgo,
  formatDuration,
  pluralize,
  formatPercent,
  formatFileSize,
  formatPhone,
  truncate,
  formatUrl,
  capitalize,
  formatList,
  formatCardNumber,
  maskData,
  formatStatus
};