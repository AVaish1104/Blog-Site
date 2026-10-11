from html.parser import HTMLParser

import pytest

from apps.blog.markdown import html_to_text, reading_stats, render_markdown

XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    '<img src=x onerror="alert(1)">',
    "[click](javascript:alert(1))",
    "[click](JAVASCRIPT:alert(1))",
    '<a href="javascript:alert(1)">x</a>',
    "<iframe src='https://evil.example'></iframe>",
    '<div style="background:url(javascript:alert(1))">x</div>',
    "![x](javascript:alert(1))",
    "<svg onload=alert(1)>",
    "[x](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==)",
]


class ElementCollector(HTMLParser):
    """Collects the real elements/attributes in rendered HTML (escaped text is ignored)."""

    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


SAFE_TAGS = {"p", "a", "img", "em", "strong", "code", "pre", "br"}


@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_dangerous_markup_is_neutralised(payload):
    collector = ElementCollector()
    collector.feed(render_markdown(payload))
    for tag, attrs in collector.elements:
        assert tag in SAFE_TAGS, tag
        assert not any(name.startswith("on") for name in attrs), attrs
        assert "style" not in attrs
        for name in ("href", "src"):
            value = (attrs.get(name) or "").strip().lower()
            assert not value.startswith(("javascript:", "data:", "vbscript:")), value


def test_common_formatting_renders():
    html = render_markdown(
        "## Heading\n\n**bold** *em* `code`\n\n> quote\n\n- a\n- b\n\n[link](https://example.com)"
    )
    assert "<h2>Heading</h2>" in html
    assert "<strong>bold</strong>" in html
    assert "<em>em</em>" in html
    assert "<code>code</code>" in html
    assert "<blockquote>" in html
    assert "<li>a</li>" in html
    assert 'href="https://example.com"' in html
    assert 'rel="noopener noreferrer"' in html


def test_h1_in_body_is_demoted_so_the_title_stays_the_only_h1():
    html = render_markdown("# Big\n\ntext")
    assert "<h1" not in html
    assert "<h2>Big</h2>" in html


def test_images_are_lazy_loaded():
    html = render_markdown("![alt text](/media/a.jpg)")
    assert 'loading="lazy"' in html
    assert 'alt="alt text"' in html


def test_plain_text_and_reading_time():
    text = html_to_text(render_markdown("Hello **world** &amp; friends"))
    assert text == "Hello world & friends"
    assert reading_stats("") == (0, 1)
    assert reading_stats("word " * 230) == (230, 1)
    assert reading_stats("word " * 231) == (231, 2)
