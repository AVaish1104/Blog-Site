from django.db import models


class Subscriber(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting confirmation"
        ACTIVE = "active", "Subscribed"
        UNSUBSCRIBED = "unsubscribed", "Unsubscribed"

    email = models.EmailField(unique=True, help_text="Stored lower-cased.")
    status = models.CharField(
        max_length=14, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    consent_text = models.TextField(help_text="The exact wording the subscriber agreed to.")
    consented_at = models.DateTimeField()
    source = models.CharField(max_length=50, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
