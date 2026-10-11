"""Keep the search index in step with posts, tags and categories."""

from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete
from django.dispatch import receiver

from apps.blog.models import Category, Post, Tag

from .backends import get_backend


def _reindex(post_id):
    def run():
        post = (
            Post.objects.select_related("category")
            .prefetch_related("tags")
            .filter(pk=post_id)
            .first()
        )
        if post:
            get_backend().index(post)

    transaction.on_commit(run)


@receiver(post_save, sender=Post)
def index_saved_post(sender, instance, raw=False, **kwargs):
    if not raw:
        _reindex(instance.pk)


@receiver(m2m_changed, sender=Post.tags.through)
def index_tag_changes(sender, instance, action, reverse, pk_set, **kwargs):
    if action not in {"post_add", "post_remove", "post_clear"}:
        return
    if reverse:
        for post_id in pk_set or []:
            _reindex(post_id)
    else:
        _reindex(instance.pk)


@receiver(post_delete, sender=Post)
def remove_deleted_post(sender, instance, **kwargs):
    post_id = instance.pk
    transaction.on_commit(lambda: get_backend().remove(post_id))


@receiver(post_save, sender=Category)
@receiver(post_save, sender=Tag)
def reindex_related_posts(sender, instance, raw=False, created=False, **kwargs):
    if raw or created:
        return
    for post_id in instance.posts.values_list("pk", flat=True):
        _reindex(post_id)


@receiver(pre_delete, sender=Category)
@receiver(pre_delete, sender=Tag)
def reindex_posts_losing_a_term(sender, instance, **kwargs):
    # Collected before the delete; _reindex runs on commit, after the relation is gone.
    for post_id in list(instance.posts.values_list("pk", flat=True)):
        _reindex(post_id)
