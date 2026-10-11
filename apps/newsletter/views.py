from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from apps.core.net import ip_hash
from apps.core.ratelimit import hit_for_request

from . import services
from .forms import SubscribeForm
from .services import Delivery

RATE_LIMIT = 5
RATE_PERIOD_SECONDS = 600


@require_http_methods(["GET", "POST"])
def subscribe(request):
    if request.method == "GET":
        return render(request, "newsletter/subscribe.html", {"form": SubscribeForm()})

    form = SubscribeForm(request.POST)
    if hit_for_request(request, "newsletter", RATE_LIMIT, RATE_PERIOD_SECONDS):
        form.add_error(None, "Too many attempts from your connection. Please try again later.")
    elif form.is_valid():
        result = services.subscribe(
            form.cleaned_data["email"],
            source=form.cleaned_data.get("source") or "website",
            ip_hash=ip_hash(request),
        )
        delivery = result.delivery
        if delivery is Delivery.SKIPPED and settings.EMAIL_DELIVERY != "smtp":
            # Without a provider, report the same outcome for new and existing
            # addresses so the page never reveals who is subscribed.
            delivery = Delivery.LOGGED
        return render(request, "newsletter/result.html", {"delivery": delivery.value})
    return render(request, "newsletter/subscribe.html", {"form": form}, status=400)


@require_GET
def confirm(request, token):
    subscriber, error = services.confirm(token)
    return render(
        request,
        "newsletter/confirm.html",
        {"subscriber": subscriber, "error": error},
        status=400 if error else 200,
    )


@require_http_methods(["GET", "POST"])
def unsubscribe(request, token):
    # GET shows a confirmation button so link scanners can't unsubscribe people.
    if request.method == "GET":
        subscriber, error = services.find_by_unsubscribe_token(token)
        return render(
            request,
            "newsletter/unsubscribe.html",
            {"token": token, "subscriber": subscriber, "error": error, "done": False},
            status=400 if error else 200,
        )
    subscriber, error = services.unsubscribe(token)
    return render(
        request,
        "newsletter/unsubscribe.html",
        {"subscriber": subscriber, "error": error, "done": not error},
        status=400 if error else 200,
    )
