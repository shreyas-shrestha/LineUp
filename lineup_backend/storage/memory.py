"""Thread-safe in-memory store. Documents are copied in and out so callers
cannot mutate stored state by accident."""

from __future__ import annotations

import threading
import uuid
from copy import deepcopy
from typing import Any, Dict, List, Optional

from lineup_backend.storage.base import Collection, Mutator, Store


class MemoryCollection(Collection):
    def __init__(self, name: str, lock: threading.RLock) -> None:
        super().__init__(name)
        self._docs: Dict[str, Dict[str, Any]] = {}
        self._lock = lock

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                deepcopy(doc)
                for doc in self._docs.values()
                if all(doc.get(key) == value for key, value in filters.items())
            ]

    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            doc = self._docs.get(str(doc_id))
            return deepcopy(doc) if doc is not None else None

    def create(self, data: Dict[str, Any], doc_id: Optional[str] = None) -> Dict[str, Any]:
        new_id = str(doc_id or uuid.uuid4())
        doc = deepcopy(data)
        doc["id"] = new_id
        with self._lock:
            self._docs[new_id] = doc
        return deepcopy(doc)

    def update(self, doc_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            doc = self._docs.get(str(doc_id))
            if doc is None:
                return None
            doc.update(deepcopy(patch))
            doc["id"] = str(doc_id)
            return deepcopy(doc)

    def upsert(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        doc = deepcopy(data)
        doc["id"] = str(doc_id)
        with self._lock:
            self._docs[str(doc_id)] = doc
        return deepcopy(doc)

    def modify(self, doc_id: str, mutator: Mutator) -> Optional[Dict[str, Any]]:
        key = str(doc_id)
        with self._lock:
            current = self._docs.get(key)
            patch = mutator(deepcopy(current) if current is not None else None)
            if patch is None:
                return deepcopy(current) if current is not None else None
            doc = current if current is not None else {}
            doc.update(deepcopy(patch))
            doc["id"] = key
            self._docs[key] = doc
            return deepcopy(doc)

    def delete(self, doc_id: str) -> bool:
        with self._lock:
            return self._docs.pop(str(doc_id), None) is not None

    def count(self) -> int:
        with self._lock:
            return len(self._docs)

    def clear(self) -> None:
        with self._lock:
            self._docs.clear()


class MemoryStore(Store):
    kind = "memory"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._collections: Dict[str, MemoryCollection] = {}
        self.bucket = None  # no blob storage in memory mode

    def collection(self, name: str) -> MemoryCollection:
        with self._lock:
            if name not in self._collections:
                self._collections[name] = MemoryCollection(name, self._lock)
            return self._collections[name]
