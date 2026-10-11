from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Project user model (defined up front so it can be extended without data migrations)."""

    @property
    def can_manage_publication(self):
        return self.is_active and self.has_perm("blog.manage_publication")
