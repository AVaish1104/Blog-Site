import re

import pytest
from django.core import mail, signing
from django.urls import reverse

from apps.newsletter import services
from apps.newsletter.models import Subscriber
from apps.newsletter.services import Delivery

pytestmark = pytest.mark.django_db


def subscribe(client, email="Person@Example.com", consent="on", **extra):
    data = {"email": email, "website": "", "source": "test", **extra}
    if consent:
        data["consent"] = consent
    return client.post(reverse("newsletter:subscribe"), data)


def confirm_link_from(message):
    return re.search(r"http://testserver(/newsletter/confirm/[^\s]+/)", message.body).group(1)


def test_subscribe_records_pending_subscriber_with_consent(client):
    response = subscribe(client)
    assert response.status_code == 200
    sub = Subscriber.objects.get()
    assert sub.email == "person@example.com"
    assert sub.status == Subscriber.Status.PENDING
    assert "unsubscribe at any time" in sub.consent_text
    assert sub.consented_at is not None
    assert len(mail.outbox) == 1


def test_without_email_provider_the_page_says_nothing_was_sent(client, settings):
    settings.EMAIL_DELIVERY = "console"
    html = subscribe(client).content.decode()
    assert "no email was sent" in html
    assert "Check your inbox" not in html


def test_with_email_provider_the_page_says_check_inbox(client, settings):
    settings.EMAIL_DELIVERY = "smtp"
    html = subscribe(client).content.decode()
    assert "Check your inbox" in html


def test_failed_delivery_is_reported(client, settings):
    settings.EMAIL_BACKEND = "tests.test_newsletter.BrokenBackend"
    html = subscribe(client).content.decode()
    assert "couldn" in html and "send the confirmation email" in html
    assert Subscriber.objects.count() == 1


class BrokenBackend:
    def __init__(self, *args, **kwargs):
        pass

    def send_messages(self, messages):
        raise ConnectionError("SMTP down")


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"email": "nope"}, "valid email"),
        ({"consent": None}, "confirm you"),
        ({"email": ""}, "required"),
    ],
)
def test_validation(client, kwargs, error):
    response = subscribe(client, **kwargs)
    assert response.status_code == 400
    assert error in response.content.decode()
    assert not Subscriber.objects.exists()


def test_honeypot(client):
    assert subscribe(client, website="spam").status_code == 400
    assert not Subscriber.objects.exists()


def test_duplicate_active_subscriber_is_not_changed_or_emailed(client, settings):
    settings.EMAIL_DELIVERY = "smtp"
    subscribe(client)
    services.confirm(services.confirm_token(Subscriber.objects.get()))
    mail.outbox.clear()
    html = subscribe(client, email="PERSON@example.com").content.decode()
    assert Subscriber.objects.count() == 1
    assert Subscriber.objects.get().status == Subscriber.Status.ACTIVE
    assert mail.outbox == []
    assert "Check your inbox" in html  # same message as a new sign-up: no enumeration


def test_duplicate_pending_subscriber_gets_a_fresh_link(client):
    subscribe(client)
    subscribe(client)
    assert Subscriber.objects.count() == 1
    assert len(mail.outbox) == 2


def test_confirmation_link_activates(client):
    subscribe(client)
    response = client.get(confirm_link_from(mail.outbox[0]))
    assert response.status_code == 200
    assert "subscribed" in response.content.decode()
    assert Subscriber.objects.get().status == Subscriber.Status.ACTIVE


def test_invalid_and_expired_confirmation_links(client, monkeypatch):
    assert client.get(reverse("newsletter:confirm", args=["bogus"])).status_code == 400
    subscribe(client)
    sub = Subscriber.objects.get()
    token = services.confirm_token(sub)
    real_loads = signing.loads
    monkeypatch.setattr(
        services.signing,
        "loads",
        lambda *a, **k: (_ for _ in ()).throw(signing.SignatureExpired("old")),
    )
    response = client.get(reverse("newsletter:confirm", args=[token]))
    assert response.status_code == 400 and "expired" in response.content.decode()
    monkeypatch.setattr(services.signing, "loads", real_loads)
    sub.refresh_from_db()
    assert sub.status == Subscriber.Status.PENDING


def test_unsubscribe_requires_explicit_post(client):
    subscribe(client)
    sub = Subscriber.objects.get()
    services.confirm(services.confirm_token(sub))
    url = reverse("newsletter:unsubscribe", args=[services.unsubscribe_token(sub)])
    page = client.get(url)
    assert page.status_code == 200
    sub.refresh_from_db()
    assert sub.status == Subscriber.Status.ACTIVE  # link scanners can't unsubscribe people
    client.post(url)
    sub.refresh_from_db()
    assert sub.status == Subscriber.Status.UNSUBSCRIBED


def test_resubscribe_after_unsubscribe_needs_confirmation(client):
    subscribe(client)
    sub = Subscriber.objects.get()
    services.unsubscribe(services.unsubscribe_token(sub))
    subscribe(client)
    sub.refresh_from_db()
    assert sub.status == Subscriber.Status.PENDING


def test_tokens_cannot_be_swapped_between_purposes(client):
    subscribe(client)
    sub = Subscriber.objects.get()
    unsub_token = services.unsubscribe_token(sub)
    assert client.get(reverse("newsletter:confirm", args=[unsub_token])).status_code == 400


def test_rate_limit(client):
    for i in range(5):
        subscribe(client, email=f"p{i}@example.com")
    response = subscribe(client, email="p9@example.com")
    assert response.status_code == 400
    assert "Too many attempts" in response.content.decode()


def test_studio_export_csv_guards_formulas(editor_client):
    from django.utils import timezone

    Subscriber.objects.create(
        email="=cmd@example.com", status="active", consent_text="x", consented_at=timezone.now()
    )
    response = editor_client.get(reverse("studio:subscriber_export"))
    body = response.content.decode()
    assert response["Content-Type"].startswith("text/csv")
    assert "'=cmd@example.com" in body


def test_delivery_enum_values():
    assert {d.value for d in Delivery} == {"sent", "logged", "failed", "skipped"}
