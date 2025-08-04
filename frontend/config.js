// frontend/config.js
/**
 * Глобальна конфігурація TeleBoost
 * Production версія
 */

window.CONFIG = {
  // API настройки
  API_URL: 'https://teleboost-teleboost.up.railway.app/api',

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
  VERSION: '1.0.0'
};