from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator

from .markdown import html_to_text, reading_stats, render_markdown

slug_validator = RegexValidator(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    "Use lowercase letters, numbers and single hyphens (for example: my-first-post).",
    code="invalid_slug",
)


class Author(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="author_profile",
        help_text="Optional sign-in account linked to this author.",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, validators=[slug_validator])
    bio = models.TextField(blank=True, max_length=1500)
    avatar = models.ForeignKey(
        "images.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    website = models.URLField(blank=True)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("blog:author_detail", args=[self.slug])


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, validators=[slug_validator])
    description = models.TextField(blank=True, max_length=500)
    position = models.PositiveSmallIntegerField(
        default=0, help_text="Lower numbers are listed first."
    )
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["position", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("blog:category_detail", args=[self.slug])


class Tag(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=80, unique=True, validators=[slug_validator])
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("blog:tag_detail", args=[self.slug])


class PostQuerySet(models.QuerySet):
    def live(self, now=None):
        """Posts visible to the public: published and not scheduled for the future."""
        return self.filter(
            status=Post.Status.PUBLISHED,
            published_at__isnull=False,
            published_at__lte=now or timezone.now(),
        )

    def scheduled(self, now=None):
        return self.filter(status=Post.Status.PUBLISHED, published_at__gt=now or timezone.now())

    def drafts(self):
        return self.filter(status=Post.Status.DRAFT)

    def with_relations(self):
        return self.select_related("author", "category", "cover_image").prefetch_related("tags")


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, validators=[slug_validator])
    excerpt = models.TextField(
        blank=True, max_length=400, help_text="A one- or two-sentence summary shown in listings."
    )
    body = models.TextField(blank=True, help_text="Written in Markdown.")
    body_html = models.TextField(blank=True, editable=False)
    body_text = models.TextField(blank=True, editable=False)
    word_count = models.PositiveIntegerField(default=0, editable=False)
    reading_time = models.PositiveSmallIntegerField(default=1, editable=False)
    cover_image = models.ForeignKey(
        "images.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    author = models.ForeignKey(Author, on_delete=models.PROTECT, related_name="posts")
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="posts"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    featured = models.BooleanField(default=False, help_text="Feature on the home page.")
    allow_comments = models.BooleanField(default=True)
    seo_title = models.CharField("SEO title", max_length=70, blank=True)
    seo_description = models.CharField("SEO description", max_length=200, blank=True)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["status", "published_at"])]
        permissions = [("manage_publication", "Can manage the publication in the studio")]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.render()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "body" in update_fields:
            kwargs["update_fields"] = set(update_fields) | {
                "body_html",
                "body_text",
                "word_count",
                "reading_time",
            }
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:post_detail", args=[self.slug])

    def render(self):
        self.body_html = render_markdown(self.body)
        self.body_text = html_to_text(self.body_html)
        self.word_count, self.reading_time = reading_stats(self.body_text)

    # --- Publication state ---------------------------------------------------

    @property
    def state(self):
        if self.status == self.Status.DRAFT or not self.published_at:
            return "draft"
        if self.published_at > timezone.now():
            return "scheduled"
        return "published"

    @property
    def is_live(self):
        return self.state == "published"

    @property
    def is_scheduled(self):
        return self.state == "scheduled"

    def get_state_display(self):
        return {"draft": "Draft", "scheduled": "Scheduled", "published": "Published"}[self.state]

    # --- Presentation --------------------------------------------------------

    @property
    def summary(self):
        return self.excerpt or Truncator(self.body_text).words(40)

    @property
    def meta_title(self):
        return self.seo_title or self.title

    @property
    def meta_description(self):
        return self.seo_description or Truncator(self.summary).chars(200)

    @property
    def comments_open(self):
        return settings.COMMENTS_ENABLED and self.allow_comments and self.is_live


class SlugRedirect(models.Model):
    """Keeps old article URLs working after a slug change (served as a 301)."""

    old_slug = models.SlugField(max_length=200, unique=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="slug_redirects")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.old_slug} → {self.post.slug}"
