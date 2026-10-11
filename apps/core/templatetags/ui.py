import json

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

_JSON_ESCAPES = {ord("<"): "\\u003C", ord(">"): "\\u003E", ord("&"): "\\u0026"}


@register.filter
def absolute_url(value):
    """Turn a site-relative URL into an absolute one using SITE_URL."""
    if not value:
        return ""
    value = str(value)
    if value.startswith(("http://", "https://")):
        return value
    return f"{settings.SITE_URL}{value if value.startswith('/') else '/' + value}"


@register.filter
def widget(field, extra_class=""):
    """
    Render a bound field's widget with accessible attributes: aria-describedby
    pointing at its help text and error list, and aria-invalid when it has errors.
    """
    attrs = {}
    described = []
    if field.help_text:
        described.append(f"{field.auto_id}_helptext")
    if field.errors:
        described.append(f"{field.auto_id}_errors")
        attrs["aria-invalid"] = "true"
    if described:
        attrs["aria-describedby"] = " ".join(described)
    if extra_class:
        attrs["class"] = extra_class
    return field.as_widget(attrs=attrs)


@register.simple_tag
def jsonld(data):
    payload = json.dumps(data, ensure_ascii=False).translate(_JSON_ESCAPES)
    return mark_safe(f'<script type="application/ld+json">{payload}</script>')  # noqa: S308


@register.simple_tag(takes_context=True)
def nav_current(context, *url_names):
    match = getattr(context.get("request"), "resolver_match", None)
    if match and match.view_name in url_names:
        return mark_safe(' aria-current="page"')
    return ""


@register.filter
def initial(value):
    value = str(value or "").strip()
    return value[:1].upper() if value else "?"
