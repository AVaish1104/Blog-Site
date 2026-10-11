"""
Adapter boundary for an external newsletter platform.

The database is always the source of truth. A provider is notified when a
subscriber confirms or unsubscribes so it can mirror the list. To integrate a
real service (Buttondown, Mailchimp, …) implement these two methods in a new
class and point NEWSLETTER_PROVIDER at it. Raise ProviderError on failure.
"""

from django.conf import settings
from django.utils.module_loading import import_string


class ProviderError(Exception):
    pass


class LocalProvider:
    """Keeps the list in this site's database only (export it as CSV from the studio)."""

    name = "local"

    def subscriber_confirmed(self, subscriber):
        return None

    def subscriber_unsubscribed(self, subscriber):
        return None


def get_provider():
    return import_string(settings.NEWSLETTER_PROVIDER)()
