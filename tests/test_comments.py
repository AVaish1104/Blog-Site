import time

import pytest
from django.urls import reverse

from apps.comments.forms import issue_token
from apps.comments.models import Comment

pytestmark = pytest.mark.django_db


def comment_data(post, **overrides):
    data = {
        "author_name": "Reader Person",
        "author_email": "reader@example.com",
        "body": "Thoughtful comment.",
        "website": "",
        "issued": issue_token(post.pk, now=time.time() - 30),
    }
    data.update(overrides)
    return data


def submit(client, post, **overrides):
    return client.post(
        reverse("blog:post_comment", args=[post.slug]), comment_data(post, **overrides)
    )


def test_valid_comment_is_held_for_moderation(client, make_post):
    post = make_post("Discuss")
    response = submit(client, post)
    assert response.status_code == 302
    comment = Comment.objects.get()
    assert comment.status == Comment.Status.PENDING
    assert comment.ip_hash and "127.0.0.1" not in comment.ip_hash
    page = client.get(post.get_absolute_url()).content.decode()
    assert "Thoughtful comment." not in page
    assert "will appear once it has been reviewed" in page


def test_approved_comments_are_shown_escaped(client, make_post):
    post = make_post("Discuss")
    Comment.objects.create(
        post=post,
        author_name="<b>Bold</b>",
        author_email="a@example.com",
        body="<script>alert(1)</script>",
        status=Comment.Status.APPROVED,
    )
    page = client.get(post.get_absolute_url()).content.decode()
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "<script>alert(1)</script>" not in page
    assert "&lt;b&gt;Bold&lt;/b&gt;" in page


def test_honeypot_rejects_bots(client, make_post):
    post = make_post("Discuss")
    response = submit(client, post, website="http://spam.example")
    assert response.status_code == 400
    assert not Comment.objects.exists()


def test_too_fast_submission_is_rejected(client, make_post):
    post = make_post("Discuss")
    response = submit(client, post, issued=issue_token(post.pk))
    assert response.status_code == 400
    assert "quick" in response.content.decode()


def test_tampered_or_expired_token_is_rejected(client, make_post):
    post = make_post("Discuss")
    assert submit(client, post, issued="garbage").status_code == 400
    old = issue_token(post.pk, now=time.time() - 60 * 60 * 25)
    response = submit(client, post, issued=old)
    assert response.status_code == 400
    assert "expired" in response.content.decode()
    assert not Comment.objects.exists()


def test_token_for_another_post_is_rejected(client, make_post):
    post, other = make_post("One"), make_post("Two")
    assert (
        submit(client, post, issued=issue_token(other.pk, now=time.time() - 30)).status_code == 400
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"author_name": ""},
        {"author_email": "not-an-email"},
        {"body": ""},
        {"body": "x" * 3001},
        {"body": "http://a http://b http://c http://d"},
    ],
)
def test_invalid_comment_fields(client, make_post, overrides):
    post = make_post("Discuss")
    response = submit(client, post, **overrides)
    assert response.status_code == 400
    assert not Comment.objects.exists()
    assert "Please fix the following" in response.content.decode()


def test_comments_closed_per_post_and_on_drafts(client, make_post):
    closed = make_post("Closed", allow_comments=False)
    submit(client, closed)
    draft = make_post("Draft", state="draft")
    assert submit(client, draft).status_code == 404
    assert not Comment.objects.exists()


def test_comments_closed_site_wide(client, make_post, settings):
    settings.COMMENTS_ENABLED = False
    post = make_post("Discuss")
    submit(client, post)
    assert not Comment.objects.exists()
    assert "Comments are closed" in client.get(post.get_absolute_url()).content.decode()


def test_rate_limit(client, make_post):
    post = make_post("Discuss")
    for i in range(5):
        assert submit(client, post, body=f"Comment {i}").status_code == 302
    response = submit(client, post, body="One too many")
    assert response.status_code == 400
    assert "several comments recently" in response.content.decode()
    assert Comment.objects.count() == 5


def test_moderation_actions(editor_client, make_post, client):
    post = make_post("Discuss")
    comment = Comment.objects.create(
        post=post, author_name="A", author_email="a@example.com", body="Please approve"
    )
    url = reverse("studio:comment_moderate", args=[comment.pk])
    editor_client.post(url, {"action": "approve"})
    comment.refresh_from_db()
    assert comment.status == Comment.Status.APPROVED and comment.moderated_by is not None
    assert "Please approve" in client.get(post.get_absolute_url()).content.decode()
    editor_client.post(url, {"action": "spam"})
    comment.refresh_from_db()
    assert comment.status == Comment.Status.SPAM
    editor_client.post(url, {"action": "delete"})
    assert not Comment.objects.exists()


def test_moderation_queue_defaults_to_pending(editor_client, make_post):
    post = make_post("Discuss")
    Comment.objects.create(post=post, author_name="P", author_email="p@example.com", body="pending")
    Comment.objects.create(
        post=post,
        author_name="A",
        author_email="a@example.com",
        body="ok",
        status=Comment.Status.APPROVED,
    )
    response = editor_client.get(reverse("studio:comment_list"))
    assert [c.body for c in response.context["comments"]] == ["pending"]
