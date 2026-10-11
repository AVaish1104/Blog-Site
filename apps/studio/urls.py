from django.urls import path

from . import views

app_name = "studio"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("posts/", views.PostListView.as_view(), name="post_list"),
    path("posts/new/", views.PostCreateView.as_view(), name="post_create"),
    path("posts/preview/", views.PostPreviewView.as_view(), name="post_preview"),
    path("posts/<int:pk>/", views.PostUpdateView.as_view(), name="post_edit"),
    path(
        "posts/<int:pk>/preview/", views.PostSavedPreviewView.as_view(), name="post_saved_preview"
    ),
    path("posts/<int:pk>/publish/", views.PostPublishView.as_view(), name="post_publish"),
    path("posts/<int:pk>/unpublish/", views.PostUnpublishView.as_view(), name="post_unpublish"),
    path("posts/<int:pk>/delete/", views.PostDeleteView.as_view(), name="post_delete"),
    path("images/", views.ImageListView.as_view(), name="image_list"),
    path("images/<int:pk>/", views.ImageUpdateView.as_view(), name="image_edit"),
    path("images/<int:pk>/delete/", views.ImageDeleteView.as_view(), name="image_delete"),
    path("topics/", views.TaxonomyView.as_view(), name="taxonomy"),
    path("topics/<int:pk>/", views.CategoryUpdateView.as_view(), name="category_edit"),
    path("topics/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),
    path("tags/<int:pk>/", views.TagUpdateView.as_view(), name="tag_edit"),
    path("tags/<int:pk>/delete/", views.TagDeleteView.as_view(), name="tag_delete"),
    path("authors/", views.AuthorListView.as_view(), name="author_list"),
    path("authors/new/", views.AuthorEditView.as_view(), name="author_create"),
    path("authors/<int:pk>/", views.AuthorEditView.as_view(), name="author_edit"),
    path("authors/<int:pk>/delete/", views.AuthorDeleteView.as_view(), name="author_delete"),
    path("comments/", views.CommentListView.as_view(), name="comment_list"),
    path(
        "comments/<int:pk>/moderate/", views.CommentModerateView.as_view(), name="comment_moderate"
    ),
    path("subscribers/", views.SubscriberListView.as_view(), name="subscriber_list"),
    path("subscribers/export.csv", views.SubscriberExportView.as_view(), name="subscriber_export"),
    path(
        "subscribers/<int:pk>/delete/",
        views.SubscriberDeleteView.as_view(),
        name="subscriber_delete",
    ),
]
