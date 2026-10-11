from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from .models import Author, Category, Post, Tag


class PostSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Post.objects.live().only("slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at


class _LiveRelatedSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5
    model = None

    def items(self):
        return self.model.objects.filter(
            posts__status=Post.Status.PUBLISHED, posts__published_at__lte=timezone.now()
        ).distinct()


class CategorySitemap(_LiveRelatedSitemap):
    model = Category


class TagSitemap(_LiveRelatedSitemap):
    model = Tag
    priority = 0.3


class AuthorSitemap(_LiveRelatedSitemap):
    model = Author
    priority = 0.4


class StaticSitemap(Sitemap):
    changefreq = "daily"
    priority = 1.0

    def items(self):
        return ["blog:home", "blog:post_list", "blog:category_list"]

    def location(self, item):
        return reverse(item)


sitemaps = {
    "static": StaticSitemap,
    "posts": PostSitemap,
    "topics": CategorySitemap,
    "tags": TagSitemap,
    "authors": AuthorSitemap,
}
