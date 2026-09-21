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


class PersistentStoreRequired(RuntimeError):
    """Raised at startup when production would otherwise run on the in-memory store."""


def create_store(config: AppConfig) -> Store:
    """Build the configured store.

    Outside production a Firestore failure falls back to memory so local work
    keeps going. In production that fallback is refused: users would pay for
    credits that disappear on the next deploy (``LINEUP_ALLOW_MEMORY_STORE``
    overrides this for throwaway demos).
    """
    if config.has_firestore:
        try:
            from lineup_backend.storage.firestore import FirestoreStore

            store = FirestoreStore(config.firebase_credentials)
            logger.info("Storage: Firestore")
            return store
        except Exception as exc:  # noqa: BLE001 - decide below whether the failure is fatal
            if config.require_persistent_store:
                raise PersistentStoreRequired(
                    f"Firestore initialisation failed ({type(exc).__name__}: {exc}). Refusing to start production on the "
                    "in-memory store: purchases would be lost on restart. Fix FIREBASE_CREDENTIALS, or set "
                    "LINEUP_ALLOW_MEMORY_STORE=true for a throwaway demo."
                ) from exc
            logger.error("Firestore initialisation failed (%s: %s); using in-memory storage", type(exc).__name__, exc)
    elif config.require_persistent_store:
        raise PersistentStoreRequired(
            "FIREBASE_CREDENTIALS is not set. Production needs Firestore so credits bought through Stripe survive a "
            "restart; set it, or set LINEUP_ALLOW_MEMORY_STORE=true for a throwaway demo."
        )
    logger.info("Storage: in-memory (data is lost on restart)")
    return MemoryStore()


__all__ = ["COLLECTIONS", "Collection", "Store", "MemoryStore", "PersistentStoreRequired", "create_store", "seed_mock_data"]
