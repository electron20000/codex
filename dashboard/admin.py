from django.contrib import admin

from .models import Location, LocationMessage


class LocationMessageInline(admin.TabularInline):
    model = LocationMessage
    extra = 0
    fields = ("text", "is_active", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "is_closed", "updated_at")
    list_editable = ("order", "is_closed")
    ordering = ("order", "id")
    search_fields = ("name", "slug")
    inlines = [LocationMessageInline]


@admin.register(LocationMessage)
class LocationMessageAdmin(admin.ModelAdmin):
    list_display = ("location", "short_text", "is_active", "created_at", "updated_at")
    list_filter = ("location", "is_active")
    search_fields = ("text",)
    ordering = ("location__order", "created_at", "id")

    @admin.display(description="Treść")
    def short_text(self, obj):
        return obj.display_text[:80]
