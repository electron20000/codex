from .models import ThemeSettings


def theme_settings(request):
    """Expose theme settings to all templates."""

    return {"theme": ThemeSettings.load()}

