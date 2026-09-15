"""Persistence layer.

One repository interface (:class:`Store` / :class:`Collection`) with two
implementations: in-memory (default) and Firestore (when ``FIREBASE_CREDENTIALS``
is set). Routes never touch either backend directly.
"""

from __future__ import annotations

import logging

from lineup_backend.config import AppConfig
from lineup_backend.storage.base import COLLECTIONS, Collection, Store
from lineup_backend.storage.memory import MemoryStore
from lineup_backend.storage.seed import seed_mock_data

logger = logging.getLogger(__name__)


def create_store(config: AppConfig) -> Store:
    """Build the configured store, falling back to memory if Firestore fails."""
    if config.has_firestore:
        try:
            from lineup_backend.storage.firestore import FirestoreStore

            store = FirestoreStore(config.firebase_credentials)
            logger.info("Storage: Firestore")
            return store
        except Exception as exc:  # noqa: BLE001 - any init failure must not take the API down
            logger.error("Firestore initialisation failed (%s: %s); using in-memory storage", type(exc).__name__, exc)
    logger.info("Storage: in-memory (data is lost on restart)")
    return MemoryStore()


__all__ = ["COLLECTIONS", "Collection", "Store", "MemoryStore", "create_store", "seed_mock_data"]
