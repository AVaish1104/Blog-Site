from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.blog.models import Author, Post
from apps.comments.models import Comment
from apps.core.ratelimit import hit
from apps.images.models import Image

pytestmark = pytest.mark.django_db


def test_seed_demo_is_idempotent_and_clearable(django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        call_command("seed_demo", stdout=StringIO())
    assert Post.objects.filter(is_demo=True).count() == 14
    assert Post.objects.live().count() == 12
    assert Post.objects.scheduled().count() == 1
    assert Post.objects.drafts().count() == 1
    assert Comment.objects.count() == 2

    out = StringIO()
    call_command("seed_demo", stdout=out)
    assert "already exists" in out.getvalue()
    assert Post.objects.count() == 14

    call_command("seed_demo", "--clear", stdout=StringIO())
    assert not Post.objects.exists()
    assert not Author.objects.filter(is_demo=True).exists()
    assert not Image.objects.filter(is_demo=True).exists()


def test_clear_keeps_user_content(make_post, django_capture_on_commit_callbacks):
    mine = make_post("My own post")
    call_command("seed_demo", stdout=StringIO())
    call_command("seed_demo", "--clear", stdout=StringIO())
    assert list(Post.objects.all()) == [mine]


def test_create_editor(monkeypatch):
    monkeypatch.setenv("EDITOR_PASSWORD", "a-long-unique-password-42")
    call_command("create_editor", "writer", "--name", "Wren Writer", stdout=StringIO())
    user = get_user_model().objects.get(username="writer")
    assert user.can_manage_publication
    assert user.check_password("a-long-unique-password-42")
    assert Author.objects.get(user=user).name == "Wren Writer"


def test_create_editor_rejects_weak_password(monkeypatch):
    monkeypatch.setenv("EDITOR_PASSWORD", "123")
    with pytest.raises(CommandError):
        call_command("create_editor", "weak", stdout=StringIO())


def test_rate_limiter_counts_per_identity():
    assert not any(hit("scope", "a", 3, 60) for _ in range(3))
    assert hit("scope", "a", 3, 60)
    assert not hit("scope", "b", 3, 60)
    assert not hit("other", "a", 3, 60)


def test_rebuild_search_index_command(make_post):
    make_post("Indexed")
    out = StringIO()
    call_command("rebuild_search_index", stdout=out)
    assert "Indexed 1 posts" in out.getvalue()


def test_deploy_checks_flag_missing_email(settings):
    from apps.core.checks import production_configuration

    settings.EMAIL_DELIVERY = "console"
    ids = [w.id for w in production_configuration(None)]
    assert "core.W001" in ids
