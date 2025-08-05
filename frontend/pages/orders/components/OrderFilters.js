// frontend/pages/orders/components/OrderFilters.js
/**
 * OrderFilters компонент у стилі Horizontal Pills
 * Фільтри для замовлень з пошуком та категоріями
 */

import Component from '../../../shared/core/Component.js';
import { debounce } from '../../../shared/utils/helpers.js';

export default class OrderFilters extends Component {
  constructor(options = {}) {
    super(options);

    this.state = {
      searchQuery: '',
      activeStatus: 'all',
      activeCategory: null,
      showCategoryDropdown: false,
      counts: options.counts || {
        all: 0,
        active: 0,
        completed: 0,
        paused: 0,
        cancelled: 0
      },
      categories: options.categories || []
    };

    this.onFilterChange = options.onFilterChange || (() => {});
    this.onSearchChange = options.onSearchChange || (() => {});
    this.debouncedSearch = debounce(this.handleSearchInput.bind(this), 300);
  }

  render() {
    const { searchQuery, activeStatus, activeCategory, showCategoryDropdown, counts, categories } = this.state;

    return `
      <div class="order-filters-container">
        <!-- Search Bar -->
        <div class="filters-search-section">
          <div class="search-input-container glass-pill">
            <svg class="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
            <input 
              type="text" 
              class="filters-search-input" 
              placeholder="Пошук по замовленнях..."
              value="${searchQuery}"
              autocomplete="off"
            >
            ${searchQuery ? `
              <button class="clear-search-btn" aria-label="Очистити пошук">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            ` : ''}
          </div>
        </div>

        <!-- Status Pills -->
        <div class="status-pills-container">
          ${this.renderStatusPill('all', 'Всі замовлення', counts.all)}
          ${this.renderStatusPill('active', 'Активні', counts.active, 'status-active')}
          ${this.renderStatusPill('completed', 'Виконані', counts.completed, 'status-completed')}
          ${this.renderStatusPill('paused', 'Призупинені', counts.paused, 'status-paused')}
          ${this.renderStatusPill('cancelled', 'Скасовані', counts.cancelled, 'status-cancelled')}
        </div>

        <!-- Active Filters Bar -->
        ${this.renderActiveFilters()}
      </div>
    `;
  }

  renderStatusPill(status, label, count, statusClass = '') {
    const isActive = this.state.activeStatus === status;
    const hasItems = count > 0;

    return `
      <button 
        class="status-pill ${isActive ? 'active' : ''} ${!hasItems ? 'disabled' : ''} ${statusClass}" 
        data-status="${status}"
        ${!hasItems ? 'disabled' : ''}
      >
        ${this.getStatusIcon(status)}
        <span class="pill-label">${label}</span>
        <span class="pill-count ${isActive ? 'active-count' : ''}">${count}</span>
      </button>
    `;
  }

  renderActiveFilters() {
    const { searchQuery, activeCategory } = this.state;
    const hasActiveFilters = searchQuery || activeCategory;

    if (!hasActiveFilters) return '';

    return `
      <div class="active-filters-bar glass-card">
        <span class="active-filters-label">Активні фільтри:</span>
        
        ${searchQuery ? `
          <div class="filter-tag">
            <span>Пошук: ${searchQuery}</span>
            <button class="remove-filter" data-filter="search">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        ` : ''}
        
        ${activeCategory ? `
          <div class="filter-tag">
            <span>Категорія: ${this.getCategoryName(activeCategory)}</span>
            <button class="remove-filter" data-filter="category">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        ` : ''}
        
        <button class="clear-all-filters">Очистити все</button>
      </div>
    `;
  }

  getStatusIcon(status) {
    const icons = {
      all: '',
      active: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 1 1-6.219-8.56" stroke-linecap="round"/>
      </svg>`,
      completed: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="m9 12 2 2 4-4"/>
      </svg>`,
      paused: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="6" y="4" width="4" height="16"/>
        <rect x="14" y="4" width="4" height="16"/>
      </svg>`,
      cancelled: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="15" y1="9" x2="9" y2="15"/>
        <line x1="9" y1="9" x2="15" y2="15"/>
      </svg>`
    };

    return icons[status] || '';
  }

  getCategoryName(categoryKey) {
    const category = this.state.categories.find(c => c.key === categoryKey);
    return category?.name || categoryKey;
  }

  bindEvents() {
    // Search input
    const searchInput = this.element?.querySelector('.filters-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => this.debouncedSearch(e));
      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.clearSearch();
        }
      });
    }

    // Clear search button
    const clearSearchBtn = this.element?.querySelector('.clear-search-btn');
    if (clearSearchBtn) {
      clearSearchBtn.addEventListener('click', () => this.clearSearch());
    }

    // Status pills
    this.element?.querySelectorAll('.status-pill:not(.disabled)').forEach(pill => {
      pill.addEventListener('click', () => {
        const status = pill.dataset.status;
        this.setActiveStatus(status);
      });
    });

    // Remove filter tags
    this.element?.querySelectorAll('.remove-filter').forEach(btn => {
      btn.addEventListener('click', () => {
        const filterType = btn.dataset.filter;
        this.removeFilter(filterType);
      });
    });

    // Clear all filters
    const clearAllBtn = this.element?.querySelector('.clear-all-filters');
    if (clearAllBtn) {
      clearAllBtn.addEventListener('click', () => this.clearAllFilters());
    }
  }

  handleSearchInput(e) {
    const query = e.target.value;
    this.setState({ searchQuery: query });
    this.onSearchChange(query);
  }

  clearSearch() {
    this.setState({ searchQuery: '' });
    const input = this.element?.querySelector('.filters-search-input');
    if (input) input.value = '';
    this.onSearchChange('');
  }

  setActiveStatus(status) {
    if (this.state.activeStatus === status) return;

    this.setState({ activeStatus: status });
    this.onFilterChange({
      status,
      category: this.state.activeCategory,
      search: this.state.searchQuery
    });
  }

  removeFilter(filterType) {
    if (filterType === 'search') {
      this.clearSearch();
    } else if (filterType === 'category') {
      this.setState({ activeCategory: null });
      this.onFilterChange({
        status: this.state.activeStatus,
        category: null,
        search: this.state.searchQuery
      });
    }
  }

  clearAllFilters() {
    this.setState({
      searchQuery: '',
      activeStatus: 'all',
      activeCategory: null
    });

    const input = this.element?.querySelector('.filters-search-input');
    if (input) input.value = '';

    this.onFilterChange({
      status: 'all',
      category: null,
      search: ''
    });
  }

  updateCounts(newCounts) {
    this.setState({ counts: newCounts });
  }
}

// CSS для компонента
const styles = `
<style>
/* Order Filters Container */
.order-filters-container {
  margin-bottom: 24px;
}

/* Search Section */
.filters-search-section {
  margin-bottom: 16px;
}

.search-input-container {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  transition: all 0.3s ease;
}

.search-input-container:focus-within {
  border-color: rgba(168, 85, 247, 0.5);
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.1);
}

.search-icon {
  width: 20px;
  height: 20px;
  color: rgba(255, 255, 255, 0.5);
  flex-shrink: 0;
}

.filters-search-input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  font-size: 16px;
  color: white;
  font-family: inherit;
}

.filters-search-input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.clear-search-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  color: rgba(255, 255, 255, 0.6);
  flex-shrink: 0;
}

.clear-search-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  transform: scale(1.1);
}

/* Status Pills */
.status-pills-container {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
}

.status-pills-container::-webkit-scrollbar {
  display: none;
}

.status-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}

.status-pill::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
  transition: left 0.6s ease;
}

.status-pill:hover:not(.disabled) {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.12);
  transform: translateY(-2px);
  color: white;
}

.status-pill:hover:not(.disabled)::before {
  left: 100%;
}

.status-pill.active {
  background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
  border-color: transparent;
  color: white;
  box-shadow: 0 4px 15px rgba(168, 85, 247, 0.3);
}

.status-pill.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.status-pill svg {
  width: 16px;
  height: 16px;
}

.pill-label {
  font-weight: 600;
}

.pill-count {
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 700;
  min-width: 24px;
  text-align: center;
}

.pill-count.active-count {
  background: rgba(255, 255, 255, 0.3);
}

/* Status-specific colors on hover */
.status-pill.status-active:hover:not(.disabled) {
  border-color: rgba(59, 130, 246, 0.3);
  background: rgba(59, 130, 246, 0.1);
}

.status-pill.status-completed:hover:not(.disabled) {
  border-color: rgba(34, 197, 94, 0.3);
  background: rgba(34, 197, 94, 0.1);
}

.status-pill.status-paused:hover:not(.disabled) {
  border-color: rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.1);
}

.status-pill.status-cancelled:hover:not(.disabled) {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.1);
}

/* Active Filters Bar */
.active-filters-bar {
  margin-top: 16px;
  padding: 16px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.active-filters-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 500;
}

.filter-tag {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(168, 85, 247, 0.2);
  border: 1px solid rgba(168, 85, 247, 0.3);
  border-radius: 16px;
  font-size: 13px;
  color: white;
  animation: tagPop 0.3s ease;
}

@keyframes tagPop {
  0% {
    transform: scale(0.8);
    opacity: 0;
  }
  50% {
    transform: scale(1.05);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

.filter-tag span {
  font-weight: 500;
}

.remove-filter {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
  color: white;
}

.remove-filter:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

.clear-all-filters {
  margin-left: auto;
  padding: 8px 16px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.3s ease;
}

.clear-all-filters:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.3);
  color: white;
}

/* Category Dropdown */
.category-dropdown {
  position: relative;
}

.category-dropdown-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.3s ease;
}

.category-dropdown-toggle:hover {
  background: rgba(255, 255, 255, 0.08);
  color: white;
}

.category-dropdown-toggle.active {
  background: rgba(168, 85, 247, 0.2);
  border-color: rgba(168, 85, 247, 0.3);
  color: white;
}

.category-dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  min-width: 200px;
  background: rgba(20, 20, 20, 0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 8px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  z-index: 100;
  opacity: 0;
  visibility: hidden;
  transform: translateY(-10px);
  transition: all 0.3s ease;
}

.category-dropdown-menu.show {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.category-item {
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  transition: all 0.3s ease;
}

.category-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.category-item.active {
  background: rgba(168, 85, 247, 0.2);
  color: white;
}

/* Responsive */
@media (max-width: 480px) {
  .status-pills-container {
    gap: 8px;
  }

  .status-pill {
    padding: 10px 16px;
    font-size: 13px;
  }

  .active-filters-bar {
    padding: 12px;
  }

  .clear-all-filters {
    width: 100%;
    margin-left: 0;
    margin-top: 8px;
  }
}
</style>
`;

// Додаємо стилі
if (!document.getElementById('order-filters-styles')) {
  const styleElement = document.createElement('div');
  styleElement.id = 'order-filters-styles';
  styleElement.innerHTML = styles;
  document.head.appendChild(styleElement);
}