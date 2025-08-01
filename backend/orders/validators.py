# backend/orders/validators.py
"""
TeleBoost Order Validators
Валідація даних для замовлень
"""
import re
import logging
from typing import Dict, Any, Tuple, Optional, List

from backend.services.models import Service
from backend.utils.constants import SERVICE_TYPE, OrderStatus
from backend.utils.validators import validate_url, validate_quantity

logger = logging.getLogger(__name__)


def validate_order_creation(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Валідація даних для створення замовлення

    Args:
        data: Дані замовлення

    Returns:
        (is_valid, list_of_errors)
    """
    errors = []

    # Обов'язкові поля
    if 'service_id' not in data:
        errors.append('Service ID is required')
    else:
        try:
            service_id = int(data['service_id'])
            if service_id <= 0:
                errors.append('Invalid service ID')
        except:
            errors.append('Service ID must be a number')

    if 'link' not in data or not data['link']:
        errors.append('Link is required')
    elif not validate_url(data['link']):
        errors.append('Invalid URL format')

    # Валідація специфічних полів буде в validate_order_parameters

    return len(errors) == 0, errors


def validate_order_parameters(service: Service, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Валідація параметрів замовлення відповідно до типу сервісу

    Args:
        service: Сервіс
        params: Параметри замовлення

    Returns:
        (is_valid, error_message)
    """
    service_type = service.type

    # DEFAULT - звичайне замовлення
    if service_type == SERVICE_TYPE.DEFAULT:
        if 'quantity' not in params:
            return False, 'Quantity is required'

        quantity = params.get('quantity')
        if not validate_quantity(quantity, service.min, service.max):
            return False, f'Quantity must be between {service.min} and {service.max}'

    # DRIP_FEED - поступова доставка
    elif service_type == SERVICE_TYPE.DRIP_FEED:
        # Перевірка quantity
        if 'quantity' not in params:
            return False, 'Quantity is required for drip-feed'

        quantity = params.get('quantity')
        if not validate_quantity(quantity, service.min, service.max):
            return False, f'Quantity must be between {service.min} and {service.max}'

        # Перевірка runs
        if 'runs' not in params:
            return False, 'Runs parameter is required for drip-feed'

        runs = params.get('runs')
        try:
            runs = int(runs)
            if runs < 1 or runs > 100:
                return False, 'Runs must be between 1 and 100'
        except:
            return False, 'Runs must be a valid number'

        # Перевірка interval
        if 'interval' not in params:
            return False, 'Interval parameter is required for drip-feed'

        interval = params.get('interval')
        try:
            interval = int(interval)
            if interval < 1 or interval > 60 * 24:  # 1 хвилина - 24 години
                return False, 'Interval must be between 1 and 1440 minutes (24 hours)'
        except:
            return False, 'Interval must be a valid number in minutes'

        # Перевірка загальної кількості
        total_quantity = quantity * runs
        if total_quantity > service.max:
            return False, f'Total quantity ({total_quantity}) exceeds service maximum ({service.max})'

    # CUSTOM_COMMENTS - власні коментарі
    elif service_type == SERVICE_TYPE.CUSTOM_COMMENTS:
        if 'comments' not in params or not params['comments']:
            return False, 'Comments are required for this service'

        comments = params['comments']
        if isinstance(comments, str):
            comments_list = [c.strip() for c in comments.split('\n') if c.strip()]
        elif isinstance(comments, list):
            comments_list = [str(c).strip() for c in comments if str(c).strip()]
        else:
            return False, 'Comments must be a string or list'

        if not comments_list:
            return False, 'At least one comment is required'

        comment_count = len(comments_list)
        if comment_count < service.min:
            return False, f'Minimum {service.min} comments required'
        if comment_count > service.max:
            return False, f'Maximum {service.max} comments allowed'

        # Перевірка довжини коментарів
        for comment in comments_list:
            if len(comment) > 500:  # Максимальна довжина коментаря
                return False, 'Comments must be less than 500 characters each'

    # POLL - голосування
    elif service_type == SERVICE_TYPE.POLL:
        if 'quantity' not in params:
            return False, 'Quantity is required for polls'

        quantity = params.get('quantity')
        if not validate_quantity(quantity, service.min, service.max):
            return False, f'Quantity must be between {service.min} and {service.max}'

        if 'answer_number' not in params:
            return False, 'Answer number is required for polls'

        answer = params.get('answer_number')
        try:
            answer_num = int(answer)
            if answer_num < 1 or answer_num > 10:
                return False, 'Answer number must be between 1 and 10'
        except:
            return False, 'Answer number must be a valid integer'

    # SUBSCRIPTION - підписки
    elif service_type == SERVICE_TYPE.SUBSCRIPTION:
        required_fields = ['username', 'min', 'max']

        for field in required_fields:
            if field not in params:
                return False, f'{field} is required for subscriptions'

        # Валідація username
        username = params.get('username')
        if not username or not isinstance(username, str):
            return False, 'Valid username is required'

        # Видаляємо @ якщо є
        username = username.lstrip('@')
        if not re.match(r'^[a-zA-Z0-9_]{1,32}$', username):
            return False, 'Invalid username format'

        # Валідація min/max
        try:
            min_val = int(params.get('min'))
            max_val = int(params.get('max'))

            if min_val < 0:
                return False, 'Minimum cannot be negative'
            if max_val < min_val:
                return False, 'Maximum must be greater than minimum'
            if min_val < service.min:
                return False, f'Minimum must be at least {service.min}'
            if max_val > service.max:
                return False, f'Maximum cannot exceed {service.max}'
        except:
            return False, 'Min and max must be valid integers'

        # Опціональні параметри
        if 'posts' in params:
            posts = params.get('posts')
            try:
                posts = int(posts)
                if posts < 0 or posts > 1000:
                    return False, 'Posts must be between 0 and 1000'
            except:
                return False, 'Posts must be a valid integer'

        if 'delay' in params:
            delay = params.get('delay')
            try:
                delay = int(delay)
                if delay < 0 or delay > 3600:
                    return False, 'Delay must be between 0 and 3600 seconds'
            except:
                return False, 'Delay must be a valid integer in seconds'

    else:
        # Невідомий тип - просто перевіряємо quantity якщо є
        if 'quantity' in params:
            quantity = params.get('quantity')
            if not validate_quantity(quantity, service.min, service.max):
                return False, f'Quantity must be between {service.min} and {service.max}'

    return True, None


def validate_order_link_for_service(service: Service, link: str) -> Tuple[bool, Optional[str]]:
    """
    Валідація посилання для конкретного сервісу та категорії

    Args:
        service: Сервіс
        link: Посилання

    Returns:
        (is_valid, error_message)
    """
    if not link:
        return False, 'Link is required'

    # Базова валідація URL
    if not validate_url(link):
        return False, 'Invalid URL format'

    # Валідація відповідно до категорії
    category = service.category.key

    validators = {
        'instagram': validate_instagram_order_link,
        'telegram': validate_telegram_order_link,
        'youtube': validate_youtube_order_link,
        'tiktok': validate_tiktok_order_link,
        'twitter': validate_twitter_order_link,
        'facebook': validate_facebook_order_link,
    }

    validator = validators.get(category)
    if validator:
        return validator(link, service.name.lower())

    # Для інших категорій просто перевіряємо базовий URL
    return True, None


def validate_instagram_order_link(link: str, service_name: str) -> Tuple[bool, Optional[str]]:
    """Валідація Instagram посилання"""
    # Визначаємо тип контенту за назвою сервісу
    if 'profile' in service_name or 'follower' in service_name:
        pattern = r'^https?://(www\.)?instagram\.com/[\w\-\.]+/?$'
        error = 'Please provide a valid Instagram profile link'
    elif 'reel' in service_name:
        pattern = r'^https?://(www\.)?instagram\.com/reel/[\w\-]+/?$'
        error = 'Please provide a valid Instagram Reel link'
    elif 'story' in service_name or 'stories' in service_name:
        pattern = r'^https?://(www\.)?instagram\.com/stories/[\w\-\.]+/\d+/?$'
        error = 'Please provide a valid Instagram Story link'
    elif 'igtv' in service_name or 'tv' in service_name:
        pattern = r'^https?://(www\.)?instagram\.com/tv/[\w\-]+/?$'
        error = 'Please provide a valid Instagram IGTV link'
    else:  # post, likes, comments, etc
        pattern = r'^https?://(www\.)?instagram\.com/(p|reel|tv)/[\w\-]+/?$'
        error = 'Please provide a valid Instagram post, reel or IGTV link'

    if not re.match(pattern, link):
        return False, error

    return True, None


def validate_telegram_order_link(link: str, service_name: str) -> Tuple[bool, Optional[str]]:
    """Валідація Telegram посилання"""
    # Для постів
    if 'post' in service_name or 'view' in service_name or 'reaction' in service_name:
        pattern = r'^https?://(www\.)?(t\.me|telegram\.me)/[\w\-]+/\d+/?$'
        error = 'Please provide a valid Telegram post link (e.g., https://t.me/channel/123)'
    # Для каналів/груп
    else:
        pattern = r'^https?://(www\.)?(t\.me|telegram\.me)/(joinchat/)?[\w\-]+/?$'
        error = 'Please provide a valid Telegram channel or group link'

    if not re.match(pattern, link):
        return False, error

    return True, None


def validate_youtube_order_link(link: str, service_name: str) -> Tuple[bool, Optional[str]]:
    """Валідація YouTube посилання"""
    if 'channel' in service_name or 'subscriber' in service_name:
        patterns = [
            r'^https?://(www\.)?youtube\.com/channel/[\w\-]+/?$',
            r'^https?://(www\.)?youtube\.com/c/[\w\-]+/?$',
            r'^https?://(www\.)?youtube\.com/@[\w\-\.]+/?$',
        ]
        error = 'Please provide a valid YouTube channel link'
    elif 'shorts' in service_name:
        patterns = [r'^https?://(www\.)?youtube\.com/shorts/[\w\-]+']
        error = 'Please provide a valid YouTube Shorts link'
    else:  # video views, likes, etc
        patterns = [
            r'^https?://(www\.)?(youtube\.com|youtu\.be)/watch\?v=[\w\-]+',
            r'^https?://(www\.)?youtu\.be/[\w\-]+',
        ]
        error = 'Please provide a valid YouTube video link'

    for pattern in patterns:
        if re.match(pattern, link):
            return True, None

    return False, error


def validate_tiktok_order_link(link: str, service_name: str) -> Tuple[bool, Optional[str]]:
    """Валідація TikTok посилання"""
    if 'profile' in service_name or 'follower' in service_name:
        pattern = r'^https?://(www\.)?tiktok\.com/@[\w\-\.]+/?$'
        error = 'Please provide a valid TikTok profile link'

        if not re.match(pattern, link):
            return False, error
        return True, None

    else:  # video views, likes, etc
        patterns = [
            r'^https?://(www\.)?tiktok\.com/@[\w\-\.]+/video/\d+',
            r'^https?://(www\.)?vm\.tiktok\.com/[\w\-]+/?$',
        ]
        error = 'Please provide a valid TikTok video link'

        for pattern in patterns:
            if re.match(pattern, link):
                return True, None

        return False, error


def validate_twitter_order_link(link: str, service_name: str) -> Tuple[bool, Optional[str]]:
    """Валідація Twitter/X посилання"""
    if 'profile' in service_name or 'follower' in service_name:
        pattern = r'^https?://(www\.)?(twitter\.com|x\.com)/[\w\-]+/?$'
        error = 'Please provide a valid Twitter/X profile link'
    else:  # tweet likes, retweets, etc
        pattern = r'^https?://(www\.)?(twitter\.com|x\.com)/[\w\-]+/status/\d+'
        error = 'Please provide a valid tweet link'

    if not re.match(pattern, link):
        return False, error

    return True, None


def validate_facebook_order_link(link: str, service_name: str) -> Tuple[bool, Optional[str]]:
    """Валідація Facebook посилання"""
    if 'page' in service_name or 'profile' in service_name:
        patterns = [
            r'^https?://(www\.)?facebook\.com/[\w\-\.]+/?$',
            r'^https?://(www\.)?fb\.com/[\w\-\.]+/?$',
        ]
        error = 'Please provide a valid Facebook page or profile link'

        for pattern in patterns:
            if re.match(pattern, link):
                return True, None
        return False, error

    elif 'video' in service_name:
        pattern = r'^https?://(www\.)?facebook\.com/[\w\-\.]+/videos/\d+'
        error = 'Please provide a valid Facebook video link'

        if re.match(pattern, link):
            return True, None
        return False, error

    else:  # posts
        patterns = [
            r'^https?://(www\.)?facebook\.com/[\w\-\.]+/posts/\d+',
            r'^https?://(www\.)?facebook\.com/[\w\-\.]+/?$',  # fallback для профілів
            r'^https?://(www\.)?fb\.com/[\w\-\.]+/?$',
        ]
        error = 'Please provide a valid Facebook post link'

        for pattern in patterns:
            if re.match(pattern, link):
                return True, None
        return False, error


def validate_order_status_transition(current_status: str, new_status: str) -> bool:
    """
    Перевірка чи дозволений перехід між статусами

    Args:
        current_status: Поточний статус
        new_status: Новий статус

    Returns:
        True якщо перехід дозволений
    """
    # Дозволені переходи
    allowed_transitions = {
        OrderStatus.PENDING: [
            OrderStatus.PROCESSING,
            OrderStatus.CANCELLED,
            OrderStatus.FAILED
        ],
        OrderStatus.PROCESSING: [
            OrderStatus.IN_PROGRESS,
            OrderStatus.COMPLETED,
            OrderStatus.PARTIAL,
            OrderStatus.CANCELLED,
            OrderStatus.FAILED
        ],
        OrderStatus.IN_PROGRESS: [
            OrderStatus.COMPLETED,
            OrderStatus.PARTIAL,
            OrderStatus.CANCELLED,
            OrderStatus.FAILED
        ],
        OrderStatus.PARTIAL: [
            OrderStatus.COMPLETED,
            OrderStatus.CANCELLED,
            OrderStatus.FAILED
        ],
        # Фінальні статуси - немає переходів
        OrderStatus.COMPLETED: [],
        OrderStatus.CANCELLED: [],
        OrderStatus.FAILED: []
    }

    return new_status in allowed_transitions.get(current_status, [])