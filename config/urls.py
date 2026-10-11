from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.templatetags.static import static
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve

from apps.blog.sitemaps import sitemaps
from apps.core import views as core_views

admin.site.site_header = f"{settings.SITE_NAME} — system admin"

urlpatterns = [
    path("", include("apps.blog.urls")),
    path("studio/", include("apps.accounts.urls")),
    path("studio/", include("apps.studio.urls")),
    path("newsletter/", include("apps.newsletter.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", core_views.robots_txt, name="robots_txt"),
    path("favicon.ico", RedirectView.as_view(url=static("favicon.svg"), permanent=True)),
]

if settings.ADMIN_PATH:
    urlpatterns.append(path(settings.ADMIN_PATH, admin.site.urls))

if settings.SERVE_MEDIA:
    urlpatterns.append(
        re_path(
            r"^%s(?P<path>.*)$" % settings.MEDIA_URL.lstrip("/"),  # noqa: UP031
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    )

handler400 = "apps.core.views.bad_request"
handler403 = "apps.core.views.permission_denied"
handler404 = "apps.core.views.page_not_found"
handler500 = "apps.core.views.server_error"
