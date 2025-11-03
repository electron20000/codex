from django.contrib import messages
from django.forms import modelformset_factory
from django.shortcuts import redirect, render

from .forms import FloorStatusForm, QuickNoticeForm, TransZoneStatusForm
from .models import FloorStatus, QuickNotice, TransZoneStatus


def display_board(request):
    floor_statuses = (
        FloorStatus.objects.select_related("floor", "redirect_to")
        .filter(floor__is_active=True)
        .order_by("floor__order")
    )
    trans_status = TransZoneStatus.objects.first()
    active_notices = QuickNotice.objects.filter(is_active=True).order_by("sort_order")

    context = {
        "floor_statuses": floor_statuses,
        "trans_status": trans_status,
        "active_notices": active_notices,
    }
    return render(request, "dashboard/display_board.html", context)


def leader_panel(request):
    floor_queryset = (
        FloorStatus.objects.select_related("floor", "redirect_to")
        .filter(floor__is_active=True)
        .order_by("floor__order")
    )
    FloorStatusFormSet = modelformset_factory(
        FloorStatus,
        form=FloorStatusForm,
        extra=0,
    )

    QuickNoticeFormSet = modelformset_factory(
        QuickNotice,
        form=QuickNoticeForm,
        extra=0,
    )

    trans_status = TransZoneStatus.objects.first()
    if trans_status is None:
        trans_status = TransZoneStatus.objects.create()

    if request.method == "POST":
        floor_formset = FloorStatusFormSet(
            request.POST, queryset=floor_queryset, prefix="floors"
        )
        trans_form = TransZoneStatusForm(request.POST, instance=trans_status, prefix="trans")
        notice_formset = QuickNoticeFormSet(
            request.POST,
            queryset=QuickNotice.objects.order_by("sort_order"),
            prefix="notices",
        )

        if floor_formset.is_valid() and trans_form.is_valid() and notice_formset.is_valid():
            floor_formset.save()
            trans_form.save()
            notice_formset.save()
            messages.success(request, "Komunikaty zostały zaktualizowane.")
            return redirect("leader-panel")
    else:
        floor_formset = FloorStatusFormSet(queryset=floor_queryset, prefix="floors")
        trans_form = TransZoneStatusForm(instance=trans_status, prefix="trans")
        notice_formset = QuickNoticeFormSet(
            queryset=QuickNotice.objects.order_by("sort_order"), prefix="notices"
        )

    notice_groups = []
    for form in notice_formset.forms:
        label = form.instance.get_category_display()
        if notice_groups and notice_groups[-1][0] == label:
            notice_groups[-1][1].append(form)
        else:
            notice_groups.append([label, [form]])

    context = {
        "floor_formset": floor_formset,
        "trans_form": trans_form,
        "notice_formset": notice_formset,
        "notice_forms_by_category": notice_groups,
    }
    return render(request, "dashboard/leader_panel.html", context)
