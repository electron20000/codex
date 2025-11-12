from django.db import models


class Location(models.Model):
    """A place where instructions should be displayed (TRANS or specific floor)."""

    slug = models.SlugField(max_length=20, unique=True)
    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)
    is_closed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:  # pragma: no cover - human readable only
        return self.name

    @property
    def active_messages(self):
        return self.messages.filter(is_active=True).order_by("created_at", "id")


class LocationMessage(models.Model):
    """Saved message for a location that can be toggled on and off."""

    location = models.ForeignKey(
        Location, related_name="messages", on_delete=models.CASCADE
    )
    text = models.TextField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:  # pragma: no cover - human readable only
        return f"{self.location.name}: {self.text[:50]}"

    @property
    def display_text(self) -> str:
        return self.text.strip()
