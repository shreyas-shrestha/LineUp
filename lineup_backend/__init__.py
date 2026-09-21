"""LineUp backend package.

The Flask application is built by :func:`create_app` (see ``factory.py``).
Domain modules live in ``routes/`` (HTTP), ``services/`` (external APIs and
business logic) and ``storage/`` (persistence behind one repository interface).
"""

__version__ = "3.2.0"

from lineup_backend.factory import create_app  # noqa: E402

__all__ = ["create_app", "__version__"]
