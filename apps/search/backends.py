"""
Search backends.

* SQLite → FTS5 virtual table (porter stemming, bm25 ranking, prefix matching).
* PostgreSQL → built-in full-text search with weighted vectors.
* Anything else / FTS unavailable → portable term matching with Python ranking.

All backends receive a queryset of *visible* posts and only ever return posts
from it, so drafts and scheduled posts can never leak into results.
"""

import re

from django.db import connection
from django.db.models import Q

FTS_TABLE = "search_post_fts"
MAX_TERMS = 8
MAX_RESULTS = 500
_TERM_RE = re.compile(r"\w+", re.UNICODE)


def parse_terms(query):
    seen, terms = set(), []
    for match in _TERM_RE.findall((query or "").lower()):
        term = match.strip("_")
        if term and term not in seen:
            seen.add(term)
            terms.append(term)
    return terms[:MAX_TERMS]


def document_for(post):
    return {
        "title": post.title,
        "excerpt": post.excerpt,
        "body": post.body_text,
        "tags": " ".join(tag.name for tag in post.tags.all()),
        "category": post.category.name if post.category_id else "",
    }


def _order_by_ids(queryset, ids):
    position = {pk: index for index, pk in enumerate(ids)}
    posts = list(queryset.filter(pk__in=ids).with_relations())
    return sorted(posts, key=lambda post: position[post.pk])


class BasicBackend:
    name = "basic"

    def index(self, post):
        pass

    def remove(self, post_id):
        pass

    def rebuild(self, posts):
        return 0

    def search(self, terms, queryset):
        if not terms:
            return []
        condition = Q()
        for term in terms:
            condition &= (
                Q(title__icontains=term)
                | Q(excerpt__icontains=term)
                | Q(body_text__icontains=term)
                | Q(tags__name__icontains=term)
                | Q(category__name__icontains=term)
            )
        posts = list(queryset.filter(condition).distinct().with_relations()[:MAX_RESULTS])

        def score(post):
            title, excerpt = post.title.lower(), post.excerpt.lower()
            body = post.body_text.lower()
            tags = " ".join(tag.name.lower() for tag in post.tags.all())
            return sum(
                10 * title.count(t) + 4 * excerpt.count(t) + 5 * tags.count(t) + body.count(t)
                for t in terms
            )

        return sorted(posts, key=lambda p: (-score(p), -(p.published_at.timestamp())))


class SQLiteFTSBackend(BasicBackend):
    name = "sqlite-fts5"

    def index(self, post):
        doc = document_for(post)
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {FTS_TABLE} WHERE rowid = %s", [post.pk])  # noqa: S608
            cursor.execute(
                f"INSERT INTO {FTS_TABLE} (rowid, title, excerpt, body, tags, category) "  # noqa: S608
                "VALUES (%s, %s, %s, %s, %s, %s)",
                [post.pk, doc["title"], doc["excerpt"], doc["body"], doc["tags"], doc["category"]],
            )

    def remove(self, post_id):
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {FTS_TABLE} WHERE rowid = %s", [post_id])  # noqa: S608

    def rebuild(self, posts):
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {FTS_TABLE}")  # noqa: S608
        count = 0
        for post in posts:
            self.index(post)
            count += 1
        return count

    def search(self, terms, queryset):
        if not terms:
            return []
        # Terms are \w+ tokens, so quoting them makes every term a literal prefix match.
        match = " ".join(f'"{term}"*' for term in terms)
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT rowid FROM {FTS_TABLE} WHERE {FTS_TABLE} MATCH %s "  # noqa: S608
                f"ORDER BY bm25({FTS_TABLE}, 10.0, 4.0, 1.0, 5.0, 3.0) LIMIT %s",
                [match, MAX_RESULTS],
            )
            ids = [row[0] for row in cursor.fetchall()]
        return _order_by_ids(queryset, ids)


class PostgresBackend(BasicBackend):
    name = "postgres"

    def search(self, terms, queryset):
        from django.contrib.postgres.aggregates import StringAgg
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

        if not terms:
            return []
        queryset = queryset.annotate(tag_text=StringAgg("tags__name", " ", distinct=True))
        vector = (
            SearchVector("title", weight="A")
            + SearchVector("tag_text", weight="B")
            + SearchVector("excerpt", weight="B")
            + SearchVector("category__name", weight="B")
            + SearchVector("body_text", weight="C")
        )
        query = SearchQuery(" ".join(terms), search_type="websearch")
        ids = list(
            queryset.annotate(rank=SearchRank(vector, query))
            .filter(rank__gt=0)
            .order_by("-rank", "-published_at")
            .values_list("pk", flat=True)[:MAX_RESULTS]
        )
        return _order_by_ids(queryset, ids)


def fts_table_exists():
    with connection.cursor() as cursor:
        return FTS_TABLE in connection.introspection.table_names(cursor)


def get_backend():
    if connection.vendor == "sqlite" and fts_table_exists():
        return SQLiteFTSBackend()
    if connection.vendor == "postgresql":
        return PostgresBackend()
    return BasicBackend()
