from django.apps import AppConfig


class ImagesConfig(AppConfig):
    name = "apps.images"
    label = "images"

    def ready(self):
        from . import signals  # noqa: F401
