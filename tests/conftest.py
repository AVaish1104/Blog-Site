import io
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image as PILImage

from apps.blog.models import Author, Category, Post
from apps.blog.services import save_post
from apps.studio.access import ensure_editor_group

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(autouse=True)
def _fresh_cache():
    from django.core.cache import cache

    cache.clear()


@pytest.fixture
def editor(db):
    user = get_user_model().objects.create_user("editor", "editor@example.com", PASSWORD)
    user.groups.add(ensure_editor_group())
    return user


@pytest.fixture
def reader_user(db):
    """A signed-in account WITHOUT editor permission."""
    return get_user_model().objects.create_user("reader", "reader@example.com", PASSWORD)


@pytest.fixture
def editor_client(client, editor):
    client.force_login(editor)
    return client


@pytest.fixture
def author(db):
    return Author.objects.create(name="Jane Writer", slug="jane-writer", bio="Writes things.")


@pytest.fixture
def category(db):
    return Category.objects.create(name="Design", slug="design")


@pytest.fixture
def make_post(db, author, django_capture_on_commit_callbacks):
    """Create a post through the service layer, running on-commit hooks (search indexing)."""
    counter = {"n": 0}

    def factory(title=None, *, state="published", tags=(), days_ago=1, **fields):
        counter["n"] += 1
        title = title or f"Post number {counter['n']}"
        now = timezone.now()
        status = Post.Status.DRAFT if state == "draft" else Post.Status.PUBLISHED
        published_at = None
        if state == "published":
            published_at = now - timedelta(days=days_ago)
        elif state == "scheduled":
            published_at = now + timedelta(days=days_ago)
        defaults = {
            "slug": fields.pop("slug", None) or f"post-{counter['n']}",
            "body": "Some body text for this post.",
            "author": author,
            "status": status,
            "published_at": published_at,
        }
        defaults.update(fields)
        with django_capture_on_commit_callbacks(execute=True):
            post = save_post(Post(title=title, **defaults), tag_names=list(tags))
        return post

    return factory


def image_bytes(fmt="JPEG", size=(64, 48), color=(200, 50, 30), exif=None):
    buffer = io.BytesIO()
    image = PILImage.new("RGB", size, color)
    kwargs = {"exif": exif} if exif is not None else {}
    image.save(buffer, fmt, **kwargs)
    return buffer.getvalue()


def upload(name="photo.jpg", content=None, content_type="image/jpeg"):
    return SimpleUploadedFile(name, content if content is not None else image_bytes(), content_type)
