// frontend/shared/utils/constants.js
/**
 * Константи для TeleBoost
 */

// Статуси замовлень
export const ORDER_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  PARTIAL: 'partial',
  CANCELLED: 'cancelled',
  FAILED: 'failed'
};

// Лейбли статусів
export const ORDER_STATUS_LABELS = {
  [ORDER_STATUS.PENDING]: 'Очікує',
  [ORDER_STATUS.PROCESSING]: 'Обробка',
  [ORDER_STATUS.IN_PROGRESS]: 'Виконується',
  [ORDER_STATUS.COMPLETED]: 'Виконано',
  [ORDER_STATUS.PARTIAL]: 'Частково',
  [ORDER_STATUS.CANCELLED]: 'Скасовано',
  [ORDER_STATUS.FAILED]: 'Помилка'
};

// Категорії сервісів
export const SERVICE_CATEGORIES = {
  TELEGRAM: 'telegram',
  INSTAGRAM: 'instagram',
  YOUTUBE: 'youtube',
  TIKTOK: 'tiktok',
  FACEBOOK: 'facebook',
  TWITTER: 'twitter'
};

// Типи сервісів
export const SERVICE_TYPES = {
  DEFAULT: 'default',
  PACKAGE: 'package',
  CUSTOM_DATA: 'custom_data',
  SUBSCRIPTIONS: 'subscriptions',
  CUSTOM_COMMENTS: 'custom_comments',
  MENTIONS: 'mentions',
  PACKAGE_CUSTOM_COMMENTS: 'package_custom_comments',
  COMMENT_LIKES: 'comment_likes',
  POLL: 'poll',
  INVITES: 'invites',
  GROUPS: 'groups'
};

// Типи транзакцій
export const TRANSACTION_TYPES = {
  DEPOSIT: 'deposit',
  WITHDRAWAL: 'withdrawal',
  ORDER: 'order',
  REFUND: 'refund',
  BONUS: 'bonus',
  REFERRAL_BONUS: 'referral_bonus'
};

// Статуси транзакцій
export const TRANSACTION_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
};

// Методи оплати
export const PAYMENT_METHODS = {
  CRYPTO: 'crypto',
  CARD: 'card',
  WALLET: 'wallet'
};

// API endpoints
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    TELEGRAM: '/auth/telegram',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
    VERIFY: '/auth/verify',
    ME: '/auth/me'
  },
  ORDERS: {
    LIST: '/orders',
    CREATE: '/orders',
    GET: (id) => `/orders/${id}`,
    CANCEL: (id) => `/orders/${id}/cancel`,
    REFILL: (id) => `/orders/${id}/refill`,
    STATUS: (id) => `/orders/${id}/status`,
    STATISTICS: '/orders/statistics',
    HISTORY: '/orders/history',
    EXPORT: '/orders/export'
  },
  SERVICES: {
    LIST: '/services',
    GET: (id) => `/services/${id}`,
    BY_CATEGORY: (category) => `/services/category/${category}`,
    SEARCH: '/services/search'
  },
  BALANCE: {
    GET: '/balance',
    HISTORY: '/balance/history',
    DEPOSIT: '/balance/deposit',
    WITHDRAWAL: '/balance/withdrawal'
  },
  USERS: {
    PROFILE: '/users/profile',
    UPDATE: '/users/profile',
    REFERRALS: '/users/referrals',
    NOTIFICATIONS: '/users/notifications'
  }
};

// Повідомлення помилок
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Помилка мережі. Перевірте інтернет-з\'єднання',
  AUTH_REQUIRED: 'Необхідна авторизація',
  INVALID_CREDENTIALS: 'Невірні дані для входу',
  SERVER_ERROR: 'Помилка сервера. Спробуйте пізніше',
  VALIDATION_ERROR: 'Перевірте правильність введених даних',
  INSUFFICIENT_BALANCE: 'Недостатньо коштів на балансі',
  ORDER_NOT_FOUND: 'Замовлення не знайдено',
  SERVICE_NOT_FOUND: 'Сервіс не знайдено',
  RATE_LIMIT: 'Забагато запитів. Спробуйте пізніше'
};

// Локалізація
export const LOCALE = {
  CURRENCY: 'UAH',
  CURRENCY_SYMBOL: '₴',
  DATE_FORMAT: 'DD.MM.YYYY',
  TIME_FORMAT: 'HH:mm',
  DATETIME_FORMAT: 'DD.MM.YYYY HH:mm',
  DECIMAL_SEPARATOR: ',',
  THOUSANDS_SEPARATOR: ' '
};

// Telegram
export const TELEGRAM = {
  BOT_USERNAME: window.CONFIG?.BOT_USERNAME || 'TeleeBoost_bot',
  WEB_APP_VERSION: '6.9',
  THEME_PARAMS: {
    bg_color: '#000000',
    text_color: '#ffffff',
    hint_color: '#999999',
    link_color: '#7c3aed',
    button_color: '#7c3aed',
    button_text_color: '#ffffff'
  }
};

// Обмеження
export const LIMITS = {
  MIN_DEPOSIT: 50,
  MAX_DEPOSIT: 100000,
  MIN_WITHDRAWAL: 100,
  MAX_WITHDRAWAL: 50000,
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  MAX_COMMENT_LENGTH: 1000,
  MAX_ORDERS_PER_PAGE: 20,
  MAX_SERVICES_PER_PAGE: 50
};

// Час кешування (в мілісекундах)
export const CACHE_TTL = {
  SERVICES: 3600000, // 1 година
  ORDERS: 180000, // 3 хвилини
  USER: 300000, // 5 хвилин
  BALANCE: 60000, // 1 хвилина
  STATISTICS: 600000 // 10 хвилин
};

// Регулярні вирази
export const REGEX = {
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  PHONE: /^\+?[1-9]\d{1,14}$/,
  USERNAME: /^[a-zA-Z0-9_]{3,32}$/,
  URL: /^https?:\/\/([\w\-]+\.)+[\w\-]+(\/[\w\-._~:/?#[\]@!$&'()*+,;=]*)?$/,
  TELEGRAM_LINK: /^https?:\/\/(t\.me|telegram\.me)\/.+$/,
  INSTAGRAM_LINK: /^https?:\/\/(www\.)?instagram\.com\/.+$/,
  YOUTUBE_LINK: /^https?:\/\/(www\.)?(youtube\.com|youtu\.be)\/.+$/,
  TIKTOK_LINK: /^https?:\/\/(www\.)?tiktok\.com\/.+$/
};

// Кольори статусів
export const STATUS_COLORS = {
  [ORDER_STATUS.PENDING]: '#3b82f6',
  [ORDER_STATUS.PROCESSING]: '#8b5cf6',
  [ORDER_STATUS.IN_PROGRESS]: '#06b6d4',
  [ORDER_STATUS.COMPLETED]: '#22c55e',
  [ORDER_STATUS.PARTIAL]: '#f59e0b',
  [ORDER_STATUS.CANCELLED]: '#ef4444',
  [ORDER_STATUS.FAILED]: '#dc2626'
};

// Export all
export default {
  ORDER_STATUS,
  ORDER_STATUS_LABELS,
  SERVICE_CATEGORIES,
  SERVICE_TYPES,
  TRANSACTION_TYPES,
  TRANSACTION_STATUS,
  PAYMENT_METHODS,
  API_ENDPOINTS,
  ERROR_MESSAGES,
  LOCALE,
  TELEGRAM,
  LIMITS,
  CACHE_TTL,
  REGEX,
  STATUS_COLORS
};