from django.contrib import messages
from django.db import transaction
from django.db.models import Max, Prefetch
from django.forms import inlineformset_factory, modelformset_factory
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from .forms import LocationForm, LocationMessageForm
from .models import Location, LocationMessage


def _board_state():
    message_prefetch = Prefetch(
        "messages",
        queryset=LocationMessage.objects.order_by("created_at", "id"),
    )
    locations = list(
        Location.objects.order_by("order", "id").prefetch_related(message_prefetch)
    )
    last_location_update = Location.objects.aggregate(last=Max("updated_at"))
    last_message_update = LocationMessage.objects.aggregate(last=Max("updated_at"))
    timestamps = [
        value
        for value in (
            last_location_update.get("last"),
            last_message_update.get("last"),
        )
        if value is not None
    ]
    last_updated = max(timestamps) if timestamps else None
    return locations, last_updated


def display_board(request):
    locations, last_updated = _board_state()
    context = {
        "locations": locations,
        "last_updated": last_updated,
    }
    return render(request, "dashboard/display_board.html", context)


def board_data(request):
    locations, last_updated = _board_state()
    html = render_to_string(
        "dashboard/partials/location_cards.html",
        {"locations": locations},
        request=request,
    )
    payload = {
        "html": html,
        "last_updated": timezone.localtime(last_updated).isoformat()
        if last_updated
        else None,
    }
    return JsonResponse(payload)


def leader_panel(request):
    locations = list(Location.objects.order_by("order", "id"))
    LocationFormSet = modelformset_factory(Location, form=LocationForm, extra=0)
    MessageFormSet = inlineformset_factory(
        Location,
        LocationMessage,
        form=LocationMessageForm,
        extra=1,
        can_delete=True,
    )

    location_formset = LocationFormSet(
        request.POST or None,
        queryset=Location.objects.order_by("order", "id"),
        prefix="locations",
    )

    message_formsets = {}
    for location in locations:
        message_formsets[location.pk] = MessageFormSet(
            request.POST or None,
            instance=location,
            prefix=f"messages-{location.pk}",
        )

    paired_forms = [
        (form, message_formsets.get(form.instance.pk)) for form in location_formset.forms
    ]

    if request.method == "POST":
        all_valid = location_formset.is_valid()
        for formset in message_formsets.values():
            all_valid = all_valid and formset.is_valid()

        if all_valid:
            with transaction.atomic():
                location_formset.save()
                for location in locations:
                    formset = message_formsets[location.pk]
                    saved_messages = formset.save(commit=False)
                    for obj in formset.deleted_objects:
                        obj.delete()
                    for message in saved_messages:
                        message.location = location
                        message.save()
            messages.success(request, "Komunikaty zostały zaktualizowane.")
            return redirect("leader-panel")

    grouped_forms = {"primary": [], "zones": []}
    for form, formset in paired_forms:
        if form.instance.slug == "strefy":
            grouped_forms["zones"].append((form, formset))
        else:
            grouped_forms["primary"].append((form, formset))

    context = {
        "location_formset": location_formset,
        "message_formsets": paired_forms,
        "grouped_forms": grouped_forms,
    }
    return render(request, "dashboard/leader_panel.html", context)
