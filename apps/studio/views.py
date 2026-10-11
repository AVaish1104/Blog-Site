import csv
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, ProtectedError, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.blog.models import Author, Category, Post, Tag
from apps.blog.services import make_slug, publish_now, save_post, unpublish
from apps.comments.models import Comment
from apps.images.models import Image
from apps.images.services import create_image
from apps.newsletter.models import Subscriber
from apps.newsletter.services import unsubscribe_url

from .access import EditorRequiredMixin
from .forms import (
    AuthorForm,
    CategoryForm,
    ImageEditForm,
    ImageUploadForm,
    PostForm,
    TagForm,
)


def _safe_next(request, fallback):
    """Redirect target from POST 'next', only if it points at this site."""
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return fallback


def _redirect_back(request, pk):
    return redirect(_safe_next(request, reverse("studio:post_edit", args=[pk])))


# --- Dashboard ----------------------------------------------------------------


class DashboardView(EditorRequiredMixin, TemplateView):
    template_name = "studio/dashboard.html"

    def get_context_data(self, **kwargs):
        now = timezone.now()
        posts = Post.objects.all()
        live = posts.live(now)
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "counts": {
                    "published": live.count(),
                    "scheduled": posts.scheduled(now).count(),
                    "drafts": posts.drafts().count(),
                    "pending_comments": Comment.objects.pending().count(),
                    "subscribers": Subscriber.objects.filter(
                        status=Subscriber.Status.ACTIVE
                    ).count(),
                    "pending_subscribers": Subscriber.objects.filter(
                        status=Subscriber.Status.PENDING
                    ).count(),
                },
                "recent": posts.select_related("author").order_by("-updated_at")[:6],
                "upcoming": posts.scheduled(now)
                .select_related("author")
                .order_by("published_at")[:5],
                "last_published": live.order_by("-published_at").first(),
                "needs_attention": live.filter(
                    Q(excerpt="") | Q(cover_image__isnull=True)
                ).order_by("-published_at")[:5],
                "demo_count": posts.filter(is_demo=True).count(),
            }
        )
        return context


# --- Posts --------------------------------------------------------------------


class PostListView(EditorRequiredMixin, ListView):
    template_name = "studio/post_list.html"
    paginate_by = 25
    context_object_name = "posts"

    STATES = [
        ("all", "All"),
        ("draft", "Drafts"),
        ("scheduled", "Scheduled"),
        ("published", "Published"),
    ]

    def get_queryset(self):
        queryset = Post.objects.select_related("author", "category").order_by("-updated_at")
        state = self.request.GET.get("state", "all")
        if state == "draft":
            queryset = queryset.drafts()
        elif state == "scheduled":
            queryset = queryset.scheduled()
        elif state == "published":
            queryset = queryset.live()
        query = self.request.GET.get("q", "").strip()[:100]
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(slug__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        context.update(
            {
                "state": self.request.GET.get("state", "all"),
                "query": self.request.GET.get("q", "").strip()[:100],
                "states": self.STATES,
                "filter_prefix": urlencode(
                    {
                        "state": self.request.GET.get("state", "all"),
                        "q": self.request.GET.get("q", "").strip()[:100],
                    }
                ),
                "state_counts": {
                    "all": Post.objects.count(),
                    "draft": Post.objects.drafts().count(),
                    "scheduled": Post.objects.scheduled(now).count(),
                    "published": Post.objects.live(now).count(),
                },
            }
        )
        return context


class PostEditMixin(EditorRequiredMixin):
    template_name = "studio/post_form.html"

    def get_post(self):
        return None

    def render_form(self, form, post, status=200):
        return render(
            self.request,
            self.template_name,
            {
                "form": form,
                "post": post,
                "tag_names": Tag.objects.values_list("name", flat=True),
                "images": Image.objects.all()[:60],
                "has_authors": Author.objects.exists(),
            },
            status=status,
        )

    def get(self, request, *args, **kwargs):
        post = self.get_post()
        initial = {}
        if post is None:
            initial = {"status": Post.Status.DRAFT, "allow_comments": True}
            own_author = getattr(request.user, "author_profile", None)
            if own_author:
                initial["author"] = own_author.pk
            elif Author.objects.count() == 1:
                initial["author"] = Author.objects.first().pk
        form = PostForm(instance=post, initial=initial)
        return self.render_form(form, post)

    def post(self, request, *args, **kwargs):
        post = self.get_post()
        form = PostForm(request.POST, request.FILES, instance=post)
        if not form.is_valid():
            messages.error(request, "The post wasn't saved. Please correct the errors below.")
            return self.render_form(form, post, status=400)

        with transaction.atomic():
            instance = form.save(commit=False)
            if form.cleaned_data.get("new_cover"):
                instance.cover_image = create_image(
                    form.cleaned_data["new_cover"],
                    form.cleaned_data["new_cover_alt"],
                    user=request.user,
                    processed=form.processed_cover,
                )
            save_post(
                instance,
                tag_names=form.cleaned_data["tags"],
                user=request.user,
                previous_slug=form.previous_slug,
            )

        verb = "created" if post is None else "saved"
        state = instance.state
        if state == "published":
            message = f"“{instance.title}” {verb} and live."
        elif state == "scheduled":
            when = timezone.localtime(instance.published_at).strftime("%d %b %Y at %H:%M")
            message = f"“{instance.title}” {verb} and scheduled for {when}."
        else:
            message = f"“{instance.title}” {verb} as a draft."
        messages.success(request, message)
        return redirect("studio:post_edit", pk=instance.pk)


class PostCreateView(PostEditMixin, View):
    pass


class PostUpdateView(PostEditMixin, View):
    def get_post(self):
        return get_object_or_404(Post, pk=self.kwargs["pk"])


class PostPreviewView(EditorRequiredMixin, View):
    """Render unsaved editor content with the public article template."""

    def post(self, request):
        post_id = request.POST.get("post_id")
        instance = get_object_or_404(Post, pk=post_id) if post_id else None
        form = PostForm(request.POST, instance=instance, preview=True)
        if not form.is_valid():
            return render(request, "studio/preview_error.html", {"form": form}, status=400)
        post = form.save(commit=False)
        post.render()
        if not post.published_at and post.status == Post.Status.PUBLISHED:
            post.published_at = timezone.now()
        tags = [
            Tag.objects.filter(name__iexact=name).first() or Tag(name=name, slug=make_slug(name))
            for name in form.cleaned_data["tags"]
        ]
        note = "unsaved changes shown with the public layout. Nothing has been saved."
        if request.FILES.get("new_cover"):
            note += " The newly chosen cover image appears after saving."
        return render(
            request,
            "blog/post_detail.html",
            {"post": post, "post_tags": tags, "preview": True, "preview_note": note},
        )


class PostSavedPreviewView(EditorRequiredMixin, View):
    def get(self, request, pk):
        post = get_object_or_404(Post.objects.with_relations(), pk=pk)
        return render(
            request,
            "blog/post_detail.html",
            {
                "post": post,
                "post_tags": list(post.tags.all()),
                "preview": True,
                "preview_note": f"saved version ({post.get_state_display().lower()}).",
            },
        )


class PostPublishView(EditorRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        if not post.body.strip():
            messages.error(request, "Add body text before publishing.")
        else:
            publish_now(post, request.user)
            messages.success(request, f"“{post.title}” is now live.")
        return _redirect_back(request, pk)


class PostUnpublishView(EditorRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        unpublish(post, request.user)
        messages.success(request, f"“{post.title}” was unpublished and is now a draft.")
        return _redirect_back(request, pk)


class PostDeleteView(EditorRequiredMixin, View):
    def get(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        return render(
            request,
            "studio/confirm_delete.html",
            {
                "object_label": f"the post “{post.title}”",
                "consequences": [
                    "The article will no longer be available at its address.",
                    f"{post.comments.count()} comment(s) on it will be deleted too.",
                    "This can't be undone.",
                ],
                "cancel_url": reverse("studio:post_edit", args=[pk]),
                "confirm_label": "Delete post",
            },
        )

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        title = post.title
        post.delete()
        messages.success(request, f"“{title}” was deleted.")
        return redirect("studio:post_list")


# --- Images -------------------------------------------------------------------


class ImageListView(EditorRequiredMixin, View):
    template_name = "studio/image_list.html"

    def render_page(self, form, status=200):
        return render(
            self.request,
            self.template_name,
            {"form": form, "images": Image.objects.select_related("uploaded_by")},
            status=status,
        )

    def get(self, request):
        return self.render_page(ImageUploadForm())

    def post(self, request):
        form = ImageUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "The image wasn't uploaded. Please correct the errors below.")
            return self.render_page(form, status=400)
        image = create_image(
            form.cleaned_data["file"],
            form.cleaned_data["alt_text"],
            user=request.user,
            processed=form.processed,
        )
        messages.success(request, f"Uploaded “{image.alt_text}” ({image.width}×{image.height}).")
        return redirect("studio:image_list")


class ImageUpdateView(EditorRequiredMixin, View):
    def get(self, request, pk):
        image = get_object_or_404(Image, pk=pk)
        return render(
            request,
            "studio/image_form.html",
            {"form": ImageEditForm(instance=image), "image": image},
        )

    def post(self, request, pk):
        image = get_object_or_404(Image, pk=pk)
        form = ImageEditForm(request.POST, instance=image)
        if form.is_valid():
            form.save()
            messages.success(request, "Alt text updated.")
            return redirect("studio:image_list")
        return render(request, "studio/image_form.html", {"form": form, "image": image}, status=400)


class ImageDeleteView(EditorRequiredMixin, View):
    def usage(self, image):
        covers = Post.objects.filter(cover_image=image).count()
        inline = Post.objects.filter(body__contains=image.file.name).count()
        return covers, inline

    def get(self, request, pk):
        image = get_object_or_404(Image, pk=pk)
        covers, inline = self.usage(image)
        consequences = []
        if covers:
            consequences.append(f"{covers} post(s) use it as a cover and will show no cover.")
        if inline:
            consequences.append(f"{inline} post(s) embed it in their text; it will be missing.")
        consequences.append("The file will be permanently removed. This can't be undone.")
        return render(
            request,
            "studio/confirm_delete.html",
            {
                "object_label": f"the image “{image.alt_text}”",
                "consequences": consequences,
                "cancel_url": reverse("studio:image_list"),
                "confirm_label": "Delete image",
                "preview_image": image,
            },
        )

    def post(self, request, pk):
        image = get_object_or_404(Image, pk=pk)
        image.delete()
        messages.success(request, "Image deleted.")
        return redirect("studio:image_list")


# --- Topics (categories) and tags ----------------------------------------------


class TaxonomyView(EditorRequiredMixin, View):
    template_name = "studio/taxonomy.html"

    def render_page(self, category_form=None, status=200):
        return render(
            self.request,
            self.template_name,
            {
                "category_form": category_form or CategoryForm(),
                "categories": Category.objects.annotate(n=Count("posts")),
                "tags": Tag.objects.annotate(n=Count("posts")).order_by("name"),
            },
            status=status,
        )

    def get(self, request):
        return self.render_page()

    def post(self, request):
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Topic “{category.name}” created.")
            return redirect("studio:taxonomy")
        messages.error(request, "The topic wasn't created. Please correct the errors below.")
        return self.render_page(form, status=400)


class SimpleEditView(EditorRequiredMixin, View):
    model = None
    form_class = None
    noun = ""
    success_url = reverse_lazy("studio:taxonomy")

    def page(self, form, obj, status=200):
        return render(
            self.request,
            "studio/simple_form.html",
            {"form": form, "object": obj, "noun": self.noun, "cancel_url": self.success_url},
            status=status,
        )

    def get(self, request, pk=None):
        obj = get_object_or_404(self.model, pk=pk) if pk else None
        return self.page(self.form_class(instance=obj), obj)

    def post(self, request, pk=None):
        obj = get_object_or_404(self.model, pk=pk) if pk else None
        form = self.form_class(request.POST, instance=obj)
        if form.is_valid():
            saved = form.save()
            messages.success(request, f"{self.noun.capitalize()} “{saved}” saved.")
            return redirect(self.success_url)
        messages.error(request, "Nothing was saved. Please correct the errors below.")
        return self.page(form, obj, status=400)


class CategoryUpdateView(SimpleEditView):
    model, form_class, noun = Category, CategoryForm, "topic"


class TagUpdateView(SimpleEditView):
    model, form_class, noun = Tag, TagForm, "tag"


class SimpleDeleteView(EditorRequiredMixin, View):
    model = None
    noun = ""
    success_url = reverse_lazy("studio:taxonomy")

    def consequences(self, obj):
        return ["This can't be undone."]

    def get(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        return render(
            request,
            "studio/confirm_delete.html",
            {
                "object_label": f"the {self.noun} “{obj}”",
                "consequences": self.consequences(obj),
                "cancel_url": self.success_url,
                "confirm_label": f"Delete {self.noun}",
            },
        )

    def post(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        label = str(obj)
        try:
            obj.delete()
        except ProtectedError:
            messages.error(request, f"“{label}” can't be deleted while posts still use it.")
            return redirect(self.success_url)
        messages.success(request, f"{self.noun.capitalize()} “{label}” deleted.")
        return redirect(self.success_url)


class CategoryDeleteView(SimpleDeleteView):
    model, noun = Category, "topic"

    def consequences(self, obj):
        n = obj.posts.count()
        return [f"{n} post(s) in this topic will become uncategorised.", "This can't be undone."]


class TagDeleteView(SimpleDeleteView):
    model, noun = Tag, "tag"

    def consequences(self, obj):
        n = obj.posts.count()
        return [f"The tag will be removed from {n} post(s).", "This can't be undone."]


# --- Authors ------------------------------------------------------------------


class AuthorListView(EditorRequiredMixin, ListView):
    template_name = "studio/author_list.html"
    context_object_name = "authors"

    def get_queryset(self):
        return Author.objects.select_related("user").annotate(n=Count("posts"))


class AuthorEditView(SimpleEditView):
    model, form_class, noun = Author, AuthorForm, "author"
    success_url = reverse_lazy("studio:author_list")


class AuthorDeleteView(SimpleDeleteView):
    model, noun = Author, "author"
    success_url = reverse_lazy("studio:author_list")

    def consequences(self, obj):
        n = obj.posts.count()
        if n:
            return [
                f"This author has {n} post(s). Reassign or delete them first — "
                "deletion will be refused while they exist."
            ]
        return ["The author's profile page will be removed.", "This can't be undone."]


# --- Comments -----------------------------------------------------------------


class CommentListView(EditorRequiredMixin, ListView):
    template_name = "studio/comment_list.html"
    context_object_name = "comments"
    paginate_by = 30

    def get_queryset(self):
        status = self.request.GET.get("status", Comment.Status.PENDING)
        queryset = Comment.objects.select_related("post").order_by("-created_at")
        if status in Comment.Status.values:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        counts = dict(Comment.objects.values_list("status").annotate(n=Count("pk")))
        context["status"] = self.request.GET.get("status", Comment.Status.PENDING)
        context["statuses"] = [
            (value, label, counts.get(value, 0)) for value, label in Comment.Status.choices
        ]
        context["all_count"] = sum(counts.values())
        return context


class CommentModerateView(EditorRequiredMixin, View):
    ACTIONS = {
        "approve": Comment.Status.APPROVED,
        "reject": Comment.Status.REJECTED,
        "spam": Comment.Status.SPAM,
        "pending": Comment.Status.PENDING,
    }

    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        action = request.POST.get("action")
        back = _safe_next(request, reverse("studio:comment_list"))
        if action == "delete":
            comment.delete()
            messages.success(request, "Comment deleted.")
        elif action in self.ACTIONS:
            comment.status = self.ACTIONS[action]
            comment.moderated_at = timezone.now()
            comment.moderated_by = request.user
            comment.save(update_fields=["status", "moderated_at", "moderated_by"])
            messages.success(
                request,
                f"Comment by {comment.author_name} marked "
                f"“{comment.get_status_display().lower()}”.",
            )
        else:
            messages.error(request, "Unknown moderation action.")
        return redirect(back)


# --- Subscribers --------------------------------------------------------------


class SubscriberListView(EditorRequiredMixin, ListView):
    template_name = "studio/subscriber_list.html"
    context_object_name = "subscribers"
    paginate_by = 50

    def get_queryset(self):
        queryset = Subscriber.objects.all()
        status = self.request.GET.get("status", "")
        if status in Subscriber.Status.values:
            queryset = queryset.filter(status=status)
        query = self.request.GET.get("q", "").strip()[:100]
        if query:
            queryset = queryset.filter(email__icontains=query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        counts = dict(Subscriber.objects.values_list("status").annotate(n=Count("pk")))
        context.update(
            {
                "status": self.request.GET.get("status", ""),
                "query": self.request.GET.get("q", "").strip()[:100],
                "statuses": [
                    (v, label, counts.get(v, 0)) for v, label in Subscriber.Status.choices
                ],
                "all_count": sum(counts.values()),
                "filter_prefix": urlencode(
                    {
                        "status": self.request.GET.get("status", ""),
                        "q": self.request.GET.get("q", "").strip()[:100],
                    }
                ),
                "email_delivery": settings.EMAIL_DELIVERY,
            }
        )
        return context


class SubscriberExportView(EditorRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        stamp = timezone.localtime().strftime("%Y%m%d")
        response["Content-Disposition"] = f'attachment; filename="subscribers-{stamp}.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ["email", "status", "subscribed_at", "confirmed_at", "consent_text", "unsubscribe_url"]
        )
        status = request.GET.get("status", Subscriber.Status.ACTIVE)
        queryset = Subscriber.objects.order_by("created_at")
        if status in Subscriber.Status.values:
            queryset = queryset.filter(status=status)
        for sub in queryset.iterator():
            # Prefix cells that spreadsheet apps would treat as formulas.
            email = "'" + sub.email if sub.email[:1] in "=+-@" else sub.email
            writer.writerow(
                [
                    email,
                    sub.status,
                    sub.created_at.isoformat(),
                    sub.confirmed_at.isoformat() if sub.confirmed_at else "",
                    sub.consent_text,
                    unsubscribe_url(sub),
                ]
            )
        return response


class SubscriberDeleteView(SimpleDeleteView):
    model, noun = Subscriber, "subscriber"
    success_url = reverse_lazy("studio:subscriber_list")

    def consequences(self, obj):
        return [
            "Their email address and consent record will be permanently erased.",
            "This can't be undone.",
        ]
