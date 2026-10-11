from django.contrib import admin

from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author_name", "post", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("author_name", "author_email", "body")
    readonly_fields = ("ip_hash", "user_agent", "created_at", "moderated_at", "moderated_by")
