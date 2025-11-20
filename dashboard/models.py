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


class ThemeSettings(models.Model):
    """Visual customization for the display board and leader panel."""

    # Board colors
    board_bg_top = models.CharField(max_length=20, default="#03102a")
    board_bg_bottom = models.CharField(max_length=20, default="#021a32")
    board_panel = models.CharField(max_length=30, default="rgba(10, 23, 41, 0.78)")
    board_text_main = models.CharField(max_length=20, default="#f4fff6")
    board_text_muted = models.CharField(max_length=20, default="#8ba0bf")
    board_accent = models.CharField(max_length=20, default="#54f6a2")
    board_important = models.CharField(max_length=20, default="#ff4b55")
    board_green_layer_start = models.CharField(max_length=20, default="#0c3a27")
    board_green_layer_end = models.CharField(max_length=20, default="#0f5f3d")
    board_green_inner_start = models.CharField(max_length=30, default="rgba(18, 69, 46, 0.95)")
    board_green_inner_end = models.CharField(max_length=30, default="rgba(8, 43, 29, 0.98)")
    board_blue_layer_start = models.CharField(max_length=20, default="#0b1f52")
    board_blue_layer_end = models.CharField(max_length=20, default="#123c84")
    board_blue_inner_start = models.CharField(max_length=30, default="rgba(16, 47, 104, 0.92)")
    board_blue_inner_end = models.CharField(max_length=30, default="rgba(9, 31, 74, 0.96)")
    board_red_layer_start = models.CharField(max_length=20, default="#61121a")
    board_red_layer_end = models.CharField(max_length=20, default="#b12332")
    board_red_inner_start = models.CharField(max_length=30, default="rgba(144, 26, 36, 0.95)")
    board_red_inner_end = models.CharField(max_length=30, default="rgba(82, 12, 18, 0.98)")

    # Leader panel colors
    leader_bg_top = models.CharField(max_length=20, default="#03102a")
    leader_bg_bottom = models.CharField(max_length=20, default="#021a32")
    leader_panel = models.CharField(max_length=40, default="rgba(10, 23, 41, 0.78)")
    leader_text_main = models.CharField(max_length=20, default="#f4fff6")
    leader_border = models.CharField(max_length=40, default="rgba(255, 255, 255, 0.18)")
    leader_card = models.CharField(max_length=40, default="rgba(5, 17, 32, 0.7)")
    leader_message_card = models.CharField(max_length=40, default="rgba(11, 29, 51, 0.75)")
    leader_input_bg = models.CharField(max_length=40, default="rgba(3, 14, 28, 0.8)")
    leader_input_border = models.CharField(max_length=40, default="rgba(255, 255, 255, 0.25)")
    leader_button_from = models.CharField(max_length=20, default="#1b8f64")
    leader_button_to = models.CharField(max_length=20, default="#2fd48c")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Theme settings"

    def __str__(self):  # pragma: no cover - human readable only
        return "Ustawienia wyglądu"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

class LocationMessage(models.Model):
    """Saved message for a location that can be toggled on and off."""

    location = models.ForeignKey(
        Location, related_name="messages", on_delete=models.CASCADE
    )
    text = models.TextField()
    is_active = models.BooleanField(default=False)
    is_important = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:  # pragma: no cover - human readable only
        return f"{self.location.name}: {self.text[:50]}"

    @property
    def display_text(self) -> str:
        return self.text.strip()
