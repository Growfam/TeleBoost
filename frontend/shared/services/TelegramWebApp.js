// frontend/shared/services/TelegramWebApp.js
/**
 * Централізований сервіс для роботи з Telegram WebApp
 * Гарантує правильну ініціалізацію
 */

class TelegramWebAppService {
  constructor() {
    this.tg = null;
    this.isReady = false;
    this.readyPromise = null;
    this.initDataCache = null;
    this.initAttempts = 0;
    this.maxAttempts = 10;
  }

  /**
   * Ініціалізація Telegram WebApp (викликати ОДИН раз)
   */
  async init() {
    if (this.readyPromise) {
      return this.readyPromise;
    }

    this.readyPromise = new Promise((resolve) => {
      // Чекаємо повного завантаження сторінки
      const initialize = async () => {
        if (!window.Telegram?.WebApp) {
          console.error('Telegram WebApp not available');
          resolve(false);
          return;
        }

        this.tg = window.Telegram.WebApp;

        // Спробуємо отримати initData кілька разів
        const tryGetInitData = async () => {
          this.initAttempts++;

          // Викликаємо ready() тільки на першій спробі
          if (this.initAttempts === 1) {
            try {
              this.tg.ready();
              console.log('TelegramWebApp: ready() called');
            } catch (error) {
              console.error('TelegramWebApp: Error calling ready():', error);
            }
          }

          // Чекаємо трохи після ready()
          await new Promise(r => setTimeout(r, 200));

          // Перевіряємо наявність initData
          const hasInitData = !!this.tg.initData;
          const initDataLength = this.tg.initData?.length || 0;

          console.log(`TelegramWebApp: Attempt ${this.initAttempts}:`, {
            hasInitData,
            initDataLength,
            platform: this.tg.platform,
            version: this.tg.version
          });

          if (hasInitData || this.initAttempts >= this.maxAttempts) {
            this.isReady = true;
            this.initDataCache = this.tg.initData;

            // Налаштовуємо тему
            this.setupTheme();

            console.log('TelegramWebApp: Initialization complete', {
              success: hasInitData,
              attempts: this.initAttempts,
              dataLength: initDataLength
            });

            resolve(hasInitData);
          } else {
            // Спробуємо ще раз
            setTimeout(() => tryGetInitData(), 300);
          }
        };

        // Починаємо спроби
        await tryGetInitData();
      };

      // Чекаємо повного завантаження DOM
      if (document.readyState === 'complete') {
        // Даємо ще трохи часу для Telegram
        setTimeout(initialize, 100);
      } else {
        window.addEventListener('load', () => {
          setTimeout(initialize, 100);
        });
      }
    });

    return this.readyPromise;
  }

  /**
   * Отримати initData
   */
  getInitData() {
    if (!this.isReady) {
      console.warn('TelegramWebApp: Not ready yet');
      return null;
    }

    // Використовуємо кешовану версію або беремо актуальну
    return this.initDataCache || this.tg?.initData || null;
  }

  /**
   * Отримати initDataUnsafe
   */
  getInitDataUnsafe() {
    return this.tg?.initDataUnsafe || null;
  }

  /**
   * Перевірити чи це Telegram WebApp
   */
  isTelegramWebApp() {
    return !!(this.tg && (this.getInitData() || this.tg.platform !== 'unknown'));
  }

  /**
   * Налаштувати тему
   */
  setupTheme() {
    if (!this.tg) return;

    try {
      this.tg.expand();
      this.tg.setHeaderColor('#1a0033');
      this.tg.setBackgroundColor('#000000');
    } catch (error) {
      console.error('TelegramWebApp: Error setting theme:', error);
    }
  }

  /**
   * Отримати Telegram WebApp об'єкт
   */
  getTelegramWebApp() {
    return this.tg;
  }
}

// Singleton
export const telegramWebApp = new TelegramWebAppService();
export default telegramWebApp;