"""Repository interface implemented by the memory and Firestore stores."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

Mutator = Callable[[Optional[Dict[str, Any]]], Optional[Dict[str, Any]]]

COLLECTIONS = (
    "social_posts",
    "post_comments",
    "user_follows",
    "appointments",
    "barber_portfolios",
    "barber_reviews",
    "barber_availability",
    "barber_services",
    "client_notes",
    "subscription_packages",
    "client_subscriptions",
    "hair_trends",
    "users",
    "barber_profiles",
    "usage_events",
    "stripe_events",
)


class Collection(ABC):
    """A named set of JSON documents, each with a string ``id``."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        """Return documents matching all equality filters (insertion order)."""

    @abstractmethod
    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Return one document or None."""

    @abstractmethod
    def create(self, data: Dict[str, Any], doc_id: Optional[str] = None) -> Dict[str, Any]:
        """Insert a document (generating an id unless given) and return it."""

    @abstractmethod
    def update(self, doc_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Merge ``patch`` into an existing document; None if it does not exist."""

    @abstractmethod
    def upsert(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Replace or create the document with the given id."""

    @abstractmethod
    def delete(self, doc_id: str) -> bool:
        """Delete a document; True if it existed."""

    @abstractmethod
    def modify(self, doc_id: str, mutator: Mutator) -> Optional[Dict[str, Any]]:
        """Atomically read-modify-write one document.

        ``mutator`` receives a copy of the current document (or ``None``) and
        returns a patch to merge (creating the document when it did not exist)
        or ``None`` to leave it untouched. Exceptions raised by the mutator
        abort the write and propagate. Returns the resulting document.
        """

    @abstractmethod
    def count(self) -> int:
        """Number of documents."""

    @abstractmethod
    def clear(self) -> None:
        """Remove every document (tests / seeding)."""

    def find_one(self, **filters: Any) -> Optional[Dict[str, Any]]:
        items = self.list(**filters)
        return items[0] if items else None

    def claim(self, doc_id: str, data: Dict[str, Any]) -> bool:
        """Create the document only if it does not exist yet; True when we created it.

        Built on the atomic ``modify`` so two concurrent callers cannot both
        win (Stripe retries and duplicate webhook deliveries).
        """
        won = False

        def mutator(current: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            nonlocal won
            if current is not None:
                return None
            won = True
            return dict(data)

        self.modify(doc_id, mutator)
        return won


class Store(ABC):
    """Factory for collections. Attribute access (``store.appointments``) is supported."""

    kind: str = "abstract"

    @abstractmethod
    def collection(self, name: str) -> Collection:
        """Return the collection with the given name."""

    def __getattr__(self, name: str) -> Collection:
        if name in COLLECTIONS:
            return self.collection(name)
        raise AttributeError(name)

    def reset(self) -> None:
        for name in COLLECTIONS:
            self.collection(name).clear()

    def counts(self) -> Dict[str, int]:
        return {name: self.collection(name).count() for name in COLLECTIONS}
