// frontend/shared/core/Component.js
/**
 * Базовий клас для всіх компонентів TeleBoost
 * Забезпечує уніфікований підхід до управління станом та життєвим циклом
 */

export default class Component {
  constructor(options = {}) {
    // Стан компонента
    this.state = {};

    // Опції
    this.options = options;

    // DOM елементи
    this.element = null;
    this.container = null;

    // Прапорці
    this.mounted = false;
    this.destroyed = false;

    // Слухачі подій
    this.listeners = new Map();
    this.subscriptions = [];
  }

  /**
   * Встановити стан компонента
   */
  setState(updates) {
    const prevState = { ...this.state };
    this.state = { ...this.state, ...updates };

    if (this.mounted && !this.destroyed) {
      this.onStateChange(prevState, this.state);
      this.rerender();
    }
  }

  /**
   * Отримати стан
   */
  getState() {
    return { ...this.state };
  }

  /**
   * Рендер компонента (має бути перевизначений в дочірніх класах)
   */
  render() {
    throw new Error('render() method must be implemented');
  }

  /**
   * Монтування компонента в DOM
   */
  mount(container) {
    if (this.mounted) {
      console.warn('Component is already mounted');
      return;
    }

    this.container = container;

    // Очищаємо контейнер
    if (typeof container === 'string') {
      this.container = document.querySelector(container);
    }

    if (!this.container) {
      throw new Error('Container not found');
    }

    // Рендеримо HTML
    this.container.innerHTML = this.render();

    // Зберігаємо референцію на елемент
    this.element = this.container.firstElementChild || this.container;

    // Встановлюємо прапорець
    this.mounted = true;

    // Викликаємо lifecycle методи
    this.afterMount();
    this.bindEvents();
  }

  /**
   * Перерендер компонента
   */
  rerender() {
    if (!this.mounted || this.destroyed) return;

    // Зберігаємо скрол позицію
    const scrollTop = this.element?.scrollTop || 0;
    const scrollLeft = this.element?.scrollLeft || 0;

    // Відв'язуємо події
    this.unbindEvents();

    // Рендеримо новий HTML
    const newHTML = this.render();

    // Оновлюємо DOM
    if (this.element && this.element.outerHTML) {
      this.element.outerHTML = newHTML;

      // Оновлюємо референцію
      if (this.container.firstElementChild) {
        this.element = this.container.firstElementChild;
      } else {
        this.element = this.container;
      }
    } else {
      this.container.innerHTML = newHTML;
      this.element = this.container.firstElementChild || this.container;
    }

    // Відновлюємо скрол
    if (this.element) {
      this.element.scrollTop = scrollTop;
      this.element.scrollLeft = scrollLeft;
    }

    // Прив'язуємо події знову
    this.bindEvents();
    this.afterUpdate();
  }

  /**
   * Прив'язка подій (має бути перевизначений в дочірніх класах)
   */
  bindEvents() {
    // Override in child classes
  }

  /**
   * Відв'язка подій
   */
  unbindEvents() {
    this.listeners.forEach((listener, key) => {
      const [element, event] = key.split(':');
      const el = this.element?.querySelector(element) || this.element;
      if (el) {
        el.removeEventListener(event, listener);
      }
    });
    this.listeners.clear();
  }

  /**
   * Додати слухача події
   */
  addEventListener(selector, event, handler) {
    const element = selector === 'self' ? this.element : this.element?.querySelector(selector);

    if (!element) {
      console.warn(`Element ${selector} not found`);
      return;
    }

    element.addEventListener(event, handler);
    this.listeners.set(`${selector}:${event}`, handler);
  }

  /**
   * Делегування подій
   */
  delegate(event, selector, handler) {
    const delegatedHandler = (e) => {
      const target = e.target.closest(selector);
      if (target && this.element.contains(target)) {
        handler.call(target, e);
      }
    };

    this.addEventListener('self', event, delegatedHandler);
  }

  /**
   * Lifecycle hooks
   */
  afterMount() {
    // Override in child classes
  }

  afterUpdate() {
    // Override in child classes
  }

  beforeDestroy() {
    // Override in child classes
  }

  onStateChange(prevState, nextState) {
    // Override in child classes
  }

  /**
   * Знищення компонента
   */
  destroy() {
    if (this.destroyed) return;

    // Викликаємо hook
    this.beforeDestroy();

    // Відв'язуємо події
    this.unbindEvents();

    // Відписуємось від всіх підписок
    this.subscriptions.forEach(unsubscribe => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    });
    this.subscriptions = [];

    // Видаляємо з DOM
    if (this.element) {
      this.element.remove();
    }

    // Очищаємо референції
    this.element = null;
    this.container = null;

    // Встановлюємо прапорці
    this.mounted = false;
    this.destroyed = true;
  }

  /**
   * Утиліти
   */

  // Пошук елемента
  $(selector) {
    return this.element?.querySelector(selector);
  }

  // Пошук всіх елементів
  $$(selector) {
    return this.element?.querySelectorAll(selector) || [];
  }

  // Показати елемент
  show() {
    if (this.element) {
      this.element.style.display = '';
    }
  }

  // Сховати елемент
  hide() {
    if (this.element) {
      this.element.style.display = 'none';
    }
  }

  // Додати клас
  addClass(className) {
    if (this.element) {
      this.element.classList.add(className);
    }
  }

  // Видалити клас
  removeClass(className) {
    if (this.element) {
      this.element.classList.remove(className);
    }
  }

  // Перемкнути клас
  toggleClass(className) {
    if (this.element) {
      this.element.classList.toggle(className);
    }
  }

  // Встановити атрибут
  setAttribute(name, value) {
    if (this.element) {
      this.element.setAttribute(name, value);
    }
  }

  // Отримати атрибут
  getAttribute(name) {
    return this.element?.getAttribute(name);
  }

  // Видалити атрибут
  removeAttribute(name) {
    if (this.element) {
      this.element.removeAttribute(name);
    }
  }
}

/**
 * Міксін для компонентів з формами
 */
export const FormMixin = {
  // Отримати дані форми
  getFormData(formSelector) {
    const form = this.$(formSelector);
    if (!form) return {};

    const formData = new FormData(form);
    const data = {};

    for (const [key, value] of formData.entries()) {
      data[key] = value;
    }

    return data;
  },

  // Встановити значення форми
  setFormData(formSelector, data) {
    const form = this.$(formSelector);
    if (!form) return;

    Object.keys(data).forEach(key => {
      const input = form.elements[key];
      if (input) {
        if (input.type === 'checkbox') {
          input.checked = Boolean(data[key]);
        } else if (input.type === 'radio') {
          const radio = form.querySelector(`input[name="${key}"][value="${data[key]}"]`);
          if (radio) radio.checked = true;
        } else {
          input.value = data[key];
        }
      }
    });
  },

  // Валідація форми
  validateForm(formSelector, rules) {
    const form = this.$(formSelector);
    if (!form) return { valid: false, errors: {} };

    const errors = {};
    let valid = true;

    Object.keys(rules).forEach(field => {
      const input = form.elements[field];
      const value = input?.value;
      const fieldRules = rules[field];

      if (fieldRules.required && !value) {
        errors[field] = 'This field is required';
        valid = false;
      } else if (fieldRules.minLength && value.length < fieldRules.minLength) {
        errors[field] = `Minimum length is ${fieldRules.minLength}`;
        valid = false;
      } else if (fieldRules.pattern && !fieldRules.pattern.test(value)) {
        errors[field] = fieldRules.message || 'Invalid format';
        valid = false;
      }
    });

    return { valid, errors };
  }
};

/**
 * Міксін для компонентів зі списками
 */
export const ListMixin = {
  // Рендер списку
  renderList(items, renderItem, emptyMessage = 'No items') {
    if (!items || items.length === 0) {
      return `<div class="empty-list">${emptyMessage}</div>`;
    }

    return items.map(renderItem).join('');
  },

  // Фільтрація списку
  filterList(items, query, fields) {
    if (!query) return items;

    const lowerQuery = query.toLowerCase();

    return items.filter(item => {
      return fields.some(field => {
        const value = item[field];
        return value && value.toString().toLowerCase().includes(lowerQuery);
      });
    });
  },

  // Сортування списку
  sortList(items, field, direction = 'asc') {
    return [...items].sort((a, b) => {
      const aVal = a[field];
      const bVal = b[field];

      if (aVal < bVal) return direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return direction === 'asc' ? 1 : -1;
      return 0;
    });
  },

  // Пагінація списку
  paginateList(items, page, perPage) {
    const start = (page - 1) * perPage;
    const end = start + perPage;

    return {
      items: items.slice(start, end),
      totalPages: Math.ceil(items.length / perPage),
      currentPage: page,
      hasNext: end < items.length,
      hasPrev: page > 1
    };
  }
};

/**
 * Функція для застосування міксінів
 */
export function applyMixins(targetClass, ...mixins) {
  mixins.forEach(mixin => {
    Object.getOwnPropertyNames(mixin).forEach(name => {
      targetClass.prototype[name] = mixin[name];
    });
  });
}