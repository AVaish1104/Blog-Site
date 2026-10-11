from django.db import models


class RateLimitCounter(models.Model):
    """Fixed-window request counter shared by every server process via the database."""

    key = models.CharField(max_length=100)
    window_start = models.DateTimeField(db_index=True)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["key", "window_start"], name="unique_ratelimit_window")
        ]

    def __str__(self):
        return f"{self.key} @ {self.window_start:%Y-%m-%d %H:%M} = {self.count}"
