from django import forms

from .models import Location, LocationMessage, ThemeSettings


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ["is_closed"]
        widgets = {
            "is_closed": forms.CheckboxInput(attrs={"class": "toggle-input"}),
        }


class LocationMessageForm(forms.ModelForm):
    class Meta:
        model = LocationMessage
        fields = ["is_active", "is_important", "text"]
        widgets = {
            "is_active": forms.CheckboxInput(attrs={"class": "toggle-input"}),
            "is_important": forms.CheckboxInput(attrs={"class": "toggle-input"}),
            "text": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": "Wpisz komunikat",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["text"].required = False
        self.fields["is_important"].required = False

    def clean(self):
        cleaned = super().clean()
        text = cleaned.get("text", "")
        is_active = cleaned.get("is_active")
        is_important = cleaned.get("is_important")
        cleaned["text"] = text.strip()
        if (is_active or is_important) and not cleaned["text"]:
            self.add_error("text", "Wpisz treść komunikatu albo odznacz pole aktywacji.")
        return cleaned


class ThemeSettingsForm(forms.ModelForm):
    hex_color_fields = {
        "board_bg_top",
        "board_bg_bottom",
        "board_text_main",
        "board_text_muted",
        "board_accent",
        "board_important",
        "board_green_layer_start",
        "board_green_layer_end",
        "board_blue_layer_start",
        "board_blue_layer_end",
        "board_red_layer_start",
        "board_red_layer_end",
        "leader_bg_top",
        "leader_bg_bottom",
        "leader_text_main",
        "leader_button_from",
        "leader_button_to",
    }

    class Meta:
        model = ThemeSettings
        exclude = ["updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css_classes = ["theme-input"]
            if name in self.hex_color_fields:
                field.widget = forms.TextInput(attrs={"type": "color", "class": "theme-input"})
            else:
                field.widget.attrs.update({"placeholder": "rgba(...)"})
            field.widget.attrs.update({"class": " ".join(css_classes)})
