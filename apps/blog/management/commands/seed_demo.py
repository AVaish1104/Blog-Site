import io
import random
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image as PILImage
from PIL import ImageDraw

from apps.blog import demo_content as demo
from apps.blog.models import Author, Category, Post, Tag
from apps.blog.services import save_post
from apps.comments.models import Comment
from apps.images.models import Image
from apps.images.services import create_image

PALETTE = {
    "paper": (246, 245, 241),
    "white": (255, 255, 255),
    "ink": (20, 20, 20),
    "grey": (207, 203, 195),
    "accent": (168, 50, 26),
}


def generate_cover(seed, width=1600, height=1000):
    """An abstract, typographic-feeling composition — original artwork, no licensing issues."""
    rng = random.Random(seed)
    image = PILImage.new("RGB", (width, height), PALETTE["paper"] if seed % 2 else PALETTE["white"])
    draw = ImageDraw.Draw(image)
    columns = 12
    col = width / columns
    for i in range(1, columns):  # faint grid
        draw.line([(i * col, 0), (i * col, height)], fill=PALETTE["grey"], width=1)
    # Keep every composition inside the central square so thumbnail crops never look empty.
    left, right = (width - height) / 2 + 80, (width + height) / 2 - 80
    cx, cy = width / 2, height / 2
    style = seed % 4
    if style == 0:
        r = rng.randint(220, 300)
        cx += rng.choice([-1, 1]) * col
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PALETTE["accent"])
        draw.rectangle(
            [left - 80, cy + r * 0.45, right + 80, cy + r * 0.45 + 14], fill=PALETTE["ink"]
        )
    elif style == 1:
        for i in range(7):
            y = height * 0.2 + i * height * 0.1
            x = left + rng.randint(0, 4) * col / 2
            draw.rectangle(
                [x, y, min(right, x + col * rng.randint(3, 6)), y + 22],
                fill=PALETTE["accent"] if i == 3 else PALETTE["ink"],
            )
    elif style == 2:
        draw.rectangle(
            [left + col, height * 0.18, cx + col / 2, height * 0.82], fill=PALETTE["ink"]
        )
        r = col * 1.6
        draw.ellipse([cx - r / 2, cy - r, cx + r * 1.5, cy + r], fill=PALETTE["accent"])
    else:
        for i in range(13):
            y = height * 0.17 + i * 50
            length = col * rng.randint(2, 6)
            draw.rectangle(
                [left, y, min(right, left + length), y + 12],
                fill=PALETTE["accent"] if i == 6 else PALETTE["ink"],
            )
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=88)
    return SimpleUploadedFile(f"demo-cover-{seed}.jpg", buffer.getvalue(), "image/jpeg")


class Command(BaseCommand):
    help = "Create clearly marked demo content (author, topics, posts) for a first run."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Remove all demo content.")

    def handle(self, *args, clear=False, **options):
        if clear:
            self.clear()
            return
        if Post.objects.filter(is_demo=True).exists():
            self.stdout.write("Demo content already exists. Use --clear to remove it first.")
            return
        with transaction.atomic():
            self.seed()

    def clear(self):
        with transaction.atomic():
            posts = Post.objects.filter(is_demo=True)
            Comment.objects.filter(post__in=posts).delete()
            count = posts.count()
            posts.delete()
            Author.objects.filter(is_demo=True, posts__isnull=True).delete()
            Category.objects.filter(is_demo=True, posts__isnull=True).delete()
            Tag.objects.filter(is_demo=True, posts__isnull=True).delete()
            used = set(Post.objects.exclude(cover_image=None).values_list("cover_image", flat=True))
            images = Image.objects.filter(is_demo=True).exclude(pk__in=used)
            for image in images:
                image.delete()
        self.stdout.write(self.style.SUCCESS(f"Removed {count} demo posts and related demo data."))

    def seed(self):
        now = timezone.now()
        existing_tags = set(Tag.objects.values_list("pk", flat=True))
        author, _ = Author.objects.get_or_create(
            slug=demo.AUTHOR["slug"], defaults={**demo.AUTHOR, "is_demo": True}
        )
        categories = {}
        for position, (name, slug, description) in enumerate(demo.CATEGORIES):
            existing = Category.objects.filter(name__iexact=name).first()
            if existing:
                categories[slug] = existing
                continue
            categories[slug], _ = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "position": position,
                    "is_demo": True,
                },
            )

        def make_post(
            index,
            title,
            category,
            tags,
            excerpt,
            body,
            *,
            published_at,
            status,
            featured=False,
            cover=True,
        ):
            cover_image = None
            if cover:
                cover_image = create_image(
                    generate_cover(index),
                    f"Abstract composition illustrating “{title}”",
                    is_demo=True,
                )
            post = Post(
                title=title,
                slug=title_slug(title),
                excerpt=excerpt,
                body=body,
                author=author,
                category=categories[category],
                status=status,
                published_at=published_at,
                featured=featured,
                cover_image=cover_image,
                is_demo=True,
            )
            save_post(post, tag_names=tags)
            return post

        for index, (title, category, tags, excerpt, body, days_ago, featured) in enumerate(
            demo.POSTS
        ):
            make_post(
                index,
                title,
                category,
                tags,
                excerpt,
                body,
                published_at=now - timedelta(days=days_ago, hours=index),
                status=Post.Status.PUBLISHED,
                featured=featured,
                cover=index % 3 != 2,
            )

        title, category, tags, excerpt, body, days_ahead = demo.SCHEDULED_POST
        make_post(
            90,
            title,
            category,
            tags,
            excerpt,
            body,
            published_at=now + timedelta(days=-days_ahead),
            status=Post.Status.PUBLISHED,
            cover=False,
        )
        title, category, tags, excerpt, body = demo.DRAFT_POST
        make_post(
            91,
            title,
            category,
            tags,
            excerpt,
            body,
            published_at=None,
            status=Post.Status.DRAFT,
            cover=False,
        )

        Tag.objects.exclude(pk__in=existing_tags).update(is_demo=True)
        first = Post.objects.live().filter(is_demo=True).order_by("-published_at").first()
        Comment.objects.create(
            post=first,
            author_name="A sample reader",
            author_email="reader@example.com",
            body="A demo comment, approved so you can see how comments appear.",
            status=Comment.Status.APPROVED,
        )
        Comment.objects.create(
            post=first,
            author_name="Another sample reader",
            author_email="other@example.com",
            body="A demo comment awaiting moderation. Approve or reject it in the studio.",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {Post.objects.filter(is_demo=True).count()} demo posts "
                "(12 published, 1 scheduled, 1 draft), 4 topics and 2 comments."
            )
        )


def title_slug(title):
    from apps.blog.services import unique_slug

    return unique_slug(title)
