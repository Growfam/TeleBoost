// frontend/shared/services/SupabaseClient.js
/**
 * Supabase клієнт з заглушкою для випадків коли Supabase не налаштований
 */

// Перевіряємо чи налаштований Supabase
const isSupabaseConfigured = window.CONFIG?.SUPABASE_URL &&
                           window.CONFIG?.SUPABASE_URL !== 'https://your-project.supabase.co' &&
                           window.CONFIG?.SUPABASE_ANON_KEY &&
                           window.CONFIG?.SUPABASE_ANON_KEY !== 'your-anon-key';

let supabase = null;

// Створюємо клієнт тільки якщо є правильна конфігурація
if (isSupabaseConfigured) {
  // Динамічний імпорт Supabase (потрібно додати скрипт в HTML)
  if (window.createClient) {
    supabase = window.createClient(window.CONFIG.SUPABASE_URL, window.CONFIG.SUPABASE_ANON_KEY, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: false
      },
      realtime: {
        params: {
          eventsPerSecond: 10
        }
      }
    });
  } else {
    console.warn('Supabase library not loaded');
  }
} else {
  console.warn('Supabase not configured - realtime features disabled');

  // Заглушка для supabase
  supabase = {
    channel: () => ({
      on: () => ({ subscribe: () => {} }),
      subscribe: () => {},
      unsubscribe: () => {}
    }),
    removeChannel: () => {},
    from: () => ({
      select: () => Promise.resolve({ data: [], error: null }),
      insert: () => Promise.resolve({ data: null, error: null }),
      update: () => Promise.resolve({ data: null, error: null }),
      delete: () => Promise.resolve({ data: null, error: null })
    }),
    realtime: {
      isConnected: () => false
    },
    auth: {
      getUser: () => Promise.resolve({ data: { user: null }, error: null }),
      updateUser: () => Promise.resolve({ data: null, error: null }),
      signOut: () => Promise.resolve({ error: null })
    },
    storage: {
      from: () => ({
        upload: () => Promise.resolve({ data: null, error: null }),
        getPublicUrl: () => ({ data: { publicUrl: '' } }),
        createSignedUrl: () => Promise.resolve({ data: { signedUrl: '' }, error: null }),
        remove: () => Promise.resolve({ error: null }),
        list: () => Promise.resolve({ data: [], error: null })
      })
    },
    rpc: () => Promise.resolve({ data: null, error: null })
  };
}

export { supabase };

/**
 * Хелпер для підписки на зміни в таблиці
 */
export function subscribeToTable(table, callback, filters = {}) {
  if (!isSupabaseConfigured) {
    console.warn('Supabase not configured - subscribeToTable disabled');
    return () => {}; // Повертаємо пусту функцію unsubscribe
  }

  const channel = supabase.channel(`${table}_changes`);

  // Базова підписка на всі зміни
  let subscription = channel.on(
    'postgres_changes',
    {
      event: '*',
      schema: 'public',
      table: table,
      filter: filters.filter
    },
    (payload) => {
      callback(payload);
    }
  );

  // Підписка на конкретні події якщо вказані
  if (filters.events) {
    filters.events.forEach(event => {
      subscription = subscription.on(
        'postgres_changes',
        {
          event: event,
          schema: 'public',
          table: table,
          filter: filters.filter
        },
        (payload) => {
          callback({ ...payload, event });
        }
      );
    });
  }

  // Підписуємось
  subscription.subscribe((status) => {
    if (status === 'SUBSCRIBED') {
      console.log(`Subscribed to ${table} changes`);
    }
  });

  // Повертаємо функцію для відписки
  return () => {
    supabase.removeChannel(subscription);
  };
}

/**
 * Хелпер для підписки на presence (онлайн статус)
 */
export function subscribeToPresence(channelName, callbacks = {}) {
  if (!isSupabaseConfigured) {
    console.warn('Supabase not configured - subscribeToPresence disabled');
    return {
      track: () => {},
      untrack: () => {},
      getState: () => ({}),
      unsubscribe: () => {}
    };
  }

  const channel = supabase.channel(channelName);

  // Підписка на sync
  if (callbacks.onSync) {
    channel.on('presence', { event: 'sync' }, () => {
      const state = channel.presenceState();
      callbacks.onSync(state);
    });
  }

  // Підписка на join
  if (callbacks.onJoin) {
    channel.on('presence', { event: 'join' }, ({ key, newPresences }) => {
      callbacks.onJoin({ key, newPresences });
    });
  }

  // Підписка на leave
  if (callbacks.onLeave) {
    channel.on('presence', { event: 'leave' }, ({ key, leftPresences }) => {
      callbacks.onLeave({ key, leftPresences });
    });
  }

  // Підписуємось на канал
  channel.subscribe(async (status) => {
    if (status === 'SUBSCRIBED' && callbacks.onSubscribed) {
      callbacks.onSubscribed();
    }
  });

  // Функції для роботи з presence
  return {
    track: (data) => channel.track(data),
    untrack: () => channel.untrack(),
    getState: () => channel.presenceState(),
    unsubscribe: () => supabase.removeChannel(channel)
  };
}

/**
 * Хелпер для broadcast (обмін повідомленнями між клієнтами)
 */
export function subscribeToBroadcast(channelName, event, callback) {
  if (!isSupabaseConfigured) {
    console.warn('Supabase not configured - subscribeToBroadcast disabled');
    return {
      send: () => {},
      unsubscribe: () => {}
    };
  }

  const channel = supabase.channel(channelName);

  channel
    .on('broadcast', { event }, (payload) => {
      callback(payload);
    })
    .subscribe();

  // Функція для відправки повідомлень
  const send = (data) => {
    channel.send({
      type: 'broadcast',
      event: event,
      payload: data
    });
  };

  // Повертаємо функції
  return {
    send,
    unsubscribe: () => supabase.removeChannel(channel)
  };
}

/**
 * Database хелпери
 */
export const Database = {
  // SELECT запити
  async select(table, options = {}) {
    if (!isSupabaseConfigured) {
      return { data: [], count: 0 };
    }

    let query = supabase.from(table).select(options.select || '*');

    // Фільтри
    if (options.filters) {
      Object.entries(options.filters).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          query = query.in(key, value);
        } else if (value === null) {
          query = query.is(key, null);
        } else {
          query = query.eq(key, value);
        }
      });
    }

    // Сортування
    if (options.orderBy) {
      query = query.order(options.orderBy.column, {
        ascending: options.orderBy.ascending ?? true
      });
    }

    // Пагінація
    if (options.limit) {
      query = query.limit(options.limit);
    }
    if (options.offset) {
      query = query.range(options.offset, options.offset + (options.limit || 10) - 1);
    }

    const { data, error, count } = await query;

    if (error) throw error;
    return { data, count };
  },

  // INSERT
  async insert(table, data) {
    if (!isSupabaseConfigured) {
      return null;
    }

    const { data: result, error } = await supabase
      .from(table)
      .insert(data)
      .select();

    if (error) throw error;
    return result;
  },

  // UPDATE
  async update(table, id, updates) {
    if (!isSupabaseConfigured) {
      return null;
    }

    const { data, error } = await supabase
      .from(table)
      .update(updates)
      .eq('id', id)
      .select();

    if (error) throw error;
    return data;
  },

  // DELETE
  async delete(table, id) {
    if (!isSupabaseConfigured) {
      return true;
    }

    const { error } = await supabase
      .from(table)
      .delete()
      .eq('id', id);

    if (error) throw error;
    return true;
  },

  // RPC (stored procedures)
  async rpc(functionName, params = {}) {
    if (!isSupabaseConfigured) {
      return null;
    }

    const { data, error } = await supabase.rpc(functionName, params);

    if (error) throw error;
    return data;
  }
};

/**
 * Storage хелпери
 */
export const Storage = {
  // Завантажити файл
  async upload(bucket, path, file, options = {}) {
    if (!isSupabaseConfigured) {
      return null;
    }

    const { data, error } = await supabase.storage
      .from(bucket)
      .upload(path, file, {
        cacheControl: '3600',
        upsert: false,
        ...options
      });

    if (error) throw error;
    return data;
  },

  // Отримати публічний URL
  getPublicUrl(bucket, path) {
    if (!isSupabaseConfigured) {
      return '';
    }

    const { data } = supabase.storage
      .from(bucket)
      .getPublicUrl(path);

    return data.publicUrl;
  },

  // Створити підписаний URL
  async createSignedUrl(bucket, path, expiresIn = 3600) {
    if (!isSupabaseConfigured) {
      return '';
    }

    const { data, error } = await supabase.storage
      .from(bucket)
      .createSignedUrl(path, expiresIn);

    if (error) throw error;
    return data.signedUrl;
  },

  // Видалити файл
  async delete(bucket, paths) {
    if (!isSupabaseConfigured) {
      return true;
    }

    const { error } = await supabase.storage
      .from(bucket)
      .remove(paths);

    if (error) throw error;
    return true;
  },

  // Список файлів
  async list(bucket, path = '', options = {}) {
    if (!isSupabaseConfigured) {
      return [];
    }

    const { data, error } = await supabase.storage
      .from(bucket)
      .list(path, {
        limit: 100,
        offset: 0,
        ...options
      });

    if (error) throw error;
    return data;
  }
};

/**
 * Auth хелпери (якщо використовується Supabase Auth)
 */
export const Auth = {
  // Отримати поточного користувача
  async getUser() {
    if (!isSupabaseConfigured) {
      return null;
    }

    const { data: { user }, error } = await supabase.auth.getUser();
    if (error) throw error;
    return user;
  },

  // Оновити користувача
  async updateUser(updates) {
    if (!isSupabaseConfigured) {
      return null;
    }

    const { data, error } = await supabase.auth.updateUser(updates);
    if (error) throw error;
    return data;
  },

  // Вийти
  async signOut() {
    if (!isSupabaseConfigured) {
      return true;
    }

    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    return true;
  }
};

// Експортуємо типізовані хелпери для конкретних таблиць
export const Tables = {
  users: {
    subscribe: (callback, userId = null) => {
      const filters = userId ? { filter: `id=eq.${userId}` } : {};
      return subscribeToTable('users', callback, filters);
    },

    get: (id) => Database.select('users', {
      filters: { id },
      limit: 1
    }).then(({ data }) => data?.[0]),

    update: (id, updates) => Database.update('users', id, updates)
  },

  orders: {
    subscribe: (callback, userId = null) => {
      const filters = userId ? { filter: `user_id=eq.${userId}` } : {};
      return subscribeToTable('orders', callback, filters);
    },

    subscribeToStatus: (orderId, callback) => {
      return subscribeToTable('orders', (payload) => {
        if (payload.new?.id === orderId) {
          callback(payload);
        }
      }, { filter: `id=eq.${orderId}` });
    },

    getByUser: (userId, options = {}) => Database.select('orders', {
      filters: { user_id: userId },
      orderBy: { column: 'created_at', ascending: false },
      ...options
    })
  },

  transactions: {
    subscribe: (callback, userId = null) => {
      const filters = userId ? { filter: `user_id=eq.${userId}` } : {};
      return subscribeToTable('transactions', callback, filters);
    },

    getByUser: (userId, options = {}) => Database.select('transactions', {
      filters: { user_id: userId },
      orderBy: { column: 'created_at', ascending: false },
      ...options
    })
  },

  services: {
    subscribe: (callback) => subscribeToTable('services', callback),

    getAll: (options = {}) => Database.select('services', {
      filters: { is_active: true },
      orderBy: { column: 'position', ascending: true },
      ...options
    }),

    getByCategory: (category) => Database.select('services', {
      filters: { category, is_active: true },
      orderBy: { column: 'position', ascending: true }
    })
  },

  notifications: {
    subscribe: (callback, userId) => {
      return subscribeToTable('user_notifications', callback, {
        filter: `user_id=eq.${userId}`,
        events: ['INSERT']
      });
    },

    markAsRead: (id) => Database.update('user_notifications', id, {
      is_read: true,
      read_at: new Date().toISOString()
    })
  }
};

export default supabase;