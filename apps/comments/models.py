from django.conf import settings
from django.db import models


class CommentQuerySet(models.QuerySet):
    def approved(self):
        return self.filter(status=Comment.Status.APPROVED).order_by("created_at")

    def pending(self):
        return self.filter(status=Comment.Status.PENDING)


class Comment(models.Model):
    """A reader comment. Nothing is shown publicly until an editor approves it."""

    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SPAM = "spam", "Spam"

    post = models.ForeignKey("blog.Post", on_delete=models.CASCADE, related_name="comments")
    author_name = models.CharField("name", max_length=80)
    author_email = models.EmailField("email", help_text="Never published.")
    body = models.TextField("comment", max_length=3000)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    ip_hash = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    objects = CommentQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author_name} on {self.post}"
