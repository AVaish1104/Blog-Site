import getpass
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.blog.models import Author
from apps.blog.services import unique_slug
from apps.studio.access import ensure_editor_group


class Command(BaseCommand):
    help = (
        "Create (or update) an editor account that can use the studio, plus a matching author "
        "profile. The password is read from EDITOR_PASSWORD or prompted for."
    )

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--email", default="")
        parser.add_argument("--name", default="", help="Author display name.")
        parser.add_argument("--no-author", action="store_true", help="Skip the author profile.")

    def handle(self, username, email="", name="", no_author=False, **options):
        password = os.environ.get("EDITOR_PASSWORD")
        if not password:
            if not os.isatty(0):
                raise CommandError("Set EDITOR_PASSWORD or run interactively.")
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Password (again): "):
                raise CommandError("Passwords didn't match.")

        User = get_user_model()
        user = User.objects.filter(username=username).first() or User(username=username)
        try:
            validate_password(password, user)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from None

        if email:
            user.email = email
        user.set_password(password)
        user.is_active = True
        user.save()
        user.groups.add(ensure_editor_group())

        if not no_author and not Author.objects.filter(user=user).exists():
            display = name or username
            Author.objects.create(
                user=user, name=display, slug=unique_slug(display, model=Author, max_length=140)
            )
        self.stdout.write(
            self.style.SUCCESS(f"Editor '{username}' is ready to sign in at /studio/.")
        )
