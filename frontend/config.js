// frontend/config.js
/**
 * Глобальна конфігурація TeleBoost
 * Production версія з HTTPS
 */

window.CONFIG = {
  // API настройки - ЗАВЖДИ HTTPS для Railway!
  API_URL: 'https://teleboost-teleboost.up.railway.app/api',

  // Frontend URL
  APP_URL: 'https://teleboost-teleboost.up.railway.app',

  // Telegram Bot
  BOT_USERNAME: 'TeleeBoost_bot',

  // Supabase (поки що заглушки - додати реальні дані якщо використовується)
  SUPABASE_URL: 'https://your-project.supabase.co',
  SUPABASE_ANON_KEY: 'your-anon-key',

  // Функції які відключені якщо Supabase не налаштований
  FEATURES: {
    REALTIME: false,
    PRESENCE: false,
    BROADCAST: false
  },

  // Версія додатку
  VERSION: '1.0.0',

  // Environment
  ENV: 'production',

  // Debug mode
  DEBUG: false
};