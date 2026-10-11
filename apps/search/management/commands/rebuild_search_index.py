from django.core.management.base import BaseCommand

from apps.blog.models import Post
from apps.search.backends import get_backend


class Command(BaseCommand):
    help = "Rebuild the full-text search index from all posts."

    def handle(self, *args, **options):
        backend = get_backend()
        posts = Post.objects.select_related("category").prefetch_related("tags")
        count = backend.rebuild(posts.iterator(chunk_size=200))
        self.stdout.write(self.style.SUCCESS(f"Indexed {count} posts using '{backend.name}'."))
