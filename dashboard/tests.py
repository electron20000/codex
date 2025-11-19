from django.test import TestCase
from django.urls import reverse

from .models import Location, LocationMessage


class DisplayBoardTests(TestCase):
    def setUp(self):
        self.trans, _ = Location.objects.get_or_create(
            slug="trans", defaults={"name": "TRANS", "order": 0}
        )
        self.p1, _ = Location.objects.get_or_create(
            slug="p1", defaults={"name": "P1", "order": 1}
        )
        self.zones, _ = Location.objects.get_or_create(
            slug="strefy", defaults={"name": "STREFY", "order": 5}
        )
        LocationMessage.objects.create(
            location=self.trans,
            text="Test komunikat",
            is_active=True,
            is_important=True,
        )
        LocationMessage.objects.create(location=self.p1, text="Nieaktywny", is_active=False)

    def test_locations_render_in_order(self):
        response = self.client.get(reverse("display-board"))
        self.assertContains(response, "TRANS")
        self.assertContains(response, "P1")
        self.assertContains(response, "STREFY")
        # Active message visible, inactive one hidden
        self.assertContains(response, "Test komunikat")
        self.assertNotContains(response, "Nieaktywny")
        self.assertContains(response, "location-message--important")

    def test_closed_location_displays_closed_message(self):
        self.trans.is_closed = True
        self.trans.save()
        response = self.client.get(reverse("display-board"))
        self.assertContains(response, "Zamknięte")

    def test_board_data_endpoint_returns_updated_markup(self):
        response = self.client.get(reverse("board-data"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("Test komunikat", payload["html"])
        self.assertIsNotNone(payload["last_updated"])


class LeaderPanelTests(TestCase):
    def setUp(self):
        self.location, _ = Location.objects.get_or_create(
            slug="trans", defaults={"name": "TRANS", "order": 0}
        )

    def test_adds_message_via_formset(self):
        url = reverse("leader-panel")
        response = self.client.get(url)

        post_data = {}
        location_formset = response.context["location_formset"]
        for key, value in location_formset.management_form.initial.items():
            post_data[f"locations-{key}"] = str(value)

        for index, form in enumerate(location_formset.forms):
            post_data[f"locations-{index}-id"] = str(form.instance.pk or "")
            if form.instance.is_closed:
                post_data[f"locations-{index}-is_closed"] = "on"

        message_formsets = response.context["message_formsets"]
        trans_prefix = None
        for form, formset in message_formsets:
            prefix = formset.prefix
            if form.instance.pk == self.location.pk:
                trans_prefix = prefix
            for key, value in formset.management_form.initial.items():
                post_data[f"{prefix}-{key}"] = str(value)
            for i, message_form in enumerate(formset.forms):
                if message_form.instance.pk:
                    post_data[f"{prefix}-{i}-id"] = str(message_form.instance.pk)
                    post_data[f"{prefix}-{i}-text"] = message_form.instance.text
                    if message_form.instance.is_active:
                        post_data[f"{prefix}-{i}-is_active"] = "on"
                else:
                    post_data[f"{prefix}-{i}-text"] = ""
        assert trans_prefix is not None
        post_data[f"{trans_prefix}-0-text"] = "Nowy komunikat"
        post_data[f"{trans_prefix}-0-is_active"] = "on"
        post_data[f"{trans_prefix}-0-is_important"] = "on"

        response = self.client.post(url, data=post_data, follow=True)
        self.assertRedirects(response, url)
        self.assertTrue(LocationMessage.objects.filter(location=self.location).exists())
        message = LocationMessage.objects.get(location=self.location)
        self.assertTrue(message.is_active)
        self.assertTrue(message.is_important)
        self.assertEqual(message.display_text, "Nowy komunikat")
