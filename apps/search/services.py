import re
from dataclasses import dataclass, field

from django.utils.html import escape
from django.utils.safestring import mark_safe

from apps.blog.models import Post

from .backends import get_backend, parse_terms

MAX_QUERY_LENGTH = 200


@dataclass
class SearchOutcome:
    query: str
    terms: list = field(default_factory=list)
    results: list = field(default_factory=list)
    error: str = ""


def search_posts(raw_query):
    query = (raw_query or "").strip()
    if len(query) > MAX_QUERY_LENGTH:
        return SearchOutcome(
            query=query[:MAX_QUERY_LENGTH],
            error=f"Searches are limited to {MAX_QUERY_LENGTH} characters.",
        )
    terms = parse_terms(query)
    if query and not terms:
        return SearchOutcome(query=query, error="Try searching with letters or numbers.")
    results = get_backend().search(terms, Post.objects.live())
    return SearchOutcome(query=query, terms=terms, results=results)


def highlight_snippet(text, terms, radius=110):
    """Escaped context around the first matching term, with matches wrapped in <mark>."""
    if not text:
        return ""
    lowered = text.lower()
    positions = [lowered.find(t) for t in terms if lowered.find(t) >= 0]
    if positions:
        center = min(positions)
        start, end = max(0, center - radius), min(len(text), center + radius)
    else:
        start, end = 0, min(len(text), radius * 2)
    snippet = escape(text[start:end])
    if terms:
        pattern = re.compile("|".join(re.escape(t) for t in terms), re.IGNORECASE)
        snippet = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", snippet)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return mark_safe(f"{prefix}{snippet}{suffix}")  # noqa: S308 — content escaped above
