"""Helpers for identifying clients without storing raw IP addresses."""

import hashlib
import hmac

from django.conf import settings


def client_ip(request):
    """
    Best-effort client IP. X-Forwarded-For is only used when explicitly trusted, and
    then read from the right: each proxy appends the address it saw, so the entry
    TRUSTED_PROXY_COUNT places from the end is one the client cannot forge.
    """
    remote = request.META.get("REMOTE_ADDR", "") or "unknown"
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        parts = [p.strip() for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")]
        parts = [p for p in parts if p]
        count = max(1, getattr(settings, "TRUSTED_PROXY_COUNT", 1))
        if len(parts) >= count:
            return parts[-count]
    return remote


def ip_hash(request):
    """Keyed, non-reversible fingerprint of the client IP (for abuse handling only)."""
    return hmac.new(
        settings.SECRET_KEY.encode(), client_ip(request).encode(), hashlib.sha256
    ).hexdigest()
