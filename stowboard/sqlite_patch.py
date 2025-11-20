"""Provide an updated SQLite binding when the system SQLite is too old."""
import sys


def apply():
    """Replace the stdlib sqlite3 with pysqlite3 when available.

    Django 3.2 requires SQLite 3.9+. Some environments (e.g., older
    enterprise images) ship with SQLite 3.7.x, which triggers an
    ImproperlyConfigured error at startup. Installing ``pysqlite3-binary``
    supplies a modern SQLite build; we remap it here so Django imports the
    newer driver transparently.
    """

    try:  # pragma: no cover - exercised indirectly via settings
        import pysqlite3
    except ImportError:
        return

    sys.modules["sqlite3"] = sys.modules["pysqlite3"]
    sys.modules["sqlite3.dbapi2"] = sys.modules["pysqlite3.dbapi2"]


# Apply on import for modules that simply ``import stowboard.sqlite_patch``.
apply()
