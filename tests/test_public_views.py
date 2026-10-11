import json
import re

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_home_empty_state(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Nothing has been published yet" in response.content.decode()


def test_home_shows_featured_and_latest_but_not_drafts(client, make_post):
    make_post("Lead story", featured=True, days_ago=5)
    make_post("Recent one", days_ago=1)
    make_post("Secret draft", state="draft")
    make_post("Future post", state="scheduled")
    html = client.get("/").content.decode()
    assert "Lead story" in html
    assert "Recent one" in html
    assert "Secret draft" not in html
    assert "Future post" not in html


def test_post_list_paginates(client, make_post):
    for i in range(12):
        make_post(f"Item {i}", days_ago=i + 1)
    first = client.get("/posts/")
    assert first.status_code == 200
    assert first.context["page"].paginator.num_pages == 2
    assert len(first.context["page"].object_list) == 10
    assert client.get("/posts/?page=2").status_code == 200
    assert client.get("/posts/?page=3").status_code == 404
    assert client.get("/posts/?page=abc").status_code == 404


def test_article_page_content_and_metadata(client, make_post, category):
    post = make_post(
        "A fine article",
        category=category,
        tags=["Craft"],
        excerpt="A short summary.",
        body="Hello **reader**.",
    )
    response = client.get(post.get_absolute_url())
    html = response.content.decode()
    assert response.status_code == 200
    assert "<h1" in html and "A fine article" in html
    assert "<strong>reader</strong>" in html
    assert "Jane Writer" in html
    assert "min read" in html
    assert 'href="/topics/design/"' in html
    assert 'href="/tags/craft/"' in html
    assert '<link rel="canonical" href="http://testserver/posts/' in html
    assert 'property="og:type" content="article"' in html
    data = json.loads(re.search(r'application/ld\+json">(.*?)</script>', html, re.S).group(1))
    assert data["@type"] == "BlogPosting"
    assert data["headline"] == "A fine article"
    assert data["author"]["name"] == "Jane Writer"


@pytest.mark.parametrize("state", ["draft", "scheduled"])
def test_unpublished_posts_are_not_reachable(client, make_post, state):
    post = make_post("Hidden", state=state, slug="hidden")
    assert client.get("/posts/hidden/").status_code == 404
    assert post.slug == "hidden"


def test_missing_post_shows_helpful_404(client):
    response = client.get("/posts/does-not-exist/")
    assert response.status_code == 404
    assert "This page doesn" in response.content.decode()


def test_old_slug_redirects_permanently(client, make_post):
    from apps.blog.services import save_post

    post = make_post("Moved", slug="old-address")
    post.slug = "new-address"
    save_post(post, previous_slug="old-address")
    response = client.get("/posts/old-address/")
    assert response.status_code == 301
    assert response["Location"] == "/posts/new-address/"


def test_category_tag_and_author_pages(client, make_post, category, author):
    make_post("In design", category=category, tags=["Grids"])
    make_post("Draft in design", category=category, tags=["Grids"], state="draft")
    for url in ["/topics/", "/topics/design/", "/tags/", "/tags/grids/", "/authors/jane-writer/"]:
        response = client.get(url)
        assert response.status_code == 200, url
        html = response.content.decode()
        if url != "/topics/" and url != "/tags/":
            assert "In design" in html
            assert "Draft in design" not in html
    assert client.get("/topics/nope/").status_code == 404
    assert client.get("/tags/nope/").status_code == 404
    assert client.get("/authors/nope/").status_code == 404


def test_feeds_list_only_live_posts(client, make_post):
    make_post("Feed visible")
    make_post("Feed draft", state="draft")
    for url in [reverse("blog:feed_rss"), reverse("blog:feed_atom")]:
        response = client.get(url)
        body = response.content.decode()
        assert response.status_code == 200
        assert "Feed visible" in body
        assert "Feed draft" not in body


def test_sitemap_and_robots(client, make_post):
    post = make_post("Mapped")
    make_post("Unmapped", state="draft", slug="unmapped")
    sitemap = client.get("/sitemap.xml").content.decode()
    assert post.get_absolute_url() in sitemap
    assert "/posts/unmapped/" not in sitemap
    robots = client.get("/robots.txt")
    assert robots["Content-Type"].startswith("text/plain")
    assert "Disallow: /studio/" in robots.content.decode()
    assert "Sitemap: http://testserver/sitemap.xml" in robots.content.decode()


def test_security_headers_present(client):
    response = client.get("/")
    assert "default-src 'self'" in response["Content-Security-Policy"]
    assert response["X-Frame-Options"] == "DENY"
    assert response["X-Content-Type-Options"] == "nosniff"
