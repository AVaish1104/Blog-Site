from django.conf import settings
from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Atom1Feed

from .models import Post

FEED_SIZE = 20


class LatestPostsFeed(Feed):
    def title(self):
        return settings.SITE_NAME

    def description(self):
        return settings.SITE_TAGLINE

    # Absolute URLs from SITE_URL (Django leaves absolute links untouched), so feeds
    # never depend on the Host header of whoever requested them.
    def link(self):
        return settings.SITE_URL + reverse("blog:home")

    def feed_url(self):
        return settings.SITE_URL + reverse("blog:feed_rss")

    def item_link(self, item):
        return settings.SITE_URL + item.get_absolute_url()

    def items(self):
        return Post.objects.live().with_relations()[:FEED_SIZE]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.summary

    def item_pubdate(self, item):
        return item.published_at

    def item_updateddate(self, item):
        return item.updated_at

    def item_author_name(self, item):
        return item.author.name

    def item_categories(self, item):
        names = [tag.name for tag in item.tags.all()]
        return [item.category.name, *names] if item.category else names


class LatestPostsAtomFeed(LatestPostsFeed):
    feed_type = Atom1Feed

    def subtitle(self):
        return settings.SITE_TAGLINE

    def feed_url(self):
        return settings.SITE_URL + reverse("blog:feed_atom")
