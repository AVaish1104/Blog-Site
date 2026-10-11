from django.contrib import admin

from .models import Subscriber


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "status", "created_at", "confirmed_at")
    list_filter = ("status",)
    search_fields = ("email",)
    readonly_fields = ("consent_text", "consented_at", "ip_hash", "created_at")
