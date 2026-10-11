from django.apps import AppConfig


class SearchConfig(AppConfig):
    name = "apps.search"
    label = "search"

    def ready(self):
        from . import signals  # noqa: F401
