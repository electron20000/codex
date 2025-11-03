from django import forms

from .models import Floor, FloorStatus, QuickNotice, TransZoneStatus


class FloorStatusForm(forms.ModelForm):
    class Meta:
        model = FloorStatus
        fields = ["status", "redirect_to", "note"]
        widgets = {
            "status": forms.RadioSelect,
            "note": forms.TextInput(attrs={"placeholder": "Dodatkowa informacja"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Floor.objects.filter(is_active=True)
        if self.instance and self.instance.floor_id:
            queryset = queryset.exclude(pk=self.instance.floor_id)
        self.fields["redirect_to"].queryset = queryset
        self.fields["redirect_to"].empty_label = "– wybierz piętro –"

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        redirect_to = cleaned.get("redirect_to")
        note = cleaned.get("note", "")

        if status == FloorStatus.Status.REDIRECT and not redirect_to:
            self.add_error(
                "redirect_to",
                "Wybierz piętro, na które mają przejść pracownicy.",
            )
        if redirect_to and self.instance and redirect_to == self.instance.floor:
            self.add_error("redirect_to", "Piętro docelowe musi być inne niż aktualne.")
        if status != FloorStatus.Status.REDIRECT:
            cleaned["redirect_to"] = None
        cleaned["note"] = note.strip()
        return cleaned


class TransZoneStatusForm(forms.ModelForm):
    class Meta:
        model = TransZoneStatus
        fields = ["status", "redirect_to", "note"]
        widgets = {
            "status": forms.RadioSelect,
            "note": forms.TextInput(attrs={"placeholder": "Dodatkowa informacja"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["redirect_to"].queryset = Floor.objects.filter(is_active=True)
        self.fields["redirect_to"].empty_label = "– wybierz piętro –"

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        redirect_to = cleaned.get("redirect_to")
        note = cleaned.get("note", "")

        if status in {TransZoneStatus.Status.RESTRICTED, TransZoneStatus.Status.LIMITED} and not redirect_to:
            self.add_error("redirect_to", "Wybierz piętro, na które mają kierować się pracownicy.")
        if status == TransZoneStatus.Status.AVAILABLE:
            cleaned["redirect_to"] = None
        cleaned["note"] = note.strip()
        return cleaned


class QuickNoticeForm(forms.ModelForm):
    class Meta:
        model = QuickNotice
        fields = ["is_active", "note"]
        widgets = {
            "note": forms.TextInput(attrs={"placeholder": "Uzupełnij treść"}),
        }

    def clean(self):
        cleaned = super().clean()
        note = cleaned.get("note", "")
        if note and not self.instance.allow_note:
            self.add_error("note", "Ten komunikat nie pozwala na dodatkową notatkę.")
        if not cleaned.get("is_active"):
            cleaned["note"] = ""
        else:
            cleaned["note"] = note.strip()
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["note"].required = False
        if not self.instance.allow_note:
            self.fields["note"].widget = forms.HiddenInput()
