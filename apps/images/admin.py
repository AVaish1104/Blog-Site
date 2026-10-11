from django.contrib import admin

from .models import Image


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "width", "height", "file_size", "is_demo", "created_at")
    list_filter = ("is_demo",)
    search_fields = ("alt_text", "original_filename")
    readonly_fields = ("width", "height", "file_size", "uploaded_by", "created_at")
