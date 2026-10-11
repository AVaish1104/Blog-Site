from urllib.parse import urlencode

from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.search.services import highlight_snippet, search_posts

from .models import Author, Category, Post, SlugRedirect, Tag
from .services import adjacent_posts, related_posts


def paginate(request, items, per_page=None):
    paginator = Paginator(items, per_page or settings.POSTS_PER_PAGE)
    try:
        return paginator.page(request.GET.get("page") or 1)
    except (EmptyPage, PageNotAnInteger):
        raise Http404("That page doesn't exist.") from None


def live_post_counts(queryset, related_name="posts"):
    return queryset.annotate(
        post_count=Count(
            related_name,
            filter=Q(
                **{
                    f"{related_name}__status": Post.Status.PUBLISHED,
                    f"{related_name}__published_at__lte": timezone.now(),
                }
            ),
            distinct=True,
        )
    )


@require_GET
def home(request):
    live = Post.objects.live().with_relations()
    featured = live.filter(featured=True).first() or live.first()
    latest = list(live.exclude(pk=featured.pk)[:6]) if featured else []
    categories = live_post_counts(Category.objects.all()).filter(post_count__gt=0)
    return render(
        request,
        "blog/home.html",
        {
            "featured": featured,
            "latest": latest,
            "categories": categories,
            "has_more": live.count() > len(latest) + (1 if featured else 0),
        },
    )


@require_GET
def post_list(request):
    page = paginate(request, Post.objects.live().with_relations())
    return render(request, "blog/post_list.html", {"page": page})


@require_GET
def post_detail(request, slug):
    post = Post.objects.live().with_relations().filter(slug=slug).first()
    if post is None:
        redirect_entry = SlugRedirect.objects.select_related("post").filter(old_slug=slug).first()
        if redirect_entry and redirect_entry.post.is_live:
            return redirect(redirect_entry.post, permanent=True)
        raise Http404("No published post at this address.")
    return render(request, "blog/post_detail.html", article_context(post))


def article_context(post, comment_form=None):
    """Context for the public article template (also used after a failed comment)."""
    from apps.comments.forms import CommentForm

    if comment_form is None and post.comments_open:
        comment_form = CommentForm.for_post(post)
    older, newer = adjacent_posts(post)
    return {
        "post": post,
        "post_tags": list(post.tags.all()),
        "related": related_posts(post),
        "older": older,
        "newer": newer,
        "comments": post.comments.approved(),
        "comment_form": comment_form,
        "article_ld": article_structured_data(post),
    }


def article_structured_data(post):
    """schema.org BlogPosting for search engines."""
    base = settings.SITE_URL
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post.title[:110],
        "description": post.meta_description,
        "url": base + post.get_absolute_url(),
        "mainEntityOfPage": base + post.get_absolute_url(),
        "datePublished": post.published_at.isoformat() if post.published_at else None,
        "dateModified": post.updated_at.isoformat() if post.updated_at else None,
        "wordCount": post.word_count,
        "author": {
            "@type": "Person",
            "name": post.author.name,
            "url": base + post.author.get_absolute_url(),
        },
        "publisher": {"@type": "Organization", "name": settings.SITE_NAME, "url": base + "/"},
    }
    if post.cover_image:
        url = post.cover_image.url
        data["image"] = url if url.startswith("http") else base + url
    if post.category:
        data["articleSection"] = post.category.name
    keywords = [tag.name for tag in post.tags.all()]
    if keywords:
        data["keywords"] = keywords
    return {key: value for key, value in data.items() if value is not None}


@require_GET
def category_list(request):
    categories = live_post_counts(Category.objects.all())
    return render(request, "blog/category_list.html", {"categories": categories})


@require_GET
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    page = paginate(request, Post.objects.live().filter(category=category).with_relations())
    return render(request, "blog/category_detail.html", {"category": category, "page": page})


@require_GET
def tag_list(request):
    tags = live_post_counts(Tag.objects.all()).filter(post_count__gt=0).order_by("name")
    return render(request, "blog/tag_list.html", {"tags": tags})


@require_GET
def tag_detail(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    page = paginate(request, Post.objects.live().filter(tags=tag).with_relations())
    return render(request, "blog/tag_detail.html", {"tag": tag, "page": page})


@require_GET
def author_detail(request, slug):
    author = get_object_or_404(Author.objects.select_related("avatar"), slug=slug)
    page = paginate(request, Post.objects.live().filter(author=author).with_relations())
    return render(request, "blog/author_detail.html", {"author": author, "page": page})


@require_GET
def search(request):
    outcome = search_posts(request.GET.get("q", ""))
    page = None
    if outcome.terms and not outcome.error:
        page = paginate(request, outcome.results)
        for post in page.object_list:
            post.snippet = highlight_snippet(post.body_text, outcome.terms)
    return render(
        request,
        "blog/search.html",
        {"outcome": outcome, "page": page, "search_prefix": urlencode({"q": outcome.query})},
    )
