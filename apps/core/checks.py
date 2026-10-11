from django.conf import settings
from django.core.checks import Tags, Warning, register


@register(Tags.security, deploy=True)
def production_configuration(app_configs, **kwargs):
    warnings = []
    if settings.EMAIL_DELIVERY != "smtp":
        warnings.append(
            Warning(
                "No email provider is configured; newsletter confirmation emails will only "
                "be written to the server log.",
                hint="Set EMAIL_HOST and related EMAIL_* variables.",
                id="core.W001",
            )
        )
    if settings.SITE_URL.startswith("http://") and "127.0.0.1" not in settings.SITE_URL:
        warnings.append(
            Warning(
                "SITE_URL is not HTTPS; feed, sitemap and email links will use plain HTTP.",
                id="core.W002",
            )
        )
    if not settings.SERVE_MEDIA and settings.STORAGES["default"]["BACKEND"].endswith(
        "FileSystemStorage"
    ):
        warnings.append(
            Warning(
                "Uploaded media is stored on local disk but Django will not serve it.",
                hint=(
                    "Serve MEDIA_ROOT from your web server, set DJANGO_SERVE_MEDIA=true, "
                    "or configure S3-compatible storage."
                ),
                id="core.W003",
            )
        )
    return warnings
