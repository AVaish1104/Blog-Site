import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def image_upload_to(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"images/{timezone.now():%Y/%m}/{uuid.uuid4().hex}.{extension}"


class Image(models.Model):
    """An uploaded, validated and re-encoded image."""

    file = models.ImageField(upload_to=image_upload_to, width_field="width", height_field="height")
    alt_text = models.CharField(
        "alt text",
        max_length=250,
        help_text="Describe the image for people who can't see it.",
    )
    width = models.PositiveIntegerField(default=0, editable=False)
    height = models.PositiveIntegerField(default=0, editable=False)
    file_size = models.PositiveIntegerField(default=0, editable=False)
    original_filename = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.alt_text or self.original_filename or f"Image {self.pk}"

    @property
    def url(self):
        return self.file.url if self.file else ""

    @property
    def markdown(self):
        alt = self.alt_text.replace("[", "").replace("]", "")
        return f"![{alt}]({self.url})"
