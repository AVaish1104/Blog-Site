import pytest

from apps.blog.models import Post
from apps.search.backends import BasicBackend, SQLiteFTSBackend, get_backend, parse_terms
from apps.search.services import highlight_snippet, search_posts

pytestmark = pytest.mark.django_db


def test_sqlite_uses_full_text_backend():
    assert isinstance(get_backend(), SQLiteFTSBackend)


def test_finds_posts_by_title_body_and_tag(make_post):
    by_title = make_post("Typography basics", body="Nothing relevant.")
    by_body = make_post("Another", body="A long discussion of kerning and typography.")
    by_tag = make_post("Third", body="Unrelated.", tags=["Typography"])
    results = search_posts("typography").results
    assert set(results) == {by_title, by_body, by_tag}
    assert results[0] == by_title  # title matches rank first


def test_never_returns_drafts_or_scheduled(make_post):
    make_post("Visible gardening")
    make_post("Draft gardening", state="draft")
    make_post("Scheduled gardening", state="scheduled")
    titles = [p.title for p in search_posts("gardening").results]
    assert titles == ["Visible gardening"]


def test_prefix_and_multi_term_matching(make_post):
    post = make_post("Maintaining software", body="Notes about maintenance work")
    make_post("Software only")
    assert search_posts("maint").results == [post]
    assert search_posts("software maintenance").results == [post]


def test_index_follows_edits_and_deletes(make_post, django_capture_on_commit_callbacks):
    post = make_post("Before")
    assert search_posts("before").results == [post]
    with django_capture_on_commit_callbacks(execute=True):
        post.title = "After"
        post.save()
    assert search_posts("before").results == []
    assert search_posts("after").results == [post]
    with django_capture_on_commit_callbacks(execute=True):
        post.delete()
    assert search_posts("after").results == []


def test_empty_invalid_and_overlong_queries():
    assert search_posts("").results == []
    assert search_posts("").error == ""
    assert search_posts("!!! ???").error
    assert search_posts("x" * 201).error


def test_fts_special_syntax_is_treated_as_text(make_post):
    make_post("Quotes and stars")
    for query in ['"unbalanced', "NEAR(a b)", "title:quotes", "a OR b", "*", "-quotes"]:
        outcome = search_posts(query)
        assert outcome.error == "" or outcome.results == []


def test_basic_backend_matches_and_ranks(make_post):
    title_hit = make_post("Ocean currents")
    body_hit = make_post("Other", body="The ocean is large.")
    results = BasicBackend().search(["ocean"], Post.objects.live())
    assert results == [title_hit, body_hit]


def test_parse_terms():
    assert parse_terms("Hello, hello WORLD! _x_") == ["hello", "world", "x"]


def test_snippet_escapes_content_and_marks_terms():
    html = highlight_snippet("Use <script> tags carefully with Django templates", ["django"])
    assert "&lt;script&gt;" in html
    assert "<mark>Django</mark>" in html


def test_search_page_states(client, make_post):
    make_post("Searchable thing")
    assert "Search the archive" in client.get("/search/").content.decode()
    found = client.get("/search/?q=searchable").content.decode()
    assert "1 result" in found and "Searchable thing" in found
    assert "No articles matched" in client.get("/search/?q=nomatchword").content.decode()
    assert "couldn" in client.get("/search/?q=%21%21").content.decode()
