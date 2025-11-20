# StowBoard

StowBoard to prosta aplikacja Django wspierająca liderów działu STOW w magazynie. 
Pozwala szybko udostępniać pracownikom informacje o tym, na które piętra mają się 
udać, oraz czy mogą pobierać wózki ze strefy transu.

## Wymagania

- Python 3.11+
- Django 3.2.25 (patrz `requirements.txt`)
- pysqlite3-binary (dostarczany, aby zapewnić SQLite ≥ 3.9 w środowiskach ze
  starszą biblioteką systemową)

## Pierwsze uruchomienie

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # opcjonalnie, aby korzystać z panelu admina
python manage.py runserver
```

Aplikacja udostępnia dwa główne adresy URL:

- `/` – tablica informacyjna przeznaczona do wyświetlania na telewizorach.
- `/leader/` – panel lidera z formularzami do aktualizowania komunikatów.

W panelu lidera każda lokalizacja (TRANS, P1–P4) ma przycisk **Zamknięte** oraz listę zapamiętywanych
komunikatów. Możesz dodać kolejne pola, uzupełnić treść i zaznaczyć, które wiadomości mają pojawić się na
tablicy. Zmiana statusu na zamknięty powoduje, że na ekranie pracowniczym dana sekcja świeci się na czerwono
z napisem „Zamknięte”, w przeciwnym razie okienka są zielone. Dodatkowe lokalizacje lub modyfikacje możesz
przygotować z poziomu panelu admina (`/admin/`).

> Uwaga: gdy systemowa biblioteka SQLite jest starsza niż 3.9 (np. 3.7.x),
> automatycznie wczytywany jest moduł `pysqlite3` dostarczający nowszą wersję
> wymagane przez Django 3.2.
