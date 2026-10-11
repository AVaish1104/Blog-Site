import pytest

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db


def test_login_page_renders(client):
    response = client.get("/studio/login/")
    assert response.status_code == 200
    assert 'autocomplete="current-password"' in response.content.decode()


def test_editor_can_sign_in_and_out(client, editor):
    response = client.post("/studio/login/", {"username": "editor", "password": PASSWORD})
    assert response.status_code == 302
    assert response["Location"] == "/studio/"
    assert client.get("/studio/").status_code == 200

    response = client.post("/studio/logout/")
    assert response.status_code == 302
    assert client.get("/studio/").status_code == 302


def test_logout_requires_post(client, editor):
    client.force_login(editor)
    assert client.get("/studio/logout/").status_code == 405
    assert client.get("/studio/").status_code == 200


def test_wrong_password_shows_error(client, editor):
    response = client.post("/studio/login/", {"username": "editor", "password": "nope"})
    assert response.status_code == 200
    assert "didn" in response.content.decode()


def test_repeated_failures_lock_the_account_out(client, editor):
    for _ in range(5):
        client.post("/studio/login/", {"username": "editor", "password": "wrong"})
    response = client.post("/studio/login/", {"username": "editor", "password": PASSWORD})
    assert response.status_code == 429
    assert "temporarily paused" in response.content.decode()
    assert client.get("/studio/").status_code == 302


def test_login_ignores_offsite_next(client, editor):
    response = client.post(
        "/studio/login/?next=https://evil.example/",
        {"username": "editor", "password": PASSWORD, "next": "https://evil.example/"},
    )
    assert response.status_code == 302
    assert "evil.example" not in response["Location"]


def test_password_change_requires_login(client):
    assert client.get("/studio/account/password/").status_code == 302
