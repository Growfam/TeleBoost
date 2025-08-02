// frontend/pages/home/home.js
/**
 * Главная страница TeleBoost
 */

// Импорты компонентов
import Header from '/frontend/shared/components/Header.js';
import Navigation from '/frontend/shared/components/Navigation.js';
import { ToastProvider, useToast } from '/frontend/shared/components/Toast.js';
import { AuthGuard, useTelegramAuth } from '/frontend/shared/auth/TelegramAuth.js';

// Импорты сервисов
import { AuthAPI, ServicesAPI, OrdersAPI, StatsAPI } from '/frontend/shared/services/APIClient.js';
import { realtimeService, RealtimeSubscriptions } from '/frontend/shared/services/RealtimeService.js';
import { servicesCache, ordersCache, userCache } from '/frontend/shared/services/CacheService.js';

// Импорты страничных компонентов
import BalanceCard from '/frontend/pages/home/components/BalanceCard.js';
import ServicesGrid from '/frontend/pages/home/components/ServicesGrid.js';
import RecentOrders from '/frontend/pages/home/components/RecentOrders.js';

// Импорты утилит
import { getIcon } from '/frontend/shared/ui/svg.js';

/**
 * Главный класс страницы
 */
class HomePage {
  constructor() {
    this.state = {
      user: null,
      balance: 0,
      services: [],
      orders: [],
      stats: {
        totalUsers: 0,
        totalOrders: 0,
        successRate: 0
      },
      isLoading: true,
      error: null
    };

    this.components = {};
    this.subscriptions = [];
  }

  /**
   * Инициализация страницы
   */
  async init() {
    try {
      // Инициализируем Telegram Web App
      this.initTelegram();

      // Проверяем авторизацию
      const { isAuthenticated, user } = await this.checkAuth();
      if (!isAuthenticated) {
        window.location.href = '/login';
        return;
      }

      this.state.user = user;

      // Инициализируем компоненты
      this.initComponents();

      // Загружаем данные
      await this.loadInitialData();

      // Подписываемся на realtime обновления
      this.subscribeToRealtimeUpdates();

      // Убираем состояние загрузки
      this.state.isLoading = false;
      this.hideSkeletons();

    } catch (error) {
      console.error('Failed to initialize home page:', error);
      this.showError('Ошибка загрузки страницы');
    }
  }

  /**
   * Инициализация Telegram Web App
   */
  initTelegram() {
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;

      // Расширяем на весь экран
      tg.expand();

      // Устанавливаем цвета
      tg.setHeaderColor('#1a0033');
      tg.setBackgroundColor('#000000');

      // Готовность
      tg.ready();
    }
  }

  /**
   * Проверка авторизации
   */
  async checkAuth() {
    try {
      // Сначала проверяем кеш
      const cachedUser = userCache.get('current_user');
      if (cachedUser) {
        return { isAuthenticated: true, user: cachedUser };
      }

      // Запрашиваем с сервера
      const response = await AuthAPI.getMe();
      if (response.success && response.data.user) {
        userCache.set('current_user', response.data.user, 300000); // 5 минут
        return { isAuthenticated: true, user: response.data.user };
      }

      return { isAuthenticated: false, user: null };
    } catch (error) {
      console.error('Auth check failed:', error);
      return { isAuthenticated: false, user: null };
    }
  }

  /**
   * Инициализация компонентов
   */
  initComponents() {
    // Header
    this.components.header = new Header({
      onMenuClick: this.handleMenuClick.bind(this),
      showNotification: false
    });
    document.getElementById('header-root').innerHTML = this.components.header.render();

    // Navigation
    this.components.navigation = new Navigation({
      activeItem: 'home',
      onNavigate: this.handleNavigate.bind(this),
      notifications: { orders: 0, profile: false }
    });
    document.getElementById('navigation-root').innerHTML = this.components.navigation.render();

    // Balance Card
    this.components.balanceCard = new BalanceCard({
      balance: this.state.user.balance || 0,
      currency: 'USD',
      onDeposit: this.handleDeposit.bind(this),
      onHistory: this.handleHistory.bind(this)
    });
    document.getElementById('balance-card-root').innerHTML = this.components.balanceCard.render();

    // Services Grid
    this.components.servicesGrid = new ServicesGrid({
      services: [],
      onServiceClick: this.handleServiceClick.bind(this)
    });
    document.getElementById('services-grid-root').innerHTML = this.components.servicesGrid.render();

    // Recent Orders
    this.components.recentOrders = new RecentOrders({
      orders: [],
      onOrderClick: this.handleOrderClick.bind(this),
      onViewAll: this.handleViewAllOrders.bind(this)
    });
    document.getElementById('recent-orders-root').innerHTML = this.components.recentOrders.render();

    // Добавляем иконки в заголовки секций
    document.getElementById('services-icon').innerHTML = getIcon('services', '', 24);
    document.getElementById('orders-icon').innerHTML = getIcon('orders', '', 24);
  }

  /**
   * Загрузка начальных данных
   */
  async loadInitialData() {
    try {
      // Загружаем параллельно
      const [servicesResponse, ordersResponse, statsResponse] = await Promise.all([
        this.loadServices(),
        this.loadOrders(),
        this.loadStats()
      ]);

      // Обновляем состояние
      if (servicesResponse) {
        this.state.services = servicesResponse;
        this.components.servicesGrid.update({ services: servicesResponse });
      }

      if (ordersResponse) {
        this.state.orders = ordersResponse;
        this.components.recentOrders.update({ orders: ordersResponse });

        // Обновляем счетчик в навигации
        const activeOrders = ordersResponse.filter(o =>
          ['pending', 'processing', 'in_progress'].includes(o.status)
        ).length;
        this.components.navigation.update({
          notifications: { orders: activeOrders, profile: false }
        });
      }

      if (statsResponse) {
        this.state.stats = statsResponse;
        this.updateStats(statsResponse);
      }

    } catch (error) {
      console.error('Failed to load initial data:', error);
    }
  }

  /**
   * Загрузка сервисов
   */
  async loadServices() {
    try {
      // Проверяем кеш
      const cached = servicesCache.get('telegram_services');
      if (cached) {
        return cached;
      }

      // Загружаем только Telegram сервисы
      const response = await ServicesAPI.getAll({
        category: 'telegram',
        active: true,
        limit: 6 // Популярные сервисы
      });

      if (response.success && response.data.services) {
        const services = response.data.services;
        servicesCache.set('telegram_services', services, 3600000); // 1 час
        return services;
      }

      return [];
    } catch (error) {
      console.error('Failed to load services:', error);
      return [];
    }
  }

  /**
   * Загрузка заказов
   */
  async loadOrders() {
    try {
      // Проверяем кеш
      const cached = ordersCache.get(`user_orders_${this.state.user.id}`);
      if (cached) {
        return cached;
      }

      // Загружаем последние заказы
      const response = await OrdersAPI.getAll({
        limit: 5,
        page: 1
      });

      if (response.success && response.data.orders) {
        const orders = response.data.orders;
        ordersCache.set(`user_orders_${this.state.user.id}`, orders, 180000); // 3 минуты
        return orders;
      }

      return [];
    } catch (error) {
      console.error('Failed to load orders:', error);
      return [];
    }
  }

  /**
   * Загрузка статистики
   */
  async loadStats() {
    try {
      const response = await StatsAPI.getLive();

      if (response.success && response.data) {
        return {
          totalUsers: response.data.total_users || 0,
          totalOrders: response.data.total_orders || 0,
          successRate: response.data.success_rate || 98.5
        };
      }

      return this.state.stats;
    } catch (error) {
      console.error('Failed to load stats:', error);
      return this.state.stats;
    }
  }

  /**
   * Подписка на realtime обновления
   */
  subscribeToRealtimeUpdates() {
    // Подписка на обновления баланса
    const balanceUnsubscribe = RealtimeSubscriptions.onBalanceUpdate((data) => {
      this.components.balanceCard.update({ balance: data.new });
      this.showToast(`Баланс обновлен: ${data.difference > 0 ? '+' : ''}${data.difference.toFixed(2)} USD`, 'info');
    });
    this.subscriptions.push(balanceUnsubscribe);

    // Подписка на новые заказы
    const orderUnsubscribe = RealtimeSubscriptions.onNewOrder((order) => {
      this.state.orders.unshift(order);
      this.components.recentOrders.update({ orders: this.state.orders.slice(0, 5) });
      this.showToast('Новый заказ создан', 'success');
    });
    this.subscriptions.push(orderUnsubscribe);

    // Подписка на изменение статуса заказов
    const statusUnsubscribe = RealtimeSubscriptions.onOrderStatusChange((data) => {
      const orderIndex = this.state.orders.findIndex(o => o.id === data.orderId);
      if (orderIndex !== -1) {
        this.state.orders[orderIndex].status = data.newStatus;
        this.components.recentOrders.update({ orders: this.state.orders.slice(0, 5) });

        if (data.newStatus === 'completed') {
          this.showToast(`Заказ #${data.orderId.slice(0, 8)} выполнен!`, 'success');
        }
      }
    });
    this.subscriptions.push(statusUnsubscribe);
  }

  /**
   * Обновление статистики
   */
  updateStats(stats) {
    // Анимированное обновление чисел
    this.animateValue('total-users', 0, stats.totalUsers, 2000);
    this.animateValue('total-orders', 0, stats.totalOrders, 2000);

    const successElement = document.getElementById('success-rate');
    if (successElement) {
      successElement.textContent = `${stats.successRate}%`;
    }
  }

  /**
   * Анимация числовых значений
   */
  animateValue(elementId, start, end, duration) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const startTime = performance.now();
    const update = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      const currentValue = Math.floor(start + (end - start) * progress);
      element.textContent = currentValue.toLocaleString('ru-RU');

      if (progress < 1) {
        requestAnimationFrame(update);
      }
    };

    requestAnimationFrame(update);
  }

  /**
   * Скрыть skeleton loaders
   */
  hideSkeletons() {
    const skeletons = document.querySelectorAll('.skeleton-loader, .services-skeleton, .orders-skeleton');
    skeletons.forEach(skeleton => {
      skeleton.style.display = 'none';
    });
  }

  /**
   * Обработчики событий
   */
  handleMenuClick(isOpen) {
    // Открытие/закрытие меню
    console.log('Menu clicked:', isOpen);
  }

  handleNavigate(item) {
    window.location.href = item.path;
  }

  handleDeposit() {
    window.location.href = '/deposit';
  }

  handleHistory() {
    window.location.href = '/transactions';
  }

  handleServiceClick(service) {
    window.location.href = `/order/new?service=${service.id}`;
  }

  handleOrderClick(order) {
    window.location.href = `/order/${order.id}`;
  }

  handleViewAllOrders() {
    window.location.href = '/orders';
  }

  /**
   * Показать сообщение
   */
  showToast(message, type = 'info') {
    if (window.showToast) {
      window.showToast(message, type);
    }
  }

  /**
   * Показать ошибку
   */
  showError(message) {
    this.state.error = message;
    const errorContainer = document.createElement('div');
    errorContainer.className = 'error-message animate-fadeInDown';
    errorContainer.innerHTML = `
      <span class="error-icon">${getIcon('error', '', 20)}</span>
      <span>${message}</span>
    `;

    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
      mainContent.insertBefore(errorContainer, mainContent.firstChild);
    }
  }

  /**
   * Очистка при уничтожении
   */
  destroy() {
    // Отписываемся от всех подписок
    this.subscriptions.forEach(unsubscribe => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    });

    // Очищаем компоненты
    Object.values(this.components).forEach(component => {
      if (component.destroy) {
        component.destroy();
      }
    });
  }
}

// Инициализация страницы при загрузке
document.addEventListener('DOMContentLoaded', () => {
  const homePage = new HomePage();
  homePage.init();

  // Сохраняем в глобальную переменную для отладки
  window.homePage = homePage;
});