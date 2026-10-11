"""
Studio access control. Every studio view goes through EditorRequiredMixin:
anonymous visitors are sent to sign in, signed-in users without the
`blog.manage_publication` permission get a 403. Nothing is executed first.
"""

from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied

EDITOR_GROUP = "Editors"
EDITOR_PERMISSION = "blog.manage_publication"


def is_editor(user):
    return bool(
        user and user.is_authenticated and user.is_active and user.has_perm(EDITOR_PERMISSION)
    )


class EditorRequiredMixin(AccessMixin):
    raise_exception = False

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not is_editor(request.user):
            raise PermissionDenied("Editor access required.")
        return super().dispatch(request, *args, **kwargs)


def ensure_editor_group():
    group, _ = Group.objects.get_or_create(name=EDITOR_GROUP)
    app_label, codename = EDITOR_PERMISSION.split(".")
    permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
    group.permissions.add(permission)
    return group
