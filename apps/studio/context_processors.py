from .access import is_editor


def studio(request):
    """Sidebar badge counts — only computed for editors on studio pages."""
    match = getattr(request, "resolver_match", None)
    if not match or match.namespace != "studio" or not is_editor(request.user):
        return {}
    from apps.comments.models import Comment

    return {"studio_pending_comments": Comment.objects.pending().count()}
