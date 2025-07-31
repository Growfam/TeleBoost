# backend/services/validators.py
"""
TeleBoost Service Validators
Validation functions for service orders
"""
import re
import logging
from typing import Dict, Any, Tuple, Optional, List
from urllib.parse import urlparse

from backend.services.models import Service
from backend.utils.constants import SERVICE_TYPE
from backend.utils.validators import validate_url, validate_quantity

logger = logging.getLogger(__name__)


def validate_service_order(service_id: int, order_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate complete service order

    Args:
        service_id: Service ID
        order_data: Order data including link, quantity, etc.

    Returns:
        (is_valid, error_message)
    """
    try:
        # Get service
        service = Service.get_by_id(service_id)

        if not service:
            return False, "Service not found"

        if not service.is_active:
            return False, "Service is not active"

        # Validate link
        if 'link' not in order_data:
            return False, "Link is required"

        is_valid, error = validate_service_link(service, order_data['link'])
        if not is_valid:
            return False, error

        # Validate parameters based on service type
        is_valid, error = validate_service_parameters(service, order_data)
        if not is_valid:
            return False, error

        # Check service limits
        is_valid, error = check_service_limits(service, order_data)
        if not is_valid:
            return False, error

        return True, None

    except Exception as e:
        logger.error(f"Error validating service order: {e}")
        return False, "Validation error"


def validate_service_link(service: Service, link: str) -> Tuple[bool, Optional[str]]:
    """
    Validate link for specific service

    Args:
        service: Service instance
        link: URL to validate

    Returns:
        (is_valid, error_message)
    """
    if not link:
        return False, "Link is required"

    # Basic URL validation
    if not validate_url(link):
        return False, "Invalid URL format"

    # Category-specific validation
    category = service.category.key

    if category == 'instagram':
        return validate_instagram_link(link)
    elif category == 'telegram':
        return validate_telegram_link(link)
    elif category == 'youtube':
        return validate_youtube_link(link)
    elif category == 'tiktok':
        return validate_tiktok_link(link)
    elif category == 'twitter':
        return validate_twitter_link(link)
    elif category == 'facebook':
        return validate_facebook_link(link)

    # Generic validation for other categories
    return True, None


def validate_instagram_link(link: str) -> Tuple[bool, Optional[str]]:
    """Validate Instagram link"""
    patterns = [
        r'^https?://(www\.)?instagram\.com/[\w\-\.]+/?$',  # Profile
        r'^https?://(www\.)?instagram\.com/p/[\w\-]+/?$',  # Post
        r'^https?://(www\.)?instagram\.com/reel/[\w\-]+/?$',  # Reel
        r'^https?://(www\.)?instagram\.com/tv/[\w\-]+/?$',  # IGTV
        r'^https?://(www\.)?instagram\.com/stories/[\w\-\.]+/\d+/?$',  # Story
    ]

    for pattern in patterns:
        if re.match(pattern, link):
            return True, None

    return False, "Invalid Instagram link. Supported: profiles, posts, reels, IGTV, stories"


def validate_telegram_link(link: str) -> Tuple[bool, Optional[str]]:
    """Validate Telegram link"""
    patterns = [
        r'^https?://(www\.)?(t\.me|telegram\.me)/[\w\-]+/?$',  # Channel/Group
        r'^https?://(www\.)?(t\.me|telegram\.me)/[\w\-]+/\d+/?$',  # Post
        r'^https?://(www\.)?(t\.me|telegram\.me)/joinchat/[\w\-]+/?$',  # Join link
    ]

    for pattern in patterns:
        if re.match(pattern, link):
            return True, None

    return False, "Invalid Telegram link. Supported: channels, groups, posts"


def validate_youtube_link(link: str) -> Tuple[bool, Optional[str]]:
    """Validate YouTube link"""
    patterns = [
        r'^https?://(www\.)?(youtube\.com|youtu\.be)/watch\?v=[\w\-]+',  # Video
        r'^https?://(www\.)?youtu\.be/[\w\-]+',  # Short video link
        r'^https?://(www\.)?youtube\.com/channel/[\w\-]+/?$',  # Channel
        r'^https?://(www\.)?youtube\.com/c/[\w\-]+/?$',  # Custom channel
        r'^https?://(www\.)?youtube\.com/@[\w\-\.]+/?$',  # Handle
        r'^https?://(www\.)?youtube\.com/shorts/[\w\-]+',  # Shorts
    ]

    for pattern in patterns:
        if re.match(pattern, link):
            return True, None

    return False, "Invalid YouTube link. Supported: videos, channels, shorts"


def validate_tiktok_link(link: str) -> Tuple[bool, Optional[str]]:
    """Validate TikTok link"""
    patterns = [
        r'^https?://(www\.)?tiktok\.com/@[\w\-\.]+/?$',  # Profile
        r'^https?://(www\.)?tiktok\.com/@[\w\-\.]+/video/\d+',  # Video
        r'^https?://(www\.)?vm\.tiktok\.com/[\w\-]+/?$',  # Short link
    ]

    for pattern in patterns:
        if re.match(pattern, link):
            return True, None

    return False, "Invalid TikTok link. Supported: profiles, videos"


def validate_twitter_link(link: str) -> Tuple[bool, Optional[str]]:
    """Validate Twitter/X link"""
    patterns = [
        r'^https?://(www\.)?(twitter\.com|x\.com)/[\w\-]+/?$',  # Profile
        r'^https?://(www\.)?(twitter\.com|x\.com)/[\w\-]+/status/\d+',  # Tweet
    ]

    for pattern in patterns:
        if re.match(pattern, link):
            return True, None

    return False, "Invalid Twitter/X link. Supported: profiles, tweets"


def validate_facebook_link(link: str) -> Tuple[bool, Optional[str]]:
    """Validate Facebook link"""
    patterns = [
        r'^https?://(www\.)?facebook\.com/[\w\-\.]+/?$',  # Profile/Page
        r'^https?://(www\.)?facebook\.com/[\w\-\.]+/posts/\d+',  # Post
        r'^https?://(www\.)?facebook\.com/[\w\-\.]+/videos/\d+',  # Video
        r'^https?://(www\.)?fb\.com/[\w\-\.]+/?$',  # Short link
    ]

    for pattern in patterns:
        if re.match(pattern, link):
            return True, None

    return False, "Invalid Facebook link. Supported: profiles, pages, posts, videos"


def validate_service_parameters(service: Service, order_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate service-specific parameters

    Args:
        service: Service instance
        order_data: Order data

    Returns:
        (is_valid, error_message)
    """
    service_type = service.type

    # Default type - requires quantity
    if service_type == SERVICE_TYPE.DEFAULT:
        if 'quantity' not in order_data:
            return False, "Quantity is required"

        quantity = order_data['quantity']
        return service.validate_quantity(quantity)

    # Drip-feed type
    elif service_type == SERVICE_TYPE.DRIP_FEED:
        required = ['quantity', 'runs', 'interval']
        for field in required:
            if field not in order_data:
                return False, f"{field} is required for drip-feed"

        # Validate quantity
        is_valid, error = service.validate_quantity(order_data['quantity'])
        if not is_valid:
            return False, error

        # Validate runs
        runs = order_data['runs']
        if not isinstance(runs, int) or runs < 1 or runs > 100:
            return False, "Runs must be between 1 and 100"

        # Validate interval (minutes)
        interval = order_data['interval']
        if not isinstance(interval, int) or interval < 1 or interval > 1440:
            return False, "Interval must be between 1 and 1440 minutes (24 hours)"

        # Check total quantity
        total_quantity = order_data['quantity'] * runs
        if total_quantity > service.max:
            return False, f"Total quantity ({total_quantity}) exceeds maximum ({service.max})"

        return True, None

    # Custom comments type
    elif service_type == SERVICE_TYPE.CUSTOM_COMMENTS:
        if 'comments' not in order_data:
            return False, "Comments are required"

        comments = order_data['comments']
        if isinstance(comments, str):
            # Split by newlines
            comments_list = [c.strip() for c in comments.split('\n') if c.strip()]
        elif isinstance(comments, list):
            comments_list = [str(c).strip() for c in comments if str(c).strip()]
        else:
            return False, "Comments must be a string or list"

        if not comments_list:
            return False, "At least one comment is required"

        # Validate comment count as quantity
        comment_count = len(comments_list)
        return service.validate_quantity(comment_count)

    # Poll type
    elif service_type == SERVICE_TYPE.POLL:
        required = ['quantity', 'answer_number']
        for field in required:
            if field not in order_data:
                return False, f"{field} is required for polls"

        # Validate quantity
        is_valid, error = service.validate_quantity(order_data['quantity'])
        if not is_valid:
            return False, error

        # Validate answer number
        answer = order_data['answer_number']
        try:
            answer_num = int(answer)
            if answer_num < 1 or answer_num > 10:
                return False, "Answer number must be between 1 and 10"
        except:
            return False, "Answer number must be an integer"

        return True, None

    # Subscriptions type
    elif service_type == SERVICE_TYPE.SUBSCRIPTIONS:
        required = ['username', 'min', 'max']
        for field in required:
            if field not in order_data:
                return False, f"{field} is required for subscriptions"

        # Validate username
        username = order_data['username']
        if not username or not isinstance(username, str):
            return False, "Valid username is required"

        # Validate min/max
        try:
            min_val = int(order_data['min'])
            max_val = int(order_data['max'])

            if min_val < 0:
                return False, "Minimum cannot be negative"
            if max_val < min_val:
                return False, "Maximum must be greater than minimum"
            if max_val > service.max:
                return False, f"Maximum exceeds service limit ({service.max})"
        except:
            return False, "Min and max must be integers"

        # Optional parameters
        if 'posts' in order_data:
            posts = order_data['posts']
            if not isinstance(posts, int) or posts < 0:
                return False, "Posts must be a non-negative integer"

        if 'delay' in order_data:
            delay = order_data['delay']
            if not isinstance(delay, int) or delay < 0 or delay > 3600:
                return False, "Delay must be between 0 and 3600 seconds"

        return True, None

    # Unknown type - just validate quantity
    else:
        if 'quantity' in order_data:
            return service.validate_quantity(order_data['quantity'])

        return True, None


def check_service_limits(service: Service, order_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Check if order respects service limits

    Args:
        service: Service instance
        order_data: Order data

    Returns:
        (is_valid, error_message)
    """
    # Basic quantity limits are checked in validate_quantity
    # This function can be extended for additional limit checks

    # Example: Check if link is not already being processed
    # This would require checking active orders in the database

    # Example: Rate limiting per user
    # This would require checking user's recent orders

    # For now, just return True
    return True, None


def get_required_fields(service: Service) -> List[str]:
    """
    Get required fields for service order

    Args:
        service: Service instance

    Returns:
        List of required field names
    """
    # All services require link
    required = ['link']

    service_type = service.type

    if service_type == SERVICE_TYPE.DEFAULT:
        required.append('quantity')

    elif service_type == SERVICE_TYPE.DRIP_FEED:
        required.extend(['quantity', 'runs', 'interval'])

    elif service_type == SERVICE_TYPE.CUSTOM_COMMENTS:
        required.append('comments')

    elif service_type == SERVICE_TYPE.POLL:
        required.extend(['quantity', 'answer_number'])

    elif service_type == SERVICE_TYPE.SUBSCRIPTIONS:
        required.extend(['username', 'min', 'max'])

    else:
        # Default to quantity
        required.append('quantity')

    return required