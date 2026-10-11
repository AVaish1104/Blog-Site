"""Business logic for posts, kept out of views so the studio and tests share it."""

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.text import slugify

from .models import Post, SlugRedirect, Tag

MAX_TAGS_PER_POST = 12


def make_slug(text, max_length=200):
    slug = slugify(text)[:max_length].strip("-")
    return slug or "untitled"


def unique_slug(text, model=Post, exclude_pk=None, max_length=200):
    base = make_slug(text, max_length - 4)
    slug, counter = base, 2
    queryset = model.objects.exclude(pk=exclude_pk) if exclude_pk else model.objects.all()

    def taken(candidate):
        if queryset.filter(slug=candidate).exists():
            return True
        # Generated post slugs never reuse an address that still redirects elsewhere.
        redirects = SlugRedirect.objects.filter(old_slug=candidate).exclude(post_id=exclude_pk)
        return model is Post and redirects.exists()

    while taken(slug):
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def parse_tag_names(raw):
    """'Design, writing ,  design' → ['Design', 'writing'] (case-insensitive de-dupe)."""
    seen, names = set(), []
    for part in (raw or "").split(","):
        name = " ".join(part.split())[:60]
        if name and name.lower() not in seen:
            seen.add(name.lower())
            names.append(name)
    return names


def get_or_create_tags(names):
    tags = []
    for name in names:
        tag = Tag.objects.filter(name__iexact=name).first()
        if tag is None:
            tag = Tag.objects.create(name=name, slug=unique_slug(name, model=Tag, max_length=80))
        tags.append(tag)
    return tags


@transaction.atomic
def save_post(post, *, tag_names=None, user=None, previous_slug=None):
    """Persist a post, its tags and any slug redirect in a single transaction."""
    if user is not None and user.is_authenticated:
        if post.pk is None:
            post.created_by = user
        post.updated_by = user
    if post.status == Post.Status.PUBLISHED and post.published_at is None:
        post.published_at = timezone.now()
    post.save()

    if tag_names is not None:
        post.tags.set(get_or_create_tags(tag_names))

    # A live post takes over its address from any old redirect with the same slug;
    # drafts and scheduled posts leave existing redirects working until they go live.
    if post.is_live:
        SlugRedirect.objects.filter(old_slug=post.slug).delete()
    if previous_slug and previous_slug != post.slug and post.published_at:
        SlugRedirect.objects.update_or_create(old_slug=previous_slug, defaults={"post": post})
    return post


def publish_now(post, user=None):
    post.status = Post.Status.PUBLISHED
    if post.published_at is None or post.published_at > timezone.now():
        post.published_at = timezone.now()
    post.updated_by = user if user and user.is_authenticated else post.updated_by
    post.save(update_fields=["status", "published_at", "updated_by", "updated_at"])
    SlugRedirect.objects.filter(old_slug=post.slug).delete()
    return post


def unpublish(post, user=None):
    post.status = Post.Status.DRAFT
    post.updated_by = user if user and user.is_authenticated else post.updated_by
    post.save(update_fields=["status", "updated_by", "updated_at"])
    return post


def related_posts(post, limit=3):
    """Posts sharing the most tags (then category), newest first; falls back to latest."""
    live = Post.objects.live().exclude(pk=post.pk)
    tag_ids = list(post.tags.values_list("pk", flat=True))
    condition = Q(shared_tags__gt=0)
    if post.category_id:
        condition |= Q(category_id=post.category_id)
    candidates = live.annotate(
        shared_tags=Count("tags", filter=Q(tags__in=tag_ids), distinct=True)
    ).filter(condition)
    related = list(candidates.order_by("-shared_tags", "-published_at").with_relations()[:limit])
    if len(related) < limit:
        exclude = [p.pk for p in related]
        related += list(live.exclude(pk__in=exclude).with_relations()[: limit - len(related)])
    return related


def adjacent_posts(post):
    live = Post.objects.live().select_related("author")
    older = live.filter(published_at__lt=post.published_at).order_by("-published_at").first()
    newer = live.filter(published_at__gt=post.published_at).order_by("published_at").first()
    return older, newer
