"""Database abstraction layer for LineUp backend."""

from lineup_backend.db.firestore_client import FirestoreClient, get_firestore_client
from lineup_backend.db.repository import BaseRepository

__all__ = [
    "FirestoreClient",
    "get_firestore_client",
    "BaseRepository",
]
