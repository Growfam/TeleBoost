// frontend/pages/home/home.js
/**
 * Головна сторінка TeleBoost
 * ВИПРАВЛЕНО: Використання оновлених методів авторизації
 */

// Імпорти компонентів
import Header from '/frontend/shared/components/Header.js';
import Navigation from '/frontend/shared/components/Navigation.js';
import { ToastProvider, useToast } from '/frontend/shared/components/Toast.js';
import TelegramAuth, { AuthGuard, useTelegramAuth } from '/frontend/shared/auth/TelegramAuth.js';

// Імпорти сервісів
import { apiClient, AuthAPI, ServicesAPI, OrdersAPI, StatsAPI } from '/frontend/shared/services/APIClient.js';
import { realtimeService, RealtimeSubscriptions } from '/frontend/shared/services/RealtimeService.js';
import { servicesCache, ordersCache, userCache } from '/frontend/shared/services/CacheService.js';

// Імпорти сторінкових компонентів
import BalanceCard from '/frontend/pages/home/components/BalanceCard.js';
import ServicesGrid from '/frontend/pages/home/components/ServicesGrid.js';
import RecentOrders from '/frontend/pages/home/components/RecentOrders.js';

// Імпорти утилит
import { getIcon } from '/frontend/shared/ui/svg.js';

/**
 * Головний клас сторінки
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
   * Ініціалізація сторінки
   */
  async init() {
    try {
      console.log('Initializing home page...');

      // Ініціалізуємо Telegram Web App
      this.initTelegram();

      // Перевіряємо авторизацію
      const authResult = await this.checkAuth();
      console.log('Auth check result:', authResult);

      if (!authResult.isAuthenticated) {
        console.log('User not authenticated, redirecting to login...');
        this.showAuthScreen();
        return;
      }

      this.state.user = authResult.user;

      // Ініціалізуємо компоненти
      this.initComponents();

      // Завантажуємо дані
      await this.loadInitialData();

      // Підписуємось на realtime оновлення
      this.subscribeToRealtimeUpdates();

      // Прибираємо стан завантаження
      this.state.isLoading = false;
      this.hideSkeletons();

      console.log('Home page initialized successfully');

    } catch (error) {
      console.error('Failed to initialize home page:', error);
      this.showError('Помилка завантаження сторінки');
    }
  }

  /**
   * Ініціалізація Telegram Web App
   */
  initTelegram() {
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;

      // Розширюємо на весь екран
      tg.expand();

      // Встановлюємо кольори
      tg.setHeaderColor('#1a0033');
      tg.setBackgroundColor('#000000');

      // Готовність
      tg.ready();
    }
  }

  /**
   * Перевірка авторизації
   * ВИПРАВЛЕНО: Використовуємо правильний метод перевірки
   */
  async checkAuth() {
    try {
      // Перевіряємо локальну авторизацію
      const localAuth = AuthGuard.check();
      console.log('Local auth check:', localAuth);

      if (!localAuth.isAuthenticated) {
        return { isAuthenticated: false, user: null };
      }

      // Перевіряємо кеш
      const cachedUser = userCache.get('current_user');
      if (cachedUser) {
        console.log('Using cached user data');
        return { isAuthenticated: true, user: cachedUser };
      }

      // Запитуємо з сервера
      console.log('Fetching user data from server...');
      const response = await AuthAPI.getMe();

      if (response.success && response.data.user) {
        userCache.set('current_user', response.data.user, 300000); // 5 хвилин
        return { isAuthenticated: true, user: response.data.user };
      }

      return { isAuthenticated: false, user: null };
    } catch (error) {
      console.error('Auth check failed:', error);

      // Якщо помилка 401 - токен недійсний
      if (error.code === 'UNAUTHORIZED' || error.status === 401) {
        apiClient.clearTokens();
        return { isAuthenticated: false, user: null };
      }

      // Інші помилки - можливо проблеми з мережею
      throw error;
    }
  }

  /**
   * Показати екран авторизації
   */
  showAuthScreen() {
    const mainContent = document.querySelector('.main-content');
    if (!mainContent) return;

    // Приховуємо скелетони
    this.hideSkeletons();

    // Створюємо компонент авторизації
    const authComponent = new TelegramAuth({
      onSuccess: (data) => {
        console.log('Auth success:', data);
        // Перезавантажуємо сторінку після успішної авторизації
        setTimeout(() => {
          window.location.reload();
        }, 500);
      },
      onError: (error) => {
        console.error('Auth error:', error);
        this.showError('Помилка авторизації: ' + error.message);
      }
    });

    // Показуємо компонент авторизації
    mainContent.innerHTML = authComponent.render();
    authComponent.init();
  }

  /**
   * Ініціалізація компонентів
   */
  initComponents() {
    // Header
    this.components.header = new Header({
      onMenuClick: this.handleMenuClick.bind(this),
      showNotification: false
    });
    const headerRoot = document.getElementById('header-root');
    if (headerRoot) {
      headerRoot.innerHTML = this.components.header.render();
    }

    // Navigation
    this.components.navigation = new Navigation({
      activeItem: 'home',
      onNavigate: this.handleNavigate.bind(this),
      notifications: { orders: 0, profile: false }
    });
    const navRoot = document.getElementById('navigation-root');
    if (navRoot) {
      navRoot.innerHTML = this.components.navigation.render();
    }

    // Balance Card
    this.components.balanceCard = new BalanceCard({
      balance: this.state.user?.balance || 0,
      currency: 'USD',
      onDeposit: this.handleDeposit.bind(this),
      onHistory: this.handleHistory.bind(this)
    });
    const balanceRoot = document.getElementById('balance-card-root');
    if (balanceRoot) {
      balanceRoot.innerHTML = this.components.balanceCard.render();
      this.components.balanceCard.init();
    }

    // Services Grid
    this.components.servicesGrid = new ServicesGrid({
      services: [],
      onServiceClick: this.handleServiceClick.bind(this)
    });
    const servicesRoot = document.getElementById('services-grid-root');
    if (servicesRoot) {
      servicesRoot.innerHTML = this.components.servicesGrid.render();
      this.components.servicesGrid.init();
    }

    // Recent Orders
    this.components.recentOrders = new RecentOrders({
      orders: [],
      onOrderClick: this.handleOrderClick.bind(this),
      onViewAll: this.handleViewAllOrders.bind(this)
    });
    const ordersRoot = document.getElementById('recent-orders-root');
    if (ordersRoot) {
      ordersRoot.innerHTML = this.components.recentOrders.render();
      this.components.recentOrders.init();
    }

    // Додаємо іконки в заголовки секцій
    const servicesIcon = document.getElementById('services-icon');
    if (servicesIcon) {
      servicesIcon.innerHTML = getIcon('services', '', 24);
    }

    const ordersIcon = document.getElementById('orders-icon');
    if (ordersIcon) {
      ordersIcon.innerHTML = getIcon('orders', '', 24);
    }
  }

  /**
   * Завантаження початкових даних
   */
  async loadInitialData() {
    try {
      console.log('Loading initial data...');

      // Завантажуємо паралельно
      const [servicesResponse, ordersResponse, statsResponse] = await Promise.all([
        this.loadServices(),
        this.loadOrders(),
        this.loadStats()
      ]);

      // Оновлюємо стан
      if (servicesResponse) {
        this.state.services = servicesResponse;
        this.components.servicesGrid.update({
          services: servicesResponse,
          isLoading: false
        });
      }

      if (ordersResponse) {
        this.state.orders = ordersResponse;
        this.components.recentOrders.update({
          orders: ordersResponse,
          isLoading: false
        });

        // Оновлюємо лічильник в навігації
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

      console.log('Initial data loaded successfully');

    } catch (error) {
      console.error('Failed to load initial data:', error);
    }
  }

  /**
   * Завантаження сервісів
   */
  async loadServices() {
    try {
      // Перевіряємо кеш
      const cached = servicesCache.get('telegram_services');
      if (cached) {
        console.log('Using cached services');
        return cached;
      }

      // Завантажуємо тільки Telegram сервіси
      const response = await ServicesAPI.getAll({
        category: 'telegram',
        active: true,
        limit: 6 // Популярні сервіси
      });

      if (response.success && response.data.services) {
        const services = response.data.services;
        servicesCache.set('telegram_services', services, 3600000); // 1 година
        return services;
      }

      return [];
    } catch (error) {
      console.error('Failed to load services:', error);
      return [];
    }
  }

  /**
   * Завантаження замовлень
   */
  async loadOrders() {
    try {
      // Перевіряємо кеш
      const cached = ordersCache.get(`user_orders_${this.state.user.id}`);
      if (cached) {
        console.log('Using cached orders');
        return cached;
      }

      // Завантажуємо останні замовлення
      const response = await OrdersAPI.getAll({
        limit: 5,
        page: 1
      });

      if (response.success && response.data.orders) {
        const orders = response.data.orders;
        ordersCache.set(`user_orders_${this.state.user.id}`, orders, 180000); // 3 хвилини
        return orders;
      }

      return [];
    } catch (error) {
      console.error('Failed to load orders:', error);
      return [];
    }
  }

  /**
   * Завантаження статистики
   */
  async loadStats() {
    try {
      const response = await StatsAPI.getLive();

      if (response.success && response.data) {
        return {
          totalUsers: response.data.total_users || 15234,
          totalOrders: response.data.total_orders || 45678,
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
   * Підписка на realtime оновлення
   */
  subscribeToRealtimeUpdates() {
    // Підписка на оновлення балансу
    const balanceUnsubscribe = RealtimeSubscriptions.onBalanceUpdate((data) => {
      this.components.balanceCard.update({ balance: data.new });
      this.showToast(`Баланс оновлено: ${data.difference > 0 ? '+' : ''}${data.difference.toFixed(2)} USD`, 'info');
    });
    this.subscriptions.push(balanceUnsubscribe);

    // Підписка на нові замовлення
    const orderUnsubscribe = RealtimeSubscriptions.onNewOrder((order) => {
      this.state.orders.unshift(order);
      this.components.recentOrders.update({ orders: this.state.orders.slice(0, 5) });
      this.showToast('Нове замовлення створено', 'success');
    });
    this.subscriptions.push(orderUnsubscribe);

    // Підписка на зміну статусу замовлень
    const statusUnsubscribe = RealtimeSubscriptions.onOrderStatusChange((data) => {
      const orderIndex = this.state.orders.findIndex(o => o.id === data.orderId);
      if (orderIndex !== -1) {
        this.state.orders[orderIndex].status = data.newStatus;
        this.components.recentOrders.update({ orders: this.state.orders.slice(0, 5) });

        if (data.newStatus === 'completed') {
          this.showToast(`Замовлення #${data.orderId.slice(0, 8)} виконано!`, 'success');
        }
      }
    });
    this.subscriptions.push(statusUnsubscribe);
  }

  /**
   * Оновлення статистики
   */
  updateStats(stats) {
    // Анімоване оновлення чисел
    this.animateValue('total-users', 0, stats.totalUsers, 2000);
    this.animateValue('total-orders', 0, stats.totalOrders, 2000);

    const successElement = document.getElementById('success-rate');
    if (successElement) {
      successElement.textContent = `${stats.successRate}%`;
    }
  }

  /**
   * Анімація числових значень
   */
  animateValue(elementId, start, end, duration) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const startTime = performance.now();
    const update = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      const currentValue = Math.floor(start + (end - start) * progress);
      element.textContent = currentValue.toLocaleString('uk-UA');

      if (progress < 1) {
        requestAnimationFrame(update);
      }
    };

    requestAnimationFrame(update);
  }

  /**
   * Приховати skeleton loaders
   */
  hideSkeletons() {
    const skeletons = document.querySelectorAll('.skeleton-loader, .services-skeleton, .orders-skeleton');
    skeletons.forEach(skeleton => {
      skeleton.style.display = 'none';
    });
  }

  /**
   * Обробники подій
   */
  handleMenuClick(isOpen) {
    console.log('Menu clicked:', isOpen);
  }

  handleNavigate(item) {
    window.location.href = item.path;
  }

  handleDeposit() {
    window.location.href = '/balance';
  }

  handleHistory() {
    window.location.href = '/balance#transactions';
  }

  handleServiceClick(service) {
    window.location.href = `/services#service-${service.id}`;
  }

  handleOrderClick(order) {
    window.location.href = `/orders#order-${order.id}`;
  }

  handleViewAllOrders() {
    window.location.href = '/orders';
  }

  /**
   * Показати повідомлення
   */
  showToast(message, type = 'info') {
    if (window.showToast) {
      window.showToast(message, type);
    }
  }

  /**
   * Показати помилку
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

      // Автоматично приховати через 5 секунд
      setTimeout(() => {
        errorContainer.remove();
      }, 5000);
    }
  }

  /**
   * Очищення при знищенні
   */
  destroy() {
    // Відписуємось від усіх підписок
    this.subscriptions.forEach(unsubscribe => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    });

    // Очищаємо компоненти
    Object.values(this.components).forEach(component => {
      if (component.destroy) {
        component.destroy();
      }
    });
  }
}

// Ініціалізація сторінки при завантаженні
document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM Content Loaded, initializing HomePage...');

  const homePage = new HomePage();
  homePage.init();

  // Зберігаємо в глобальну змінну для відлагодження
  window.homePage = homePage;
});