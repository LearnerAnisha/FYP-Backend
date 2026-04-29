# payment/quota.py
from django.utils.timezone import now
from rest_framework.response import Response
from .models import DailyUsage, DAILY_LIMITS


def check_and_increment_quota(user, feature):
    """
    Call this at the start of every protected feature view.
    Returns None if allowed, or a DRF Response(403) if the free limit is hit.
    PRO users are always allowed (returns None immediately).
    """
    # PRO users: skip all checks
    try:
        if user.subscription.is_pro:
            return None
    except Exception:
        pass  # no subscription row = FREE

    limit = DAILY_LIMITS.get(feature)
    if limit is None:
        return None  # unknown feature — allow by default

    usage, _ = DailyUsage.objects.get_or_create(
        user=user, feature=feature, date=now().date()
    )

    if usage.count >= limit:
        return Response(
            {
                "error": f"Daily limit of {limit} reached for {feature.replace('_', ' ')}.",
                "limit": limit,
                "used": usage.count,
                "upgrade_url": "/pricing",
            },
            status=403,
        )

    usage.count += 1
    usage.save(update_fields=["count"])
    return None
