from django.conf import settings


def site(request):
    return {
        "publication": {
            "name": settings.SITE_NAME,
            "tagline": settings.SITE_TAGLINE,
            "url": settings.SITE_URL,
            "language": settings.SITE_LANGUAGE,
        },
        "ephemeral_data": settings.EPHEMERAL_DATA,
    }
