from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.blog.models import Post
from apps.blog.views import article_context
from apps.core.net import ip_hash
from apps.core.ratelimit import hit_for_request

from .forms import CommentForm

RATE_LIMIT = 5
RATE_PERIOD_SECONDS = 600


@require_POST
def submit_comment(request, slug):
    post = Post.objects.live().with_relations().filter(slug=slug).first()
    if post is None:
        raise Http404("No published post at this address.")
    if not post.comments_open:
        messages.error(request, "Comments are closed for this post.")
        return redirect(post)

    form = CommentForm(request.POST, post=post)
    if hit_for_request(request, "comment", RATE_LIMIT, RATE_PERIOD_SECONDS):
        form.add_error(None, "You've posted several comments recently. Please try again later.")
    elif form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.ip_hash = ip_hash(request)
        comment.user_agent = request.META.get("HTTP_USER_AGENT", "")[:300]
        comment.save()
        messages.success(
            request,
            "Thanks — your comment was received and will appear once it has been reviewed.",
        )
        return redirect(f"{post.get_absolute_url()}#comments")

    return render(request, "blog/post_detail.html", article_context(post, form), status=400)
