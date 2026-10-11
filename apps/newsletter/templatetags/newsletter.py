from django import template

from ..forms import SubscribeForm

register = template.Library()


@register.inclusion_tag("newsletter/_signup.html")
def newsletter_signup(source="website", heading=True):
    return {"form": SubscribeForm(initial={"source": source}), "heading": heading}
