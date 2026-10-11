"""
Newsletter subscription workflow (double opt-in).

Confirmation and unsubscribe links are signed with SECRET_KEY, so no tokens are
stored and links can't be forged. Delivery honestly reports what happened: with
no email provider configured the message is written to the server log, and the
caller is told it was *not* delivered.
"""

import logging
from dataclasses import dataclass
from enum import Enum

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import Subscriber
from .providers import ProviderError, get_provider

logger = logging.getLogger(__name__)

CONSENT_TEXT = (
    "I agree to receive occasional emails from {site} with new writing. "
    "I can unsubscribe at any time using the link in every email."
)
CONFIRM_MAX_AGE = 60 * 60 * 24 * 7
_CONFIRM_SALT = "newsletter.confirm"
_UNSUBSCRIBE_SALT = "newsletter.unsubscribe"


class Delivery(Enum):
    SENT = "sent"  # handed to a real email provider
    LOGGED = "logged"  # no provider configured: printed to the server log only
    FAILED = "failed"  # provider raised an error
    SKIPPED = "skipped"  # nothing needed sending


@dataclass
class SubscribeResult:
    subscriber: Subscriber
    delivery: Delivery


def consent_text():
    return CONSENT_TEXT.format(site=settings.SITE_NAME)


def normalize_email(email):
    return (email or "").strip().lower()


def confirm_token(subscriber):
    return signing.dumps({"id": subscriber.pk, "email": subscriber.email}, salt=_CONFIRM_SALT)


def unsubscribe_token(subscriber):
    return signing.dumps({"id": subscriber.pk, "email": subscriber.email}, salt=_UNSUBSCRIBE_SALT)


def _load(token, salt, max_age=None):
    try:
        data = signing.loads(token, salt=salt, max_age=max_age)
    except signing.SignatureExpired:
        return None, "expired"
    except signing.BadSignature:
        return None, "invalid"
    subscriber = Subscriber.objects.filter(pk=data.get("id"), email=data.get("email")).first()
    return subscriber, None if subscriber else "invalid"


def subscribe(email, *, source="", ip_hash=""):
    email = normalize_email(email)
    with transaction.atomic():
        subscriber, created = Subscriber.objects.select_for_update().get_or_create(
            email=email,
            defaults={
                "consent_text": consent_text(),
                "consented_at": timezone.now(),
                "source": source[:50],
                "ip_hash": ip_hash,
            },
        )
        if not created and subscriber.status == Subscriber.Status.ACTIVE:
            # Already subscribed: change nothing, send nothing.
            return SubscribeResult(subscriber, Delivery.SKIPPED)
        if not created:
            subscriber.status = Subscriber.Status.PENDING
            subscriber.consent_text = consent_text()
            subscriber.consented_at = timezone.now()
            subscriber.unsubscribed_at = None
            subscriber.ip_hash = ip_hash
            subscriber.save()
    return SubscribeResult(subscriber, send_confirmation(subscriber))


def send_confirmation(subscriber):
    confirm_url = settings.SITE_URL + reverse(
        "newsletter:confirm", args=[confirm_token(subscriber)]
    )
    context = {"site_name": settings.SITE_NAME, "confirm_url": confirm_url}
    try:
        send_mail(
            subject=f"Confirm your subscription to {settings.SITE_NAME}",
            message=render_to_string("newsletter/email/confirm.txt", context),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[subscriber.email],
        )
    except Exception:  # noqa: BLE001 — any transport failure is reported, never hidden
        logger.exception("Newsletter confirmation email failed for subscriber %s", subscriber.pk)
        return Delivery.FAILED
    return Delivery.SENT if settings.EMAIL_DELIVERY == "smtp" else Delivery.LOGGED


def confirm(token):
    subscriber, error = _load(token, _CONFIRM_SALT, max_age=CONFIRM_MAX_AGE)
    if error:
        return None, error
    if subscriber.status != Subscriber.Status.ACTIVE:
        subscriber.status = Subscriber.Status.ACTIVE
        subscriber.confirmed_at = timezone.now()
        subscriber.save(update_fields=["status", "confirmed_at"])
        _notify_provider("subscriber_confirmed", subscriber)
    return subscriber, None


def find_by_unsubscribe_token(token):
    return _load(token, _UNSUBSCRIBE_SALT)


def unsubscribe(token):
    subscriber, error = _load(token, _UNSUBSCRIBE_SALT)
    if error:
        return None, error
    if subscriber.status != Subscriber.Status.UNSUBSCRIBED:
        subscriber.status = Subscriber.Status.UNSUBSCRIBED
        subscriber.unsubscribed_at = timezone.now()
        subscriber.save(update_fields=["status", "unsubscribed_at"])
        _notify_provider("subscriber_unsubscribed", subscriber)
    return subscriber, None


def _notify_provider(method, subscriber):
    try:
        getattr(get_provider(), method)(subscriber)
    except ProviderError:
        logger.exception("Newsletter provider %s failed for subscriber %s", method, subscriber.pk)
