"""
Markdown → safe HTML.

Raw HTML in Markdown is disabled at the parser, and the output is passed through
nh3 (an allow-list sanitizer) as defence in depth, so post bodies can never
inject scripts, event handlers, styles or iframes.
"""

import html
import math
import re

import nh3
from markdown_it import MarkdownIt

WORDS_PER_MINUTE = 230

_md = MarkdownIt("commonmark", {"html": False, "typographer": True}).enable(
    ["table", "strikethrough", "replacements", "smartquotes"]
)


def _demote_h1(renderer, tokens, idx, options, env):
    # The article title is the page's only <h1>; body headings start at <h2>.
    token = tokens[idx]
    if token.tag == "h1":
        token.tag = "h2"
    return renderer.renderToken(tokens, idx, options, env)


def _lazy_image(renderer, tokens, idx, options, env):
    token = tokens[idx]
    token.attrSet("loading", "lazy")
    token.attrSet("decoding", "async")
    return renderer.image(tokens, idx, options, env)


_md.add_render_rule("heading_open", _demote_h1)
_md.add_render_rule("heading_close", _demote_h1)
_md.add_render_rule("image", _lazy_image)

ALLOWED_TAGS = {
    "p",
    "br",
    "hr",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "strong",
    "em",
    "del",
    "s",
    "code",
    "pre",
    "blockquote",
    "ul",
    "ol",
    "li",
    "a",
    "img",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "sup",
    "sub",
}
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "loading", "decoding"},
    "ol": {"start"},
    "code": {"class"},
}


def sanitize(raw_html):
    return nh3.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer",
        strip_comments=True,
    )


def render_markdown(source):
    return sanitize(_md.render(source or ""))


def html_to_text(rendered_html):
    text = nh3.clean(rendered_html, tags=set())
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def reading_stats(text):
    words = len(text.split())
    minutes = max(1, math.ceil(words / WORDS_PER_MINUTE)) if words else 1
    return words, minutes
