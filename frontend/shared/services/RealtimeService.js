// frontend/shared/services/RealtimeService.js
import { supabase, Tables, subscribeToPresence, subscribeToBroadcast } from './SupabaseClient.js';
import { generalCache, ordersCache, userCache } from './CacheService.js';

/**
 * Сервіс для управління real-time оновленнями через Supabase
 * З підтримкою режиму без Supabase
 */
export class RealtimeService {
  constructor() {
    this.subscriptions = new Map();
    this.listeners = new Map();
    this.userId = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.isSupabaseEnabled = window.CONFIG?.FEATURES?.REALTIME || false;

    // Підписуємось на події авторизації
    window.addEventListener('auth:login', (e) => this.handleAuthLogin(e.detail));
    window.addEventListener('auth:logout', () => this.handleAuthLogout());

    // Логування стану
    console.log('RealtimeService initialized:', {
      supabaseEnabled: this.isSupabaseEnabled,
      features: window.CONFIG?.FEATURES
    });
  }

  /**
   * Обробка входу користувача
   */
  handleAuthLogin(authData) {
    this.userId = authData.user.id;
    if (this.isSupabaseEnabled) {
      this.startRealtimeSubscriptions();
    } else {
      console.log('Realtime features disabled - Supabase not configured');
      // Емулюємо підключення для UI
      this.isConnected = true;
      this.emit('connection:established');
    }
  }

  /**
   * Обробка виходу користувача
   */
  handleAuthLogout() {
    this.stopAllSubscriptions();
    this.userId = null;
  }

  /**
   * Запустити всі підписки
   */
  startRealtimeSubscriptions() {
    if (!this.userId || !this.isSupabaseEnabled) return;

    console.log('Starting realtime subscriptions for user:', this.userId);

    // Підписка на зміни користувача
    this.subscribeToUserUpdates();

    // Підписка на замовлення
    this.subscribeToOrders();

    // Підписка на транзакції
    this.subscribeToTransactions();

    // Підписка на сповіщення
    this.subscribeToNotifications();

    // Підписка на presence (онлайн статус)
    if (window.CONFIG?.FEATURES?.PRESENCE) {
      this.subscribeToPresence();
    }

    // Підписка на системні повідомлення
    if (window.CONFIG?.FEATURES?.BROADCAST) {
      this.subscribeToSystemBroadcast();
    }

    this.isConnected = true;
  }

  /**
   * Зупинити всі підписки
   */
  stopAllSubscriptions() {
    this.subscriptions.forEach(unsubscribe => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    });
    this.subscriptions.clear();
    this.isConnected = false;
  }

  /**
   * Підписка на оновлення користувача
   */
  subscribeToUserUpdates() {
    if (!this.isSupabaseEnabled) return;

    const unsubscribe = Tables.users.subscribe((payload) => {
      console.log('User update:', payload);

      // Оновлюємо кеш
      if (payload.new) {
        userCache.set(`user:${this.userId}`, payload.new);

        // Сповіщаємо listeners
        this.emit('user:update', payload.new);

        // Якщо змінився баланс
        if (payload.old?.balance !== payload.new?.balance) {
          this.emit('balance:update', {
            old: payload.old?.balance,
            new: payload.new?.balance,
            difference: payload.new?.balance - payload.old?.balance
          });
        }
      }
    }, this.userId);

    this.subscriptions.set('user', unsubscribe);
  }

  /**
   * Підписка на замовлення
   */
  subscribeToOrders() {
    if (!this.isSupabaseEnabled) return;

    const unsubscribe = Tables.orders.subscribe((payload) => {
      console.log('Order update:', payload);

      // Інвалідуємо кеш замовлень
      ordersCache.invalidatePattern(`orders:${this.userId}:*`);

      // Визначаємо тип події
      if (payload.eventType === 'INSERT') {
        this.emit('order:created', payload.new);
      } else if (payload.eventType === 'UPDATE') {
        this.emit('order:updated', payload.new);

        // Перевіряємо зміну статусу
        if (payload.old?.status !== payload.new?.status) {
          this.emit('order:status', {
            orderId: payload.new.id,
            oldStatus: payload.old?.status,
            newStatus: payload.new.status,
            order: payload.new
          });
        }
      } else if (payload.eventType === 'DELETE') {
        this.emit('order:deleted', payload.old);
      }
    }, this.userId);

    this.subscriptions.set('orders', unsubscribe);
  }

  /**
   * Підписка на транзакції
   */
  subscribeToTransactions() {
    if (!this.isSupabaseEnabled) return;

    const unsubscribe = Tables.transactions.subscribe((payload) => {
      console.log('Transaction update:', payload);

      if (payload.eventType === 'INSERT') {
        this.emit('transaction:new', payload.new);

        // Оновлюємо баланс в UI
        if (payload.new.type === 'deposit' || payload.new.type === 'referral_bonus') {
          this.emit('balance:increase', payload.new);
        } else if (payload.new.type === 'withdrawal' || payload.new.type === 'order') {
          this.emit('balance:decrease', payload.new);
        }
      }
    }, this.userId);

    this.subscriptions.set('transactions', unsubscribe);
  }

  /**
   * Підписка на сповіщення
   */
  subscribeToNotifications() {
    if (!this.isSupabaseEnabled) return;

    const unsubscribe = Tables.notifications.subscribe((payload) => {
      console.log('New notification:', payload);

      if (payload.eventType === 'INSERT') {
        this.emit('notification:new', payload.new);

        // Показуємо toast
        this.showNotificationToast(payload.new);
      }
    }, this.userId);

    this.subscriptions.set('notifications', unsubscribe);
  }

  /**
   * Підписка на presence (хто онлайн)
   */
  subscribeToPresence() {
    if (!this.isSupabaseEnabled || !window.CONFIG?.FEATURES?.PRESENCE) return;

    const presence = subscribeToPresence('online_users', {
      onSync: () => {
        const state = presence.getState();
        const onlineCount = Object.keys(state).length;
        this.emit('presence:sync', { count: onlineCount, users: state });
      },
      onJoin: ({ key, newPresences }) => {
        this.emit('presence:join', { userId: key, presences: newPresences });
      },
      onLeave: ({ key, leftPresences }) => {
        this.emit('presence:leave', { userId: key, presences: leftPresences });
      },
      onSubscribed: () => {
        // Трекаємо себе як онлайн
        presence.track({
          user_id: this.userId,
          online_at: new Date().toISOString()
        });
      }
    });

    this.subscriptions.set('presence', presence);
  }

  /**
   * Підписка на системні broadcast повідомлення
   */
  subscribeToSystemBroadcast() {
    if (!this.isSupabaseEnabled || !window.CONFIG?.FEATURES?.BROADCAST) return;

    // Системні оповіщення
    const systemBroadcast = subscribeToBroadcast('system', 'announcement', (data) => {
      this.emit('system:announcement', data);
      this.showSystemAnnouncement(data);
    });

    // Оновлення сервісів
    const servicesBroadcast = subscribeToBroadcast('services', 'update', (data) => {
      this.emit('services:update', data);
      // Інвалідуємо кеш сервісів
      generalCache.invalidatePattern('services:*');
    });

    this.subscriptions.set('system_broadcast', systemBroadcast);
    this.subscriptions.set('services_broadcast', servicesBroadcast);
  }

  /**
   * Підписатись на статус конкретного замовлення
   */
  subscribeToOrderStatus(orderId, callback) {
    if (!this.isSupabaseEnabled) {
      console.warn('Order status subscription not available - Supabase disabled');
      return () => {};
    }

    const key = `order_status_${orderId}`;

    // Якщо вже підписані - не дублюємо
    if (this.subscriptions.has(key)) {
      return;
    }

    const unsubscribe = Tables.orders.subscribeToStatus(orderId, (payload) => {
      callback(payload.new);
    });

    this.subscriptions.set(key, unsubscribe);

    // Повертаємо функцію для відписки
    return () => {
      unsubscribe();
      this.subscriptions.delete(key);
    };
  }

  /**
   * Показати сповіщення
   */
  showNotificationToast(notification) {
    // Викликаємо глобальний toast (буде реалізовано в Toast.js)
    if (window.showToast) {
      window.showToast(notification.message || notification.title, 'info');
    }
  }

  /**
   * Показати системне оповіщення
   */
  showSystemAnnouncement(data) {
    if (window.showModal) {
      window.showModal({
        title: data.title || 'Системне повідомлення',
        content: data.message,
        type: data.type || 'info'
      });
    }
  }

  /**
   * Додати слухача подій
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);

    // Повертаємо функцію для видалення слухача
    return () => this.off(event, callback);
  }

  /**
   * Видалити слухача
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback);
    }
  }

  /**
   * Emit подію
   */
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      });
    }

    // Також emit як CustomEvent для глобального прослуховування
    window.dispatchEvent(new CustomEvent(`realtime:${event}`, { detail: data }));
  }

  /**
   * Перевірити з'єднання
   */
  checkConnection() {
    if (!this.isSupabaseEnabled) {
      // Завжди повертаємо true якщо Supabase вимкнено
      return true;
    }
    return this.isConnected && supabase.realtime.isConnected();
  }

  /**
   * Переконектитись
   */
  async reconnect() {
    if (!this.isSupabaseEnabled) {
      console.log('Reconnect skipped - Supabase disabled');
      return;
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emit('connection:failed');
      return;
    }

    this.reconnectAttempts++;
    console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);

    this.stopAllSubscriptions();

    // Експоненційний backoff
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 30000);

    setTimeout(() => {
      this.startRealtimeSubscriptions();

      if (this.checkConnection()) {
        this.reconnectAttempts = 0;
        this.emit('connection:restored');
      } else {
        this.reconnect();
      }
    }, delay);
  }

  /**
   * Емулювати оновлення (для тестування без Supabase)
   */
  emulateUpdate(event, data) {
    if (this.isSupabaseEnabled) {
      console.warn('Emulation not available when Supabase is enabled');
      return;
    }

    console.log(`Emulating ${event}:`, data);
    this.emit(event, data);
  }
}

// Створюємо singleton
export const realtimeService = new RealtimeService();

// Хелпери для швидкої підписки
export const RealtimeSubscriptions = {
  // Підписка на оновлення балансу
  onBalanceUpdate(callback) {
    return realtimeService.on('balance:update', callback);
  },

  // Підписка на нові замовлення
  onNewOrder(callback) {
    return realtimeService.on('order:created', callback);
  },

  // Підписка на зміну статусу замовлення
  onOrderStatusChange(callback) {
    return realtimeService.on('order:status', callback);
  },

  // Підписка на конкретне замовлення
  trackOrder(orderId, callback) {
    return realtimeService.subscribeToOrderStatus(orderId, callback);
  },

  // Підписка на нові сповіщення
  onNewNotification(callback) {
    return realtimeService.on('notification:new', callback);
  },

  // Підписка на нові транзакції
  onNewTransaction(callback) {
    return realtimeService.on('transaction:new', callback);
  },

  // Підписка на онлайн користувачів
  onOnlineUsersChange(callback) {
    return realtimeService.on('presence:sync', callback);
  },

  // Підписка на системні оповіщення
  onSystemAnnouncement(callback) {
    return realtimeService.on('system:announcement', callback);
  }
};

// Auto-start якщо користувач вже авторизований
if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    try {
      const auth = JSON.parse(localStorage.getItem('auth') || '{}');
      if (auth.user?.id) {
        realtimeService.userId = auth.user.id;
        if (realtimeService.isSupabaseEnabled) {
          realtimeService.startRealtimeSubscriptions();
        }
      }
    } catch (e) {
      console.error('Failed to auto-start realtime:', e);
    }
  });
}

// Експортуємо для тестування
if (window.CONFIG?.DEBUG) {
  window.realtimeService = realtimeService;
}

export default realtimeService;