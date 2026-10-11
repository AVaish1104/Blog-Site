from django.conf import settings
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET


@require_GET
@cache_control(max_age=60 * 60 * 24)
def robots_txt(request):
    return render(
        request,
        "robots.txt",
        {"sitemap_url": f"{settings.SITE_URL}/sitemap.xml"},
        content_type="text/plain",
    )


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)


def permission_denied(request, exception):
    return render(request, "403.html", status=403)


def bad_request(request, exception):
    return render(request, "400.html", status=400)
