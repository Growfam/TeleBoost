// frontend/config.js
/**
 * Глобальна конфігурація TeleBoost
 * Завантажується перед всіма іншими скриптами
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
    REALTIME: false, // Відключаємо realtime якщо Supabase не налаштований
    PRESENCE: false,
    BROADCAST: false
  },

  // Інші налаштування
  DEBUG: true,
  VERSION: '1.0.0'
};

// Логування конфігурації в debug режимі
if (window.CONFIG.DEBUG) {
  console.log('TeleBoost Config loaded:', {
    API: window.CONFIG.API_URL,
    Bot: window.CONFIG.BOT_USERNAME,
    Features: window.CONFIG.FEATURES
  });
}