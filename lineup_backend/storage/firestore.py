"""Firestore-backed store. Only imported when FIREBASE_CREDENTIALS is set."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from lineup_backend.storage.base import Collection, Mutator, Store

logger = logging.getLogger(__name__)


def _snapshot_to_doc(snapshot: Any) -> Dict[str, Any]:
    data = snapshot.to_dict() or {}
    data["id"] = snapshot.id
    return data


def _where(query: Any, field: str, value: Any) -> Any:
    try:
        from google.cloud.firestore_v1.base_query import FieldFilter

        return query.where(filter=FieldFilter(field, "==", value))
    except ImportError:  # older google-cloud-firestore
        return query.where(field, "==", value)


def _default_transactional() -> Callable[[Callable], Callable]:
    from google.cloud import firestore

    return firestore.transactional


class FirestoreCollection(Collection):
    def __init__(self, name: str, client: Any, transactional: Optional[Callable[[Callable], Callable]] = None) -> None:
        super().__init__(name)
        self._client = client
        self._ref = client.collection(name)
        self._transactional = transactional

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        query = self._ref
        for field, value in filters.items():
            query = _where(query, field, value)
        return [_snapshot_to_doc(snap) for snap in query.stream()]

    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        snap = self._ref.document(str(doc_id)).get()
        return _snapshot_to_doc(snap) if snap.exists else None

    def create(self, data: Dict[str, Any], doc_id: Optional[str] = None) -> Dict[str, Any]:
        payload = dict(data)
        payload.pop("id", None)
        if doc_id:
            self._ref.document(str(doc_id)).set(payload)
            return {**payload, "id": str(doc_id)}
        _, ref = self._ref.add(payload)
        return {**payload, "id": ref.id}

    def update(self, doc_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ref = self._ref.document(str(doc_id))
        if not ref.get().exists:
            return None
        payload = dict(patch)
        payload.pop("id", None)
        if payload:
            ref.update(payload)
        return _snapshot_to_doc(ref.get())

    def upsert(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(data)
        payload.pop("id", None)
        self._ref.document(str(doc_id)).set(payload)
        return {**payload, "id": str(doc_id)}

    def modify(self, doc_id: str, mutator: Mutator) -> Optional[Dict[str, Any]]:
        """Read-modify-write inside a Firestore transaction (retried on contention)."""
        ref = self._ref.document(str(doc_id))
        transactional = self._transactional or _default_transactional()

        @transactional
        def _run(transaction: Any) -> Optional[Dict[str, Any]]:
            snap = ref.get(transaction=transaction)
            current = _snapshot_to_doc(snap) if snap.exists else None
            patch = mutator(dict(current) if current is not None else None)
            if patch is None:
                return current
            payload = dict(patch)
            payload.pop("id", None)
            if snap.exists:
                if payload:
                    transaction.update(ref, payload)
            else:
                transaction.set(ref, payload)
            merged = dict(current or {})
            merged.update(payload)
            merged["id"] = str(doc_id)
            return merged

        return _run(self._client.transaction())

    def delete(self, doc_id: str) -> bool:
        ref = self._ref.document(str(doc_id))
        if not ref.get().exists:
            return False
        ref.delete()
        return True

    def count(self) -> int:
        return sum(1 for _ in self._ref.stream())

    def clear(self) -> None:
        for snap in self._ref.stream():
            snap.reference.delete()


def _init_firebase(credentials_json: str) -> Tuple[Any, Any]:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage

    info = json.loads(credentials_json)
    if not firebase_admin._apps:  # noqa: SLF001 - documented idempotency check
        firebase_admin.initialize_app(credentials.Certificate(info))
    client = firestore.client()
    bucket = None
    project_id = info.get("project_id")
    if project_id:
        try:
            bucket = storage.bucket(f"{project_id}.appspot.com")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Firebase Storage bucket unavailable: %s", exc)
    return client, bucket


class FirestoreStore(Store):
    kind = "firestore"

    def __init__(
        self,
        credentials_json: Optional[str] = None,
        client: Any = None,
        bucket: Any = None,
        transactional: Optional[Callable[[Callable], Callable]] = None,
    ) -> None:
        if client is None:
            if not credentials_json:
                raise ValueError("FIREBASE_CREDENTIALS is required for FirestoreStore")
            client, bucket = _init_firebase(credentials_json)
        self._client = client
        self.bucket = bucket
        self._transactional = transactional
        self._collections: Dict[str, FirestoreCollection] = {}

    def collection(self, name: str) -> FirestoreCollection:
        if name not in self._collections:
            self._collections[name] = FirestoreCollection(name, self._client, self._transactional)
        return self._collections[name]
