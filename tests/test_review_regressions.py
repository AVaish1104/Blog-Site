"""Regression tests for defects found in the independent code review."""

from io import StringIO

import pytest
from django.core import mail
from django.core.management import call_command
from django.test import RequestFactory, override_settings
from django.urls import reverse

from apps.blog.models import Author, Category, Post, SlugRedirect, Tag
from apps.blog.services import save_post, unique_slug
from apps.core.net import client_ip
from apps.newsletter import services
from apps.newsletter.models import Subscriber
from apps.search.services import highlight_snippet, search_posts

pytestmark = pytest.mark.django_db


@override_settings(TRUST_X_FORWARDED_FOR=True, TRUSTED_PROXY_COUNT=1)
def test_client_cannot_spoof_its_ip_through_x_forwarded_for():
    request = RequestFactory().get(
        "/", HTTP_X_FORWARDED_FOR="1.2.3.4, 203.0.113.9", REMOTE_ADDR="10.0.0.1"
    )
    assert client_ip(request) == "203.0.113.9"


@override_settings(TRUST_X_FORWARDED_FOR=False)
def test_forwarded_header_ignored_unless_trusted():
    request = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="1.2.3.4", REMOTE_ADDR="10.0.0.1")
    assert client_ip(request) == "10.0.0.1"


def _subscribe(client, email="a@example.com"):
    client.post(reverse("newsletter:subscribe"), {"email": email, "consent": "on", "website": ""})
    return Subscriber.objects.get(email=email)


def test_old_confirmation_link_does_not_resubscribe(client):
    sub = _subscribe(client)
    token = services.confirm_token(sub)
    services.confirm(token)
    services.unsubscribe(services.unsubscribe_token(sub))
    subscriber, error = services.confirm(token)
    sub.refresh_from_db()
    assert error and sub.status == Subscriber.Status.UNSUBSCRIBED


def test_newer_signup_invalidates_older_confirmation_link(client, monkeypatch):
    from datetime import timedelta

    from django.utils import timezone

    sub = _subscribe(client)
    old_token = services.confirm_token(sub)
    later = timezone.now() + timedelta(seconds=5)
    monkeypatch.setattr(services.timezone, "now", lambda: later)
    _subscribe(client)
    assert services.confirm(old_token)[1] == "invalid"
    sub.refresh_from_db()
    assert services.confirm(services.confirm_token(sub))[1] is None


def test_confirmation_email_contains_unsubscribe_link(client):
    _subscribe(client)
    assert "/newsletter/unsubscribe/" in mail.outbox[0].body


def test_csv_export_includes_unsubscribe_links(editor_client, client):
    sub = _subscribe(client)
    services.confirm(services.confirm_token(sub))
    body = editor_client.get(reverse("studio:subscriber_export")).content.decode()
    assert "unsubscribe_url" in body and "/newsletter/unsubscribe/" in body


def test_draft_does_not_steal_a_live_posts_redirect(make_post, client):
    live = make_post("Live", slug="old-name")
    live.slug = "new-name"
    save_post(live, previous_slug="old-name")
    make_post("Draft", slug="old-name", state="draft")
    assert SlugRedirect.objects.filter(old_slug="old-name", post=live).exists()
    assert client.get("/posts/old-name/").status_code == 301


def test_generated_slugs_avoid_addresses_that_still_redirect(make_post):
    live = make_post("Old name", slug="old-name")
    live.slug = "new-name"
    save_post(live, previous_slug="old-name")
    assert unique_slug("Old name") == "old-name-2"


def test_deleting_a_tag_or_topic_updates_the_search_index(
    make_post, django_capture_on_commit_callbacks
):
    category = Category.objects.create(name="Zymurgy", slug="zymurgy")
    make_post("Brewing notes", tags=["Quixotic"], category=category)
    assert search_posts("quixotic").results and search_posts("zymurgy").results
    with django_capture_on_commit_callbacks(execute=True):
        Tag.objects.get(name="Quixotic").delete()
        category.delete()
    assert search_posts("quixotic").results == []
    assert search_posts("zymurgy").results == []


@pytest.mark.parametrize("term", ["amp", "27", "lt"])
def test_snippet_highlighting_never_breaks_entities(term):
    html = highlight_snippet("Tom & Jerry's <b> 27 amp lt", [term])
    assert "&amp;" in html and "&lt;b&gt;" in html
    assert "&<mark>" not in html and "&#x<mark>" not in html


def test_feeds_and_sitemap_use_site_url_not_host(client, make_post, settings):
    settings.SITE_URL = "https://blog.example.com"
    settings.ALLOWED_HOSTS = ["evil.test", "testserver"]
    post = make_post("Canonical")
    feed = client.get("/feed/", HTTP_HOST="evil.test").content.decode()
    sitemap = client.get("/sitemap.xml", HTTP_HOST="evil.test").content.decode()
    assert f"https://blog.example.com{post.get_absolute_url()}" in feed
    assert f"https://blog.example.com{post.get_absolute_url()}" in sitemap
    assert "evil.test" not in feed + sitemap


def test_seed_demo_recovers_when_demo_author_remains():
    call_command("seed_demo", stdout=StringIO())
    Post.objects.filter(is_demo=True).delete()
    assert Author.objects.filter(is_demo=True).exists()
    call_command("seed_demo", stdout=StringIO())
    assert Post.objects.filter(is_demo=True).count() == 14


def test_non_editor_can_sign_out_from_forbidden_page(client, reader_user):
    client.force_login(reader_user)
    page = client.get(reverse("studio:dashboard"))
    assert page.status_code == 403
    assert "Sign out to switch account" in page.content.decode()
    client.post(reverse("accounts:logout"))
    assert client.get(reverse("studio:dashboard")).status_code == 302


def test_preview_errors_have_no_dead_field_links(editor_client, author):
    response = editor_client.post(
        reverse("studio:post_preview"), {"title": "", "author": author.pk, "status": "draft"}
    )
    html = response.content.decode()
    assert response.status_code == 400
    assert 'href="#id_title"' not in html
    assert "title" in html.lower()
