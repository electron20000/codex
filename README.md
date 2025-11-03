# StowBoard

StowBoard to prosta aplikacja Django wspierająca liderów działu STOW w magazynie. 
Pozwala szybko udostępniać pracownikom informacje o tym, na które piętra mają się 
udać, oraz czy mogą pobierać wózki ze strefy transu.

## Wymagania

- Python 3.11+
- Django 4.2.7 (patrz `requirements.txt`)

## Pierwsze uruchomienie

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # opcjonalnie, aby korzystać z panelu admina
python manage.py runserver
```

Aplikacja udostępnia dwa główne adresy URL:

- `/` – tablica informacyjna przeznaczona do wyświetlania na telewizorach.
- `/leader/` – panel lidera z gotowymi formularzami do aktualizowania komunikatów.

W razie potrzeby dodatkowych komunikatów lub pięter można je skonfigurować w panelu admina (`/admin/`).
