// frontend/shared/services/RealtimeService.js
import { supabase, Tables, subscribeToPresence, subscribeToBroadcast } from './SupabaseClient.js';
import { generalCache, ordersCache, userCache } from './CacheService.js';

/**
 * Сервіс для управління real-time оновленнями через Supabase
 */
export class RealtimeService {
  constructor() {
    this.subscriptions = new Map();
    this.listeners = new Map();
    this.userId = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;

    // Підписуємось на події авторизації
    window.addEventListener('auth:login', (e) => this.handleAuthLogin(e.detail));
    window.addEventListener('auth:logout', () => this.handleAuthLogout());
  }

  /**
   * Обробка входу користувача
   */
  handleAuthLogin(authData) {
    this.userId = authData.user.id;
    this.startRealtimeSubscriptions();
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
    if (!this.userId) return;

    // Підписка на зміни користувача
    this.subscribeToUserUpdates();

    // Підписка на замовлення
    this.subscribeToOrders();

    // Підписка на транзакції
    this.subscribeToTransactions();

    // Підписка на сповіщення
    this.subscribeToNotifications();

    // Підписка на presence (онлайн статус)
    this.subscribeToPresence();

    // Підписка на системні повідомлення
    this.subscribeToSystemBroadcast();

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
      window.showToast({
        type: 'info',
        title: notification.title,
        message: notification.message,
        duration: 5000
      });
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
    return this.isConnected && supabase.realtime.isConnected();
  }

  /**
   * Переконектитись
   */
  async reconnect() {
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
if (localStorage.getItem('auth')) {
  try {
    const auth = JSON.parse(localStorage.getItem('auth'));
    if (auth.user?.id) {
      realtimeService.userId = auth.user.id;
      realtimeService.startRealtimeSubscriptions();
    }
  } catch (e) {
    console.error('Failed to auto-start realtime:', e);
  }
}

export default realtimeService;