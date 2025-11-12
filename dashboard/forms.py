from django import forms

from .models import Location, LocationMessage


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
