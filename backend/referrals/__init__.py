# backend/referrals/__init__.py
"""
TeleBoost Referrals Package
Дворівнева реферальна система
"""

from backend.referrals.models import Referral, ReferralStats
from backend.referrals.services import (
    process_referral_bonus,
    get_user_referrals,
    get_referral_stats,
    calculate_referral_bonus,
    process_deposit_referral_bonuses,
    get_referral_tree,
    get_referral_earnings,
)

__all__ = [
    # Models
    'Referral',
    'ReferralStats',

    # Services
    'process_referral_bonus',
    'get_user_referrals',
    'get_referral_stats',
    'calculate_referral_bonus',
    'process_deposit_referral_bonuses',
    'get_referral_tree',
    'get_referral_earnings',
]