from django.contrib import admin

from .models import Floor, FloorStatus, QuickNotice, TransZoneStatus


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ("display_name", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("display_name", "name")


@admin.register(FloorStatus)
class FloorStatusAdmin(admin.ModelAdmin):
    list_display = ("floor", "status", "redirect_to", "updated_at")
    list_filter = ("status",)
    autocomplete_fields = ("redirect_to",)


@admin.register(TransZoneStatus)
class TransZoneStatusAdmin(admin.ModelAdmin):
    list_display = ("status", "redirect_to", "updated_at")
    autocomplete_fields = ("redirect_to",)


@admin.register(QuickNotice)
class QuickNoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_active", "sort_order", "allow_note")
    list_editable = ("category", "is_active", "sort_order", "allow_note")
    list_filter = ("category", "is_active")
    search_fields = ("title", "body")
