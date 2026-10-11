"""
Authorization matrix: every studio URL is checked as an anonymous visitor, a
signed-in user without editor permission, and an editor. Write endpoints are
also checked to make sure a refused request changes nothing.
"""

import pytest
from django.urls import reverse

from apps.blog.models import Category, Post, Tag
from apps.comments.models import Comment
from apps.images.models import Image
from apps.newsletter.models import Subscriber

pytestmark = pytest.mark.django_db


@pytest.fixture
def objects(make_post, category, author):
    post = make_post("Protected", tags=["Secret"])
    comment = Comment.objects.create(
        post=post, author_name="Ann", author_email="a@example.com", body="Hi"
    )
    subscriber = Subscriber.objects.create(
        email="s@example.com", consent_text="x", consented_at=post.published_at
    )
    from django.core.files.base import ContentFile

    from .conftest import image_bytes

    image = Image(alt_text="pic")
    image.file.save("pic.jpg", ContentFile(image_bytes()), save=False)
    image.width = image.height = 10
    image.save()
    return {
        "post": post,
        "category": category,
        "author": author,
        "comment": comment,
        "subscriber": subscriber,
        "image": image,
        "tag": Tag.objects.get(name="Secret"),
    }


def studio_get_urls(o):
    return [
        reverse("studio:dashboard"),
        reverse("studio:post_list"),
        reverse("studio:post_create"),
        reverse("studio:post_edit", args=[o["post"].pk]),
        reverse("studio:post_saved_preview", args=[o["post"].pk]),
        reverse("studio:post_delete", args=[o["post"].pk]),
        reverse("studio:image_list"),
        reverse("studio:image_edit", args=[o["image"].pk]),
        reverse("studio:image_delete", args=[o["image"].pk]),
        reverse("studio:taxonomy"),
        reverse("studio:category_edit", args=[o["category"].pk]),
        reverse("studio:category_delete", args=[o["category"].pk]),
        reverse("studio:tag_edit", args=[o["tag"].pk]),
        reverse("studio:tag_delete", args=[o["tag"].pk]),
        reverse("studio:author_list"),
        reverse("studio:author_create"),
        reverse("studio:author_edit", args=[o["author"].pk]),
        reverse("studio:author_delete", args=[o["author"].pk]),
        reverse("studio:comment_list"),
        reverse("studio:subscriber_list"),
        reverse("studio:subscriber_export"),
        reverse("studio:subscriber_delete", args=[o["subscriber"].pk]),
    ]


def studio_post_actions(o):
    """(url, data) for every state-changing endpoint."""
    pk = o["post"].pk
    return [
        (
            reverse("studio:post_create"),
            {"title": "Injected", "author": o["author"].pk, "status": "published", "body": "x"},
        ),
        (
            reverse("studio:post_edit", args=[pk]),
            {"title": "Hacked", "author": o["author"].pk, "status": "published", "body": "x"},
        ),
        (reverse("studio:post_publish", args=[pk]), {}),
        (reverse("studio:post_unpublish", args=[pk]), {}),
        (reverse("studio:post_delete", args=[pk]), {}),
        (
            reverse("studio:post_preview"),
            {"title": "x", "author": o["author"].pk, "status": "draft"},
        ),
        (reverse("studio:image_delete", args=[o["image"].pk]), {}),
        (reverse("studio:image_edit", args=[o["image"].pk]), {"alt_text": "hacked"}),
        (reverse("studio:taxonomy"), {"name": "Injected topic"}),
        (reverse("studio:category_delete", args=[o["category"].pk]), {}),
        (reverse("studio:tag_delete", args=[o["tag"].pk]), {}),
        (reverse("studio:author_delete", args=[o["author"].pk]), {}),
        (reverse("studio:comment_moderate", args=[o["comment"].pk]), {"action": "approve"}),
        (reverse("studio:subscriber_delete", args=[o["subscriber"].pk]), {}),
    ]


def snapshot():
    return (
        list(Post.objects.values_list("pk", "title", "status", "published_at")),
        list(Category.objects.values_list("pk", "name")),
        list(Tag.objects.values_list("pk", "name")),
        list(Comment.objects.values_list("pk", "status")),
        list(Subscriber.objects.values_list("pk")),
        list(Image.objects.values_list("pk", "alt_text")),
    )


def test_anonymous_visitors_are_sent_to_sign_in(client, objects):
    for url in studio_get_urls(objects):
        response = client.get(url)
        assert response.status_code == 302, url
        assert response["Location"].startswith("/studio/login/"), url


def test_non_editors_are_forbidden(client, reader_user, objects):
    client.force_login(reader_user)
    for url in studio_get_urls(objects):
        assert client.get(url).status_code == 403, url


def test_editors_can_open_every_studio_page(editor_client, objects):
    for url in studio_get_urls(objects):
        assert editor_client.get(url).status_code == 200, url


@pytest.mark.parametrize("who", ["anonymous", "reader"])
def test_refused_writes_change_nothing(client, reader_user, objects, who):
    if who == "reader":
        client.force_login(reader_user)
    before = snapshot()
    for url, data in studio_post_actions(objects):
        response = client.post(url, data)
        assert response.status_code in (302, 403), url
        if who == "anonymous":
            assert response["Location"].startswith("/studio/login/"), url
    assert snapshot() == before


def test_csrf_is_enforced_on_studio_writes(editor, objects):
    from django.test import Client

    strict = Client(enforce_csrf_checks=True)
    strict.force_login(editor)
    response = strict.post(reverse("studio:post_delete", args=[objects["post"].pk]))
    assert response.status_code == 403
    assert Post.objects.filter(pk=objects["post"].pk).exists()


def test_superuser_without_group_is_an_editor(client, objects, django_user_model):
    admin = django_user_model.objects.create_superuser("root", "r@example.com", "pw-123456789")
    client.force_login(admin)
    assert client.get(reverse("studio:dashboard")).status_code == 200


def test_inactive_editor_is_refused(client, editor, objects):
    editor.is_active = False
    editor.save()
    client.force_login(editor)
    assert client.get(reverse("studio:dashboard")).status_code in (302, 403)
