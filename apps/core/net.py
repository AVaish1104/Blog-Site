"""Helpers for identifying clients without storing raw IP addresses."""

import hashlib
import hmac

from django.conf import settings


def client_ip(request):
    """Best-effort client IP. Only trusts X-Forwarded-For when explicitly configured."""
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "unknown"


def ip_hash(request):
    """Keyed, non-reversible fingerprint of the client IP (for abuse handling only)."""
    return hmac.new(
        settings.SECRET_KEY.encode(), client_ip(request).encode(), hashlib.sha256
    ).hexdigest()
