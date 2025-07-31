# backend/payments/providers/base.py
"""
TeleBoost Base Payment Provider
Абстрактний клас для платіжних провайдерів
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class BasePaymentProvider(ABC):
    """Базовий клас для всіх платіжних провайдерів"""

    def __init__(self):
        """Ініціалізація провайдера"""
        self.name = self.__class__.__name__.replace('Provider', '')
        self.is_active = True
        self.config = {}  # Дочірні класи можуть переписати це

    @abstractmethod
    def create_payment(self, amount: Decimal, currency: str,
                       **kwargs) -> Optional[Dict[str, Any]]:
        """
        Створити платіж

        Args:
            amount: Сума платежу
            currency: Валюта
            **kwargs: Додаткові параметри

        Returns:
            Dict з даними платежу або None при помилці
            Обов'язкові поля відповіді:
            - payment_id: ID платежу в системі провайдера
            - payment_url: URL для оплати
            - expires_at: Час закінчення (ISO format)
            - metadata: Додаткові дані
        """
        pass

    @abstractmethod
    def check_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Перевірити статус платежу

        Args:
            payment_id: ID платежу в системі провайдера

        Returns:
            Dict з даними статусу або None при помилці
            Обов'язкові поля відповіді:
            - status: Статус платежу (mapped to our statuses)
            - metadata: Додаткові дані від провайдера
        """
        pass

    @abstractmethod
    def process_webhook(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обробити webhook від провайдера

        Args:
            data: Дані webhook

        Returns:
            Dict з результатом обробки або None при помилці
            Обов'язкові поля відповіді:
            - payment_id: ID платежу в системі провайдера
            - status: Новий статус платежу
            - metadata: Додаткові дані
        """
        pass

    def get_supported_currencies(self) -> List[str]:
        """
        Отримати список підтримуваних валют

        Returns:
            Список валют (коди)
        """
        # Базова реалізація - дочірні класи можуть переписати
        return []

    def get_payment_limits(self, currency: str) -> Dict[str, Decimal]:
        """
        Отримати ліміти для валюти

        Args:
            currency: Код валюти

        Returns:
            Dict з полями min та max
        """
        # Базова реалізація - дочірні класи можуть переписати
        return {
            'min': Decimal('0.01'),
            'max': Decimal('999999.99')
        }

    def validate_amount(self, amount: Decimal, currency: str) -> bool:
        """
        Валідація суми платежу

        Args:
            amount: Сума
            currency: Валюта

        Returns:
            True якщо сума валідна
        """
        try:
            limits = self.get_payment_limits(currency)
            min_amount = limits.get('min', Decimal('0'))
            max_amount = limits.get('max', Decimal('999999999'))

            return min_amount <= amount <= max_amount
        except Exception as e:
            logger.error(f"Error validating amount: {e}")
            return False

    def format_amount(self, amount: Decimal, currency: str) -> str:
        """
        Форматування суми для API провайдера

        Args:
            amount: Сума
            currency: Валюта

        Returns:
            Відформатована сума як строка
        """
        # Більшість API приймають суми як строки
        # з фіксованою кількістю десяткових знаків
        from backend.utils.constants import CRYPTO_CURRENCIES

        decimals = CRYPTO_CURRENCIES.get(currency, {}).get('decimals', 2)
        format_str = f"{{:.{decimals}f}}"

        return format_str.format(amount)

    def generate_payment_description(self, payment_id: str) -> str:
        """
        Генерація опису платежу

        Args:
            payment_id: ID платежу в нашій системі

        Returns:
            Опис платежу
        """
        return f"TeleBoost Deposit #{payment_id}"

    def log_request(self, method: str, url: str, data: Optional[Dict] = None,
                    response: Optional[Dict] = None) -> None:
        """
        Логування API запитів

        Args:
            method: HTTP метод
            url: URL запиту
            data: Дані запиту
            response: Відповідь
        """
        logger.debug(f"{self.name} API Request: {method} {url}")

        if data:
            # Приховуємо чутливі дані
            safe_data = self._hide_sensitive_data(data)
            logger.debug(f"Request data: {safe_data}")

        if response:
            logger.debug(f"Response: {response}")

    def _hide_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Приховати чутливі дані для логування

        Args:
            data: Оригінальні дані

        Returns:
            Дані з прихованими секретами
        """
        sensitive_keys = ['api_key', 'secret', 'token', 'password', 'private_key']
        safe_data = data.copy()

        for key in safe_data:
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                safe_data[key] = '***HIDDEN***'

        return safe_data

    def handle_api_error(self, error: Exception, context: str = "") -> None:
        """
        Обробка помилок API

        Args:
            error: Виключення
            context: Контекст помилки
        """
        error_msg = f"{self.name} API Error"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {str(error)}"

        logger.error(error_msg)

    def is_retriable_error(self, error: Exception) -> bool:
        """
        Перевірка чи помилка може бути повторена

        Args:
            error: Виключення

        Returns:
            True якщо запит можна повторити
        """
        # Мережеві помилки та тимчасові проблеми
        retriable_errors = [
            'ConnectionError',
            'Timeout',
            'ServiceUnavailable',
            'GatewayTimeout',
        ]

        error_type = type(error).__name__
        return error_type in retriable_errors