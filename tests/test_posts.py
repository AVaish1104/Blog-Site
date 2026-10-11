from datetime import timedelta

import pytest
from django.utils import timezone

from apps.blog.models import Post, SlugRedirect, Tag
from apps.blog.services import (
    parse_tag_names,
    publish_now,
    related_posts,
    save_post,
    unique_slug,
    unpublish,
)

pytestmark = pytest.mark.django_db


def test_visibility_rules(make_post):
    live = make_post("Live")
    draft = make_post("Draft", state="draft")
    scheduled = make_post("Scheduled", state="scheduled")
    visible = set(Post.objects.live())
    assert visible == {live}
    assert live.state == "published"
    assert draft.state == "draft"
    assert scheduled.state == "scheduled"
    assert set(Post.objects.scheduled()) == {scheduled}
    assert set(Post.objects.drafts()) == {draft}


def test_scheduled_post_becomes_live_when_its_time_passes(make_post):
    post = make_post("Soon", state="scheduled", days_ago=1)
    assert not Post.objects.live().filter(pk=post.pk).exists()
    later = timezone.now() + timedelta(days=2)
    assert Post.objects.live(now=later).filter(pk=post.pk).exists()


def test_save_renders_body_and_reading_time(make_post):
    post = make_post("Rendered", body="## Part\n\n" + "word " * 500)
    assert "<h2>Part</h2>" in post.body_html
    assert post.word_count == 501
    assert post.reading_time == 3


def test_publishing_without_date_sets_now(author):
    post = save_post(
        Post(title="T", slug="t", body="b", author=author, status=Post.Status.PUBLISHED)
    )
    assert post.published_at is not None
    assert post.is_live


def test_publish_now_and_unpublish(make_post):
    post = make_post("Draft", state="draft")
    publish_now(post)
    assert post.is_live
    unpublish(post)
    post.refresh_from_db()
    assert post.state == "draft"


def test_publish_now_pulls_scheduled_post_forward(make_post):
    post = make_post("Later", state="scheduled", days_ago=5)
    publish_now(post)
    assert post.is_live


def test_slug_change_on_published_post_creates_redirect(make_post):
    post = make_post("Original", slug="original")
    post.slug = "renamed"
    save_post(post, previous_slug="original")
    assert SlugRedirect.objects.get(old_slug="original").post == post


def test_slug_change_on_never_published_draft_creates_no_redirect(make_post):
    post = make_post("Draft", slug="first", state="draft")
    post.slug = "second"
    save_post(post, previous_slug="first")
    assert not SlugRedirect.objects.exists()


def test_reusing_an_old_slug_removes_the_stale_redirect(make_post):
    post = make_post("A", slug="a")
    post.slug = "a2"
    save_post(post, previous_slug="a")
    make_post("New A", slug="a")
    assert not SlugRedirect.objects.filter(old_slug="a").exists()


def test_unique_slug_generation(make_post):
    make_post("Hello", slug="hello-world")
    assert unique_slug("Hello World") == "hello-world-2"
    assert unique_slug("!!!") == "untitled"


def test_tag_parsing_dedupes_case_insensitively():
    assert parse_tag_names(" Design, writing ,design,, Writing  ") == ["Design", "writing"]


def test_tags_are_reused_case_insensitively(make_post):
    make_post("One", tags=["Design"])
    make_post("Two", tags=["design", "Craft"])
    assert Tag.objects.count() == 2


def test_related_posts_prefer_shared_tags(make_post):
    base = make_post("Base", tags=["a", "b"])
    strong = make_post("Strong", tags=["a", "b"], days_ago=10)
    weak = make_post("Weak", tags=["a"], days_ago=2)
    make_post("Unrelated", tags=["z"], days_ago=1)
    make_post("Hidden", tags=["a", "b"], state="draft")
    related = related_posts(base)
    assert related[:2] == [strong, weak]
    assert all(p.is_live for p in related)
    assert base not in related
