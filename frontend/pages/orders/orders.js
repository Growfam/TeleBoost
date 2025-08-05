// frontend/pages/orders/orders.js
/**
 * Основна логіка сторінки замовлень
 * FIXED: Правильна перевірка авторизації
 */

import Navigation from '../../shared/components/Navigation.js';
import { ToastProvider } from '../../shared/components/Toast.js';
import AuthGuard from '../../shared/auth/AuthGuard.js';
import { ordersAPI } from './services/OrdersAPI.js';
import { ordersRealtime } from './services/OrdersRealtime.js';
import { formatPrice, formatDateTime, formatNumber } from '../../shared/utils/formatters.js';
import { ORDER_STATUS } from '../../shared/utils/constants.js';
import { apiClient } from '../../shared/services/APIClient.js';

// Стан сторінки
const state = {
  orders: [],
  filteredOrders: [],
  currentFilter: 'all',
  searchQuery: '',
  currentPage: 1,
  hasMore: false,
  isLoading: false,
  isLoadingMore: false,
  counts: {
    all: 0,
    active: 0,
    completed: 0,
    cancelled: 0
  }
};

// DOM елементи
const elements = {
  ordersList: null,
  searchInput: null,
  clearSearch: null,
  filterTabs: null,
  loadingState: null,
  emptyState: null,
  errorState: null,
  loadMoreContainer: null,
  loadMoreBtn: null,
  orderModal: null,
  modalContent: null
};

/**
 * Перевірка авторизації
 */
async function checkAuth() {
  console.log('Orders: Checking authorization...');

  // Перевіряємо наявність токена в localStorage
  const authData = localStorage.getItem('auth');
  console.log('Orders: Auth data exists:', !!authData);

  if (!authData) {
    console.log('Orders: No auth data, redirecting to login');
    window.location.href = '/login';
    return false;
  }

  try {
    const auth = JSON.parse(authData);
    console.log('Orders: Auth parsed, has token:', !!auth.access_token);

    if (!auth.access_token) {
      console.log('Orders: No access token, redirecting to login');
      window.location.href = '/login';
      return false;
    }

    // Перевіряємо чи не прострочений токен
    if (auth.expires_at) {
      const expiresAt = new Date(auth.expires_at);
      const now = new Date();
      console.log('Orders: Token expires at:', expiresAt);
      console.log('Orders: Current time:', now);

      if (expiresAt <= now) {
        console.log('Orders: Token expired, redirecting to login');
        localStorage.removeItem('auth');
        window.location.href = '/login';
        return false;
      }
    }

    // Переконуємося що apiClient має токени
    apiClient.loadTokens();
    console.log('Orders: ApiClient tokens loaded');

    return true;
  } catch (error) {
    console.error('Orders: Auth check error:', error);
    window.location.href = '/login';
    return false;
  }
}

/**
 * Ініціалізація сторінки
 */
async function init() {
  console.log('Orders: Page initialization started');

  // Перевіряємо авторизацію
  const isAuthorized = await checkAuth();
  if (!isAuthorized) {
    return;
  }

  console.log('Orders: User is authorized, continuing initialization');

  // Показуємо AuthGuard під час завантаження
  const authGuard = new AuthGuard({
    isLoading: true
  });
  authGuard.show();

  try {
    // Ініціалізуємо компоненти
    initializeToasts();
    initializeNavigation();
    initializeDOMElements();
    attachEventListeners();

    // Запускаємо real-time
    ordersRealtime.start();
    setupRealtimeCallbacks();

    // Завантажуємо замовлення
    await loadOrders();

    // Ховаємо AuthGuard
    authGuard.hide();

  } catch (error) {
    console.error('Orders: Initialization error:', error);

    authGuard.update({
      isLoading: false,
      error: 'Помилка завантаження замовлень'
    });

    // Якщо це 401 помилка - перенаправляємо на логін
    if (error.status === 401 || error.code === 'UNAUTHORIZED') {
      setTimeout(() => {
        window.location.href = '/login';
      }, 2000);
    }
  }
}

/**
 * Ініціалізація Toast
 */
function initializeToasts() {
  const toastProvider = new ToastProvider();
  toastProvider.init();
}

/**
 * Ініціалізація навігації
 */
function initializeNavigation() {
  const navContainer = document.getElementById('navigation');
  if (!navContainer) return;

  const navigation = new Navigation({
    activeItem: 'orders',
    onNavigate: (item) => {
      if (item.path !== '/orders') {
        window.location.href = item.path;
      }
    }
  });

  navContainer.innerHTML = navigation.render();
  navigation.init();
}

/**
 * Ініціалізація DOM елементів
 */
function initializeDOMElements() {
  elements.ordersList = document.getElementById('ordersList');
  elements.searchInput = document.getElementById('searchInput');
  elements.clearSearch = document.getElementById('clearSearch');
  elements.filterTabs = document.querySelectorAll('.filter-tab');
  elements.loadingState = document.getElementById('loadingState');
  elements.emptyState = document.getElementById('emptyState');
  elements.errorState = document.getElementById('errorState');
  elements.loadMoreContainer = document.getElementById('loadMoreContainer');
  elements.loadMoreBtn = document.getElementById('loadMoreBtn');
  elements.orderModal = document.getElementById('orderModal');
  elements.modalContent = document.getElementById('modalContent');
}

/**
 * Додати обробники подій
 */
function attachEventListeners() {
  // Кнопка назад
  document.getElementById('backButton')?.addEventListener('click', () => {
    window.history.back();
  });

  // Пошук
  elements.searchInput?.addEventListener('input', debounce(handleSearch, 300));
  elements.clearSearch?.addEventListener('click', clearSearch);

  // Фільтри
  elements.filterTabs.forEach(tab => {
    tab.addEventListener('click', () => handleFilterChange(tab));
  });

  // Кнопка "Завантажити ще"
  elements.loadMoreBtn?.addEventListener('click', loadMore);

  // Кнопка створення замовлення
  document.getElementById('createOrderBtn')?.addEventListener('click', () => {
    window.location.href = '/services';
  });

  // Кнопка повтору
  document.getElementById('retryBtn')?.addEventListener('click', () => {
    loadOrders();
  });

  // Закриття модалки
  document.getElementById('closeModal')?.addEventListener('click', closeModal);
  elements.orderModal?.addEventListener('click', (e) => {
    if (e.target === elements.orderModal) {
      closeModal();
    }
  });
}

/**
 * Завантажити замовлення
 */
async function loadOrders(page = 1) {
  if (state.isLoading) return;

  console.log('Orders: Loading orders, page:', page);

  try {
    showLoadingState();
    state.isLoading = true;

    const response = await ordersAPI.list({
      page,
      limit: 20,
      status: state.currentFilter === 'all' ? undefined : state.currentFilter
    });

    console.log('Orders: Loaded orders:', {
      count: response.orders?.length || 0,
      page: response.pagination?.page,
      hasMore: response.pagination?.page < response.pagination?.pages
    });

    if (page === 1) {
      state.orders = response.orders || [];
    } else {
      state.orders = [...state.orders, ...(response.orders || [])];
    }

    state.currentPage = response.pagination?.page || 1;
    state.hasMore = state.currentPage < (response.pagination?.pages || 1);

    // Оновлюємо лічильники
    updateCounts();

    // Застосовуємо фільтри та рендеримо
    applyFilters();
    renderOrders();

    // Відслідковуємо активні замовлення
    trackActiveOrders();

  } catch (error) {
    console.error('Orders: Error loading orders:', error);

    // Якщо 401 - перенаправляємо на логін
    if (error.status === 401) {
      console.log('Orders: Unauthorized, redirecting to login');
      window.location.href = '/login';
      return;
    }

    showErrorState(error.message || 'Не вдалося завантажити замовлення');
  } finally {
    state.isLoading = false;
    hideLoadingState();
  }
}

/**
 * Завантажити більше замовлень
 */
async function loadMore() {
  if (state.isLoadingMore || !state.hasMore) return;

  try {
    state.isLoadingMore = true;
    elements.loadMoreBtn.disabled = true;
    elements.loadMoreBtn.innerHTML = '<span>Завантаження...</span>';

    await loadOrders(state.currentPage + 1);

  } finally {
    state.isLoadingMore = false;
    elements.loadMoreBtn.disabled = false;
    elements.loadMoreBtn.innerHTML = `
      <span>Завантажити ще</span>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="12" y1="5" x2="12" y2="19"/>
        <polyline points="19 12 12 19 5 12"/>
      </svg>
    `;
  }
}

/**
 * Обробка пошуку
 */
function handleSearch(e) {
  state.searchQuery = e.target.value.toLowerCase();
  elements.clearSearch.style.display = state.searchQuery ? 'flex' : 'none';
  applyFilters();
  renderOrders();
}

/**
 * Очистити пошук
 */
function clearSearch() {
  state.searchQuery = '';
  elements.searchInput.value = '';
  elements.clearSearch.style.display = 'none';
  applyFilters();
  renderOrders();
}

/**
 * Обробка зміни фільтра
 */
function handleFilterChange(tab) {
  // Оновлюємо активний стан
  elements.filterTabs.forEach(t => t.classList.remove('active'));
  tab.classList.add('active');

  // Оновлюємо фільтр
  state.currentFilter = tab.dataset.filter;

  // Перезавантажуємо з новим фільтром
  state.currentPage = 1;
  loadOrders();
}

/**
 * Застосувати фільтри
 */
function applyFilters() {
  state.filteredOrders = state.orders.filter(order => {
    // Пошук
    if (state.searchQuery) {
      const searchMatch =
        order.order_number?.toLowerCase().includes(state.searchQuery) ||
        order.id?.toLowerCase().includes(state.searchQuery) ||
        order.service_name?.toLowerCase().includes(state.searchQuery) ||
        order.link?.toLowerCase().includes(state.searchQuery);

      if (!searchMatch) return false;
    }

    return true;
  });
}

/**
 * Оновити лічильники
 */
function updateCounts() {
  state.counts = {
    all: state.orders.length,
    active: 0,
    completed: 0,
    cancelled: 0
  };

  state.orders.forEach(order => {
    if (['pending', 'processing', 'in_progress'].includes(order.status)) {
      state.counts.active++;
    } else if (order.status === 'completed') {
      state.counts.completed++;
    } else if (['cancelled', 'failed'].includes(order.status)) {
      state.counts.cancelled++;
    }
  });

  // Оновлюємо UI
  document.getElementById('countAll').textContent = state.counts.all;
  document.getElementById('countActive').textContent = state.counts.active;
  document.getElementById('countCompleted').textContent = state.counts.completed;
  document.getElementById('countCancelled').textContent = state.counts.cancelled;
}

/**
 * Рендер замовлень
 */
function renderOrders() {
  if (!elements.ordersList) return;

  if (state.filteredOrders.length === 0) {
    showEmptyState();
    return;
  }

  hideEmptyState();
  elements.ordersList.innerHTML = state.filteredOrders.map(order => renderOrderCard(order)).join('');

  // Додаємо обробники кліків
  elements.ordersList.querySelectorAll('.order-card').forEach(card => {
    card.addEventListener('click', (e) => {
      if (!e.target.closest('.action-btn')) {
        openOrderDetails(card.dataset.orderId);
      }
    });

    // Обробники для кнопок дій
    card.querySelectorAll('.action-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        handleOrderAction(btn.dataset.action, card.dataset.orderId);
      });
    });
  });

  // Показуємо/ховаємо кнопку "Завантажити ще"
  if (state.hasMore && state.filteredOrders.length >= 20) {
    elements.loadMoreContainer.style.display = 'block';
  } else {
    elements.loadMoreContainer.style.display = 'none';
  }
}

/**
 * Рендер картки замовлення
 */
function renderOrderCard(order) {
  const statusClass = getStatusClass(order.status);
  const progress = order.quantity ? Math.round((order.completed / order.quantity) * 100) : 0;
  const hasProgress = ['processing', 'in_progress'].includes(order.status) && order.quantity;

  return `
    <div class="order-card ${statusClass}" data-order-id="${order.id}">
      <div class="order-header">
        <div class="order-main-info">
          <div class="order-id">#${order.order_number || order.id.slice(0, 8)}</div>
          <div class="order-service">
            ${getServiceIcon(order.service?.category?.key || 'default')}
            <span>${order.service_name}</span>
          </div>
          <div class="order-link">${order.link}</div>
        </div>
        <div class="order-status ${statusClass}">
          ${getStatusText(order.status)}
        </div>
      </div>

      <div class="order-details">
        <div class="order-detail">
          <div class="detail-label">Кількість</div>
          <div class="detail-value">${formatNumber(order.quantity || 0)}</div>
        </div>
        <div class="order-detail">
          <div class="detail-label">Виконано</div>
          <div class="detail-value">${formatNumber(order.completed || 0)}</div>
        </div>
        <div class="order-detail">
          <div class="detail-label">Ціна</div>
          <div class="detail-value">${formatPrice(order.charge || 0)}</div>
        </div>
      </div>

      ${hasProgress ? `
        <div class="order-progress">
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${progress}%"></div>
          </div>
          <div class="progress-info">
            <span>${progress}% виконано</span>
            <span>${order.remains || 0} залишилось</span>
          </div>
        </div>
      ` : ''}

      <div class="order-footer">
        <div class="order-date">${formatDateTime(order.created_at)}</div>
        <div class="order-actions">
          <button class="action-btn" data-action="details">Деталі</button>
          ${getActionButtons(order)}
        </div>
      </div>
    </div>
  `;
}

/**
 * Отримати іконку сервісу
 */
function getServiceIcon(category) {
  const icons = {
    telegram: '<svg class="order-service-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M21.198 2.433a2.242 2.242 0 0 0-1.022.215l-8.609 3.33c-2.068.8-4.133 1.598-5.724 2.21a405.15 405.15 0 0 1-2.849 1.09c-.42.147-.99.332-1.473.901-.728.968.193 1.798.919 2.112 1.058.46 2.06.745 3.059 1.122 1.074.409 2.156.842 3.23 1.295l-.138-.03c.265.624.535 1.239.804 1.858.382.883.761 1.769 1.137 2.663.19.448.521 1.05 1.08 1.246.885.32 1.694-.244 2.122-.715l1.358-1.493c.858.64 1.708 1.271 2.558 1.921l.033.025c1.153.865 1.805 1.354 2.495 1.592.728.25 1.361.151 1.88-.253.506-.395.748-.987.818-1.486.308-2.17.63-4.335.919-6.507.316-2.378.63-4.764.867-7.158.094-.952.187-1.912.272-2.875.046-.523.153-1.308-.327-1.83a1.743 1.743 0 0 0-.965-.465z"/></svg>',
    instagram: '<svg class="order-service-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg>',
    youtube: '<svg class="order-service-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z"/><polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02"/></svg>',
    default: '<svg class="order-service-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>'
  };

  return icons[category] || icons.default;
}

/**
 * Отримати клас статусу
 */
function getStatusClass(status) {
  return `status-${status}`;
}

/**
 * Отримати текст статусу
 */
function getStatusText(status) {
  const texts = {
    pending: 'Очікує',
    processing: 'Обробка',
    in_progress: 'Виконується',
    completed: 'Виконано',
    partial: 'Частково',
    cancelled: 'Скасовано',
    failed: 'Помилка'
  };

  return texts[status] || status;
}

/**
 * Отримати кнопки дій
 */
function getActionButtons(order) {
  const buttons = [];

  if (['pending', 'processing', 'in_progress'].includes(order.status)) {
    if (order.service?.cancel) {
      buttons.push('<button class="action-btn" data-action="cancel">Скасувати</button>');
    }
  } else if (order.status === 'completed') {
    buttons.push('<button class="action-btn" data-action="repeat">Повторити</button>');
    if (order.service?.refill) {
      buttons.push('<button class="action-btn" data-action="refill">Поповнити</button>');
    }
  } else if (['cancelled', 'failed'].includes(order.status)) {
    buttons.push('<button class="action-btn" data-action="repeat">Замовити знову</button>');
  }

  return buttons.join('');
}

/**
 * Обробка дій з замовленням
 */
async function handleOrderAction(action, orderId) {
  try {
    switch (action) {
      case 'details':
        openOrderDetails(orderId);
        break;

      case 'cancel':
        if (confirm('Скасувати це замовлення?')) {
          await cancelOrder(orderId);
        }
        break;

      case 'repeat':
        if (confirm('Повторити це замовлення?')) {
          await repeatOrder(orderId);
        }
        break;

      case 'refill':
        if (confirm('Запросити поповнення для цього замовлення?')) {
          await requestRefill(orderId);
        }
        break;
    }
  } catch (error) {
    console.error('Action error:', error);
    if (window.showToast) {
      window.showToast(error.message || 'Помилка виконання дії', 'error');
    }
  }
}

/**
 * Відкрити деталі замовлення
 */
async function openOrderDetails(orderId) {
  try {
    showModalLoading();
    elements.orderModal.style.display = 'flex';

    const response = await ordersAPI.get(orderId);
    const order = response.order;

    if (!order) {
      throw new Error('Замовлення не знайдено');
    }

    renderOrderDetails(order);

  } catch (error) {
    console.error('Error loading order details:', error);
    elements.modalContent.innerHTML = `
      <div class="error-state">
        <p>Не вдалося завантажити деталі замовлення</p>
      </div>
    `;
  }
}

/**
 * Рендер деталей замовлення
 */
function renderOrderDetails(order) {
  const progress = order.quantity ? Math.round((order.completed / order.quantity) * 100) : 0;

  elements.modalContent.innerHTML = `
    <div class="order-details-content">
      <div class="order-detail-section">
        <h3>Інформація про замовлення</h3>
        <div class="detail-row">
          <span class="detail-label">ID замовлення:</span>
          <span class="detail-value">#${order.order_number || order.id.slice(0, 8)}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Статус:</span>
          <span class="order-status ${getStatusClass(order.status)}">${getStatusText(order.status)}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Створено:</span>
          <span class="detail-value">${formatDateTime(order.created_at)}</span>
        </div>
        ${order.updated_at ? `
          <div class="detail-row">
            <span class="detail-label">Оновлено:</span>
            <span class="detail-value">${formatDateTime(order.updated_at)}</span>
          </div>
        ` : ''}
      </div>

      <div class="order-detail-section">
        <h3>Сервіс</h3>
        <div class="detail-row">
          <span class="detail-label">Назва:</span>
          <span class="detail-value">${order.service_name}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Категорія:</span>
          <span class="detail-value">${order.service?.category?.name || 'Інше'}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Посилання:</span>
          <span class="detail-value detail-link">${order.link}</span>
        </div>
      </div>

      <div class="order-detail-section">
        <h3>Прогрес</h3>
        <div class="detail-row">
          <span class="detail-label">Замовлено:</span>
          <span class="detail-value">${formatNumber(order.quantity || 0)}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Початкова кількість:</span>
          <span class="detail-value">${formatNumber(order.start_count || 0)}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Виконано:</span>
          <span class="detail-value">${formatNumber(order.completed || 0)}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Залишилось:</span>
          <span class="detail-value">${formatNumber(order.remains || 0)}</span>
        </div>
        ${order.quantity ? `
          <div class="progress-bar" style="margin-top: 12px;">
            <div class="progress-fill" style="width: ${progress}%"></div>
          </div>
          <div class="progress-info" style="margin-top: 8px;">
            <span>${progress}% виконано</span>
          </div>
        ` : ''}
      </div>

      <div class="order-detail-section">
        <h3>Оплата</h3>
        <div class="detail-row">
          <span class="detail-label">Вартість:</span>
          <span class="detail-value">${formatPrice(order.charge || 0)}</span>
        </div>
      </div>

      ${order.external_id ? `
        <div class="order-detail-section">
          <h3>Додаткова інформація</h3>
          <div class="detail-row">
            <span class="detail-label">External ID:</span>
            <span class="detail-value">${order.external_id}</span>
          </div>
        </div>
      ` : ''}
    </div>
  `;
}

/**
 * Скасувати замовлення
 */
async function cancelOrder(orderId) {
  try {
    const loadingToast = window.showToast('Скасування замовлення...', 'loading');

    const response = await ordersAPI.cancel(orderId);

    window.dismissToast(loadingToast);
    window.showToast(response.message || 'Замовлення скасовано', 'success');

    // Перезавантажуємо список
    await loadOrders();

  } catch (error) {
    window.showToast(error.message || 'Не вдалося скасувати замовлення', 'error');
  }
}

/**
 * Повторити замовлення
 */
async function repeatOrder(orderId) {
  try {
    const loadingToast = window.showToast('Створення нового замовлення...', 'loading');

    const response = await ordersAPI.repeat(orderId);

    window.dismissToast(loadingToast);
    window.showToast('Нове замовлення створено', 'success');

    // Перезавантажуємо список
    await loadOrders();

  } catch (error) {
    window.showToast(error.message || 'Не вдалося повторити замовлення', 'error');
  }
}

/**
 * Запросити поповнення
 */
async function requestRefill(orderId) {
  try {
    const loadingToast = window.showToast('Запит поповнення...', 'loading');

    const response = await ordersAPI.refill(orderId);

    window.dismissToast(loadingToast);
    window.showToast(response.message || 'Запит на поповнення надіслано', 'success');

  } catch (error) {
    window.showToast(error.message || 'Не вдалося запросити поповнення', 'error');
  }
}

/**
 * Закрити модалку
 */
function closeModal() {
  elements.orderModal.style.display = 'none';
  elements.modalContent.innerHTML = '';
}

/**
 * Показати стан завантаження в модалці
 */
function showModalLoading() {
  elements.modalContent.innerHTML = `
    <div class="loading-state" style="padding: 40px;">
      <div class="skeleton-card glass">
        <div class="skeleton-shimmer"></div>
      </div>
    </div>
  `;
}

/**
 * Налаштування real-time callbacks
 */
function setupRealtimeCallbacks() {
  // Оновлення при нових замовленнях або змінах
  ordersRealtime.onUpdate((data) => {
    if (data.type === 'new_order' || data.type === 'status_change') {
      // Перезавантажуємо список
      loadOrders();
    } else if (data.type === 'order_update') {
      // Оновлюємо конкретне замовлення
      updateOrderInList(data.order);
    }
  });
}

/**
 * Відслідковувати активні замовлення
 */
function trackActiveOrders() {
  const activeOrders = state.orders.filter(order =>
    ['pending', 'processing', 'in_progress'].includes(order.status)
  );

  activeOrders.forEach(order => {
    ordersRealtime.trackOrder(order.id, (data) => {
      updateOrderInList(data.order);
    });
  });
}

/**
 * Оновити замовлення в списку
 */
function updateOrderInList(updatedOrder) {
  const index = state.orders.findIndex(o => o.id === updatedOrder.id);
  if (index !== -1) {
    state.orders[index] = updatedOrder;
    applyFilters();
    renderOrders();
  }
}

/**
 * Показати стан завантаження
 */
function showLoadingState() {
  elements.loadingState.style.display = 'flex';
  elements.ordersList.style.display = 'none';
  elements.emptyState.style.display = 'none';
  elements.errorState.style.display = 'none';
}

/**
 * Сховати стан завантаження
 */
function hideLoadingState() {
  elements.loadingState.style.display = 'none';
  elements.ordersList.style.display = 'flex';
}

/**
 * Показати порожній стан
 */
function showEmptyState() {
  elements.ordersList.style.display = 'none';
  elements.emptyState.style.display = 'block';
  elements.loadMoreContainer.style.display = 'none';
}

/**
 * Сховати порожній стан
 */
function hideEmptyState() {
  elements.emptyState.style.display = 'none';
}

/**
 * Показати стан помилки
 */
function showErrorState(message) {
  elements.ordersList.style.display = 'none';
  elements.emptyState.style.display = 'none';
  elements.errorState.style.display = 'block';
  document.getElementById('errorMessage').textContent = message;
}

/**
 * Debounce функція
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Обробники глобальних подій
window.addEventListener('auth:logout', () => {
  console.log('Orders: Logout event received, redirecting to login');
  window.location.href = '/login';
});

// Запускаємо ініціалізацію
document.addEventListener('DOMContentLoaded', init);

// Зупиняємо real-time при виході
window.addEventListener('beforeunload', () => {
  ordersRealtime.stop();
});