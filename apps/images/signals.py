from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Image


@receiver(post_delete, sender=Image)
def delete_file_with_image(sender, instance, **kwargs):
    """Remove the stored file once the database row is gone (after commit)."""
    if instance.file:
        storage, name = instance.file.storage, instance.file.name
        transaction.on_commit(lambda: storage.delete(name))
