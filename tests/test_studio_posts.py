from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import Post, SlugRedirect, Tag
from apps.images.models import Image

from .conftest import upload

pytestmark = pytest.mark.django_db


def form_data(author_obj, **overrides):
    data = {
        "title": "My new post",
        "slug": "",
        "excerpt": "Summary",
        "body": "Body **text**.",
        "author": author_obj.pk,
        "category": "",
        "tags": "Design, Writing",
        "status": "draft",
        "published_at": "",
        "allow_comments": "on",
        "seo_title": "",
        "seo_description": "",
    }
    data.update(overrides)
    return data


def test_create_draft_generates_slug_and_tags(editor_client, author, editor):
    response = editor_client.post(reverse("studio:post_create"), form_data(author))
    post = Post.objects.get()
    assert response.status_code == 302
    assert response["Location"] == reverse("studio:post_edit", args=[post.pk])
    assert post.slug == "my-new-post"
    assert post.state == "draft"
    assert post.created_by == editor
    assert sorted(t.name for t in post.tags.all()) == ["Design", "Writing"]
    follow = editor_client.get(response["Location"])
    assert (
        "saved as a draft" in follow.content.decode()
        or "created as a draft" in follow.content.decode()
    )


def test_publish_from_editor_makes_post_public(editor_client, author, client):
    editor_client.post(reverse("studio:post_create"), form_data(author, status="published"))
    post = Post.objects.get()
    assert post.is_live
    assert client.get(post.get_absolute_url()).status_code == 200


def test_schedule_with_future_date(editor_client, author):
    future = (timezone.localtime() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    editor_client.post(
        reverse("studio:post_create"), form_data(author, status="published", published_at=future)
    )
    assert Post.objects.get().state == "scheduled"


@pytest.mark.parametrize(
    "overrides, field, message",
    [
        ({"title": "   "}, "title", "title"),
        ({"author": ""}, "author", "choose an author"),
        ({"slug": "Not A Slug!"}, "slug", "lowercase"),
        ({"status": "published", "body": ""}, "body", "body text"),
        ({"status": "bogus"}, "status", "valid choice"),
        ({"tags": ",".join(f"t{i}" for i in range(13))}, "tags", "at most"),
        ({"published_at": "not-a-date"}, "published_at", "valid"),
    ],
)
def test_validation_errors(editor_client, author, overrides, field, message):
    response = editor_client.post(reverse("studio:post_create"), form_data(author, **overrides))
    assert response.status_code == 400
    errors = response.context["form"].errors
    assert field in errors
    assert message.lower() in " ".join(errors[field]).lower()
    assert not Post.objects.exists()
    assert "Please fix the following" in response.content.decode()


def test_duplicate_slug_is_rejected(editor_client, author, make_post):
    make_post("Existing", slug="taken")
    response = editor_client.post(reverse("studio:post_create"), form_data(author, slug="taken"))
    assert response.status_code == 400
    assert "already used by" in " ".join(response.context["form"].errors["slug"])


def test_edit_post_and_change_slug_keeps_old_url(editor_client, author, make_post, client):
    post = make_post("Original", slug="original")
    response = editor_client.post(
        reverse("studio:post_edit", args=[post.pk]),
        form_data(author, title="Updated", slug="updated", status="published"),
    )
    assert response.status_code == 302
    post.refresh_from_db()
    assert post.title == "Updated"
    assert SlugRedirect.objects.filter(old_slug="original", post=post).exists()
    assert client.get("/posts/original/")["Location"] == "/posts/updated/"


def test_edit_form_prefills_tags(editor_client, make_post):
    post = make_post("Tagged", tags=["Alpha", "Beta"])
    response = editor_client.get(reverse("studio:post_edit", args=[post.pk]))
    assert response.context["form"]["tags"].value() == "Alpha, Beta"


def test_publish_and_unpublish_actions(editor_client, make_post):
    post = make_post("Toggle", state="draft")
    editor_client.post(reverse("studio:post_publish", args=[post.pk]))
    post.refresh_from_db()
    assert post.is_live
    editor_client.post(reverse("studio:post_unpublish", args=[post.pk]))
    post.refresh_from_db()
    assert post.state == "draft"


def test_publish_action_refuses_empty_body(editor_client, make_post):
    post = make_post("Empty", state="draft", body="")
    editor_client.post(reverse("studio:post_publish", args=[post.pk]))
    post.refresh_from_db()
    assert post.state == "draft"


def test_action_redirect_ignores_offsite_next(editor_client, make_post):
    post = make_post("Toggle", state="draft")
    response = editor_client.post(
        reverse("studio:post_publish", args=[post.pk]), {"next": "https://evil.example/"}
    )
    assert "evil.example" not in response["Location"]


def test_delete_requires_confirmation_page_then_post(editor_client, make_post):
    post = make_post("Doomed")
    confirm = editor_client.get(reverse("studio:post_delete", args=[post.pk]))
    assert confirm.status_code == 200
    assert "can't be undone" in confirm.content.decode().replace("&#x27;", "'")
    assert Post.objects.filter(pk=post.pk).exists()
    editor_client.post(reverse("studio:post_delete", args=[post.pk]))
    assert not Post.objects.filter(pk=post.pk).exists()


def test_preview_renders_public_layout_without_saving(editor_client, author):
    response = editor_client.post(
        reverse("studio:post_preview"),
        form_data(author, title="Preview me", body="## Heading\n\nPreview body", tags="NewTag"),
    )
    html = response.content.decode()
    assert response.status_code == 200
    assert "Preview me" in html and "<h2>Heading</h2>" in html
    assert "preview-banner" in html
    assert 'name="robots" content="noindex' in html
    assert not Post.objects.exists()
    assert not Tag.objects.exists()


def test_preview_of_existing_post_does_not_modify_it(editor_client, author, make_post):
    post = make_post("Saved title", slug="saved")
    editor_client.post(
        reverse("studio:post_preview"),
        form_data(author, title="Unsaved title", slug="saved", post_id=post.pk),
    )
    post.refresh_from_db()
    assert post.title == "Saved title"


def test_cover_upload_creates_image(editor_client, author):
    data = form_data(author, new_cover_alt="A red square")
    data["new_cover"] = upload()
    response = editor_client.post(reverse("studio:post_create"), data)
    assert response.status_code == 302
    post = Post.objects.get()
    assert post.cover_image.alt_text == "A red square"
    assert Image.objects.count() == 1


def test_cover_upload_requires_alt_text(editor_client, author):
    data = form_data(author)
    data["new_cover"] = upload()
    response = editor_client.post(reverse("studio:post_create"), data)
    assert response.status_code == 400
    assert "new_cover_alt" in response.context["form"].errors
    assert not Image.objects.exists()


def test_post_list_filters(editor_client, make_post):
    make_post("Live one")
    make_post("Draft one", state="draft")
    make_post("Later one", state="scheduled")

    def titles(query):
        response = editor_client.get(reverse("studio:post_list") + query)
        return [p.title for p in response.context["posts"]]

    assert titles("?state=draft") == ["Draft one"]
    assert titles("?state=scheduled") == ["Later one"]
    assert titles("?state=published") == ["Live one"]
    assert titles("?q=later") == ["Later one"]


def test_dashboard_reports_real_counts(editor_client, make_post):
    make_post("A")
    make_post("B", state="draft")
    make_post("C", state="scheduled")
    counts = editor_client.get(reverse("studio:dashboard")).context["counts"]
    assert (counts["published"], counts["drafts"], counts["scheduled"]) == (1, 1, 1)


def test_author_with_posts_cannot_be_deleted(editor_client, make_post, author):
    make_post("Owned")
    editor_client.post(reverse("studio:author_delete", args=[author.pk]))
    assert type(author).objects.filter(pk=author.pk).exists()


def test_create_topic_validation(editor_client, category):
    response = editor_client.post(reverse("studio:taxonomy"), {"name": "design", "position": 0})
    assert response.status_code == 400
    response = editor_client.post(reverse("studio:taxonomy"), {"name": "Essays", "position": 1})
    assert response.status_code == 302
    from apps.blog.models import Category

    assert Category.objects.get(name="Essays").slug == "essays"
