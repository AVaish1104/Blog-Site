from django.urls import path

from apps.comments.views import submit_comment

from . import views
from .feeds import LatestPostsAtomFeed, LatestPostsFeed

app_name = "blog"

urlpatterns = [
    path("", views.home, name="home"),
    path("posts/", views.post_list, name="post_list"),
    path("posts/<slug:slug>/", views.post_detail, name="post_detail"),
    path("posts/<slug:slug>/comments/", submit_comment, name="post_comment"),
    path("topics/", views.category_list, name="category_list"),
    path("topics/<slug:slug>/", views.category_detail, name="category_detail"),
    path("tags/", views.tag_list, name="tag_list"),
    path("tags/<slug:slug>/", views.tag_detail, name="tag_detail"),
    path("authors/<slug:slug>/", views.author_detail, name="author_detail"),
    path("search/", views.search, name="search"),
    path("feed/", LatestPostsFeed(), name="feed_rss"),
    path("feed/atom/", LatestPostsAtomFeed(), name="feed_atom"),
]
