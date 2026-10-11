"""
Database-backed fixed-window rate limiting.

Counters live in the database so limits hold across processes and restarts
without needing Redis or memcached.
"""

import hashlib
from datetime import UTC, datetime, timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import RateLimitCounter
from .net import ip_hash


def hit(scope, identity, limit, period_seconds):
    """Record one attempt. Returns True if the caller is now over the limit."""
    now = timezone.now()
    window = int(now.timestamp()) // period_seconds * period_seconds
    window_start = datetime.fromtimestamp(window, tz=UTC)
    key = f"{scope}:{hashlib.sha256(identity.encode()).hexdigest()[:40]}"

    with transaction.atomic():
        counter, created = RateLimitCounter.objects.get_or_create(
            key=key, window_start=window_start
        )
        RateLimitCounter.objects.filter(pk=counter.pk).update(count=F("count") + 1)
    counter.refresh_from_db(fields=["count"])

    if created:
        RateLimitCounter.objects.filter(window_start__lt=now - timedelta(days=2)).delete()
    return counter.count > limit


def hit_for_request(request, scope, limit, period_seconds):
    return hit(scope, ip_hash(request), limit, period_seconds)
