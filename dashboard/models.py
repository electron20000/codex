from django.db import models


class Floor(models.Model):
    """Physical floor level where associates can stow carts."""

    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:  # pragma: no cover - human readable only
        return self.display_name


class FloorStatus(models.Model):
    """Represents the current instruction for a single floor."""

    class Status(models.TextChoices):
        WORK = "work", "Stowujcie tutaj"
        REDIRECT = "redirect", "Po zakończeniu przejdźcie dalej"
        HOLD = "hold", "Wstrzymajcie pracę"

    floor = models.OneToOneField(Floor, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WORK)
    redirect_to = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="redirected_from",
    )
    note = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["floor__order"]

    def __str__(self) -> str:  # pragma: no cover - human readable only
        return f"{self.floor.display_name}: {self.get_status_display()}"

    def display_message(self) -> str:
        if self.status == self.Status.WORK:
            base = f"{self.floor.display_name}: Stowujcie tutaj – wózki są dostępne."
        elif self.status == self.Status.REDIRECT:
            target = self.redirect_to.display_name if self.redirect_to else "inną lokalizację"
            base = (
                f"{self.floor.display_name}: Po zakończeniu wózków przejdźcie na {target}."
            )
        else:
            base = f"{self.floor.display_name}: Wstrzymajcie pracę i czekajcie na dalsze instrukcje."

        if self.note:
            return f"{base} {self.note.strip()}"
        return base


class TransZoneStatus(models.Model):
    """Communicates if carts can be picked directly from the trans zone."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Można pobierać wózki"
        RESTRICTED = "restricted", "Nie pobierać wózków"
        LIMITED = "limited", "Tylko wskazane osoby"

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    redirect_to = models.ForeignKey(
        Floor,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="trans_redirects",
    )
    note = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Status strefy transu"
        verbose_name_plural = "Statusy strefy transu"

    def __str__(self) -> str:  # pragma: no cover - human readable only
        return f"Trans: {self.get_status_display()}"

    def display_message(self) -> str:
        if self.status == self.Status.AVAILABLE:
            base = "Strefa transu: można pobierać wózki bez ograniczeń."
        elif self.status == self.Status.RESTRICTED:
            target = self.redirect_to.display_name if self.redirect_to else "inne piętro"
            base = f"Strefa transu: nie pobierajcie wózków. Skierujcie się na {target}."
        else:
            target = self.redirect_to.display_name if self.redirect_to else "osoby upoważnione"
            base = (
                "Strefa transu: tylko wskazane osoby mogą pobierać wózki. "
                f"Pozostali kierują się na {target}."
            )

        if self.note:
            return f"{base} {self.note.strip()}"
        return base


class QuickNotice(models.Model):
    """Predefined notice that can be toggled on the leader panel."""

    class Category(models.TextChoices):
        GENERAL = "general", "Ogólne"
        TRAINING = "training", "Szkolenia"
        TRANS = "trans", "Strefa transu"

    slug = models.SlugField(max_length=50, unique=True)
    title = models.CharField(max_length=120)
    body = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    sort_order = models.PositiveIntegerField(default=0)
    allow_note = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self) -> str:  # pragma: no cover - human readable only
        return self.title

    def display_message(self) -> str:
        message = self.body.strip()
        if self.note:
            message = f"{message} {self.note.strip()}"
        return message
