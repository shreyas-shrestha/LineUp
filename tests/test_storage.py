from typing import Any, Dict

import pytest

from lineup_backend.config import AppConfig
from lineup_backend.storage import COLLECTIONS, MemoryStore, create_store, seed_mock_data
from lineup_backend.storage.firestore import FirestoreStore
from tests.conftest import make_app


def test_memory_collection_crud():
    store = MemoryStore()
    posts = store.social_posts
    created = posts.create({"caption": "a", "barberId": "x"})
    assert created["id"] and posts.get(created["id"])["caption"] == "a"
    posts.create({"caption": "b", "barberId": "y"}, doc_id="fixed")
    assert [p["caption"] for p in posts.list(barberId="y")] == ["b"]
    assert posts.update("fixed", {"caption": "c"})["caption"] == "c"
    assert posts.update("missing", {"caption": "c"}) is None
    assert posts.upsert("fixed", {"caption": "d"}) == {"caption": "d", "id": "fixed"}
    assert posts.find_one(caption="d")["id"] == "fixed"
    assert posts.count() == 2 and posts.delete("fixed") is True and posts.delete("fixed") is False
    posts.clear()
    assert posts.count() == 0
    assert set(store.counts()) == set(COLLECTIONS)
    assert {"users", "usage_events", "stripe_events", "barber_profiles"} <= set(COLLECTIONS)


def test_memory_modify_is_atomic_and_can_create_or_abort():
    store = MemoryStore()
    users = store.users
    users.create({"credits": 3}, doc_id="u1")
    assert users.modify("u1", lambda cur: {"credits": cur["credits"] - 1})["credits"] == 2
    assert users.get("u1")["credits"] == 2
    # None leaves the document untouched; a mutator may create a missing document.
    assert users.modify("u1", lambda cur: None)["credits"] == 2
    assert users.modify("new", lambda cur: {"credits": 9} if cur is None else None) == {"credits": 9, "id": "new"}
    assert users.modify("ghost", lambda cur: None) is None

    def fail(cur):
        raise ValueError("short")

    with pytest.raises(ValueError):
        users.modify("u1", fail)
    assert users.get("u1")["credits"] == 2


def test_memory_store_copies_documents():
    store = MemoryStore()
    doc = store.appointments.create({"barberNotes": []})
    doc["barberNotes"].append("mutated")
    assert store.appointments.get(doc["id"])["barberNotes"] == []


def test_seed_is_idempotent_and_creates_dev_accounts():
    store = MemoryStore()
    assert seed_mock_data(store) is True
    assert seed_mock_data(store) is False
    assert store.social_posts.count() == 2 and store.barber_reviews.count() == 4
    assert store.users.get("client_1")["role"] == "client" and store.users.get("client_1")["credits"] == 3
    assert store.users.get("barber_1")["role"] == "barber"
    assert store.barber_profiles.get("barber_1")["name"] == "Mike's Cuts"
    assert len(store.barber_services.list(barberId="barber_1")) == 3
    assert store.social_posts.get("2")["likedBy"] == ["client_1"]


def test_seed_policy_from_config():
    assert AppConfig(env="development").should_seed is True
    assert AppConfig(env="development", firebase_credentials="{}").should_seed is False
    assert AppConfig(env="production").should_seed is False
    assert AppConfig(env="production", seed_mock_data=True).should_seed is True
    assert make_app(seed_mock_data=False).extensions["lineup"].store.social_posts.count() == 0


def test_create_store_falls_back_to_memory_on_bad_credentials_outside_production():
    store = create_store(AppConfig(env="development", firebase_credentials="not json"))
    assert store.kind == "memory"


def test_config_from_env_and_redaction(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-secret")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_secret")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_secret")
    monkeypatch.setenv("LINEUP_DEV_SECRET", "dev-secret")
    monkeypatch.setenv("FIREBASE_WEB_CONFIG", '{"apiKey": "pub", "projectId": "p", "extra": "dropped", "appId": 5}')
    monkeypatch.setenv("STRIPE_PRICE_PLUS", "price_plus")
    monkeypatch.setenv("MAX_TRYON_PER_DAY_PER_USER", "4")
    monkeypatch.setenv("LINEUP_ALLOWED_ORIGINS", "https://a.example, https://b.example")
    monkeypatch.setenv("LINEUP_RATE_AI", "3 per minute")
    monkeypatch.setenv("LINEUP_SEED_MOCK_DATA", "true")
    monkeypatch.setenv("FLASK_ENV", "production")
    cfg = AppConfig.from_env(port=6000)
    assert cfg.gemini_api_key == "sk-secret" and cfg.port == 6000
    assert cfg.allowed_origins == ["https://a.example", "https://b.example"]
    assert cfg.rate_limits["ai"] == "3 per minute" and cfg.seed_mock_data is True
    assert cfg.has_stripe and cfg.stripe_price_ids()["plus"] == "price_plus" and cfg.stripe_price_ids()["starter"] is None
    assert cfg.daily_caps == {"analysis": 20, "tryon": 4, "barber_search": 40}
    assert cfg.firebase_web() == {"apiKey": "pub", "projectId": "p"}
    assert cfg.charge_for_mock is False and cfg.dev_login_enabled is False
    redacted = cfg.redacted()
    assert redacted["gemini_api_key"] == "***" and redacted["stripe_secret_key"] == "***"
    assert redacted["stripe_webhook_secret"] == "***" and redacted["dev_secret"] == "***" and redacted["firebase_web_config"] == "***"
    for secret in ("sk-secret", "sk_test_secret", "whsec_secret", "dev-secret"):
        assert secret not in str(redacted)
    assert cfg.configured_integrations()["stripe"] is True and cfg.configured_integrations()["firebase_auth"] is False


def test_meter_mock_defaults_by_environment():
    assert AppConfig(env="development").charge_for_mock is True
    assert AppConfig(env="testing").charge_for_mock is True
    assert AppConfig(env="production").charge_for_mock is False
    assert AppConfig(env="production", meter_mock=True).charge_for_mock is True
    assert AppConfig(env="development", meter_mock=False).charge_for_mock is False


# --- Firestore implementation against an in-memory fake client ---------------


class _Snapshot:
    def __init__(self, doc_id: str, data: Any, reference: "_DocRef"):
        self.id = doc_id
        self._data = data
        self.reference = reference
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class _DocRef:
    def __init__(self, collection: "_Collection", doc_id: str):
        self._collection = collection
        self.id = doc_id

    def get(self, transaction=None):
        return _Snapshot(self.id, self._collection.docs.get(self.id), self)

    def set(self, data):
        self._collection.docs[self.id] = dict(data)

    def update(self, patch):
        self._collection.docs[self.id].update(patch)

    def delete(self):
        self._collection.docs.pop(self.id, None)


class _Transaction:
    def __init__(self):
        self.ops = []

    def update(self, ref, patch):
        self.ops.append("update")
        ref.update(patch)

    def set(self, ref, data):
        self.ops.append("set")
        ref.set(data)


class _Query:
    def __init__(self, collection: "_Collection", filters=()):
        self._collection = collection
        self._filters = filters

    def where(self, *args, **kwargs):
        flt = kwargs.get("filter")
        field, value = (flt.field_path, flt.value) if flt is not None else (args[0], args[2])
        return _Query(self._collection, self._filters + ((field, value),))

    def stream(self):
        for doc_id, data in list(self._collection.docs.items()):
            if all(data.get(f) == v for f, v in self._filters):
                yield _Snapshot(doc_id, data, _DocRef(self._collection, doc_id))


class _Collection(_Query):
    def __init__(self):
        self.docs: Dict[str, Dict[str, Any]] = {}
        super().__init__(self)
        self._counter = 0

    def document(self, doc_id):
        return _DocRef(self, doc_id)

    def add(self, data):
        self._counter += 1
        doc_id = f"gen{self._counter}"
        self.docs[doc_id] = dict(data)
        return None, _DocRef(self, doc_id)


class _Client:
    def __init__(self):
        self._collections: Dict[str, _Collection] = {}
        self.transactions = []

    def collection(self, name):
        return self._collections.setdefault(name, _Collection())

    def transaction(self):
        txn = _Transaction()
        self.transactions.append(txn)
        return txn


def _fake_transactional(func):
    return func


def test_firestore_store_uses_same_interface():
    client = _Client()
    store = FirestoreStore(client=client, transactional=_fake_transactional)
    assert store.kind == "firestore"
    apt = store.appointments
    created = apt.create({"barberId": "b1", "status": "pending"})
    assert created["id"] == "gen1"
    apt.create({"barberId": "b2", "status": "pending"}, doc_id="fixed")
    assert [a["id"] for a in apt.list(barberId="b1")] == ["gen1"]
    assert apt.update("gen1", {"status": "confirmed"})["status"] == "confirmed"
    assert apt.update("nope", {"status": "x"}) is None
    assert apt.get("fixed")["barberId"] == "b2"
    assert apt.upsert("fixed", {"barberId": "b3"}) == {"barberId": "b3", "id": "fixed"}
    assert apt.count() == 2 and apt.delete("fixed") and not apt.delete("fixed")
    apt.clear()
    assert apt.count() == 0
    assert seed_mock_data(store) is True and store.social_posts.count() == 2
    assert store.users.get("barber_1")["role"] == "barber"


def test_firestore_modify_runs_in_a_transaction():
    client = _Client()
    store = FirestoreStore(client=client, transactional=_fake_transactional)
    users = store.users
    users.create({"credits": 3}, doc_id="u1")
    assert users.modify("u1", lambda cur: {"credits": cur["credits"] - 2})["credits"] == 1
    assert users.get("u1")["credits"] == 1
    assert client.transactions[-1].ops == ["update"]
    assert users.modify("new", lambda cur: {"credits": 5} if cur is None else None) == {"credits": 5, "id": "new"}
    assert client.transactions[-1].ops == ["set"]
    assert users.modify("u1", lambda cur: None)["credits"] == 1
    assert users.modify("ghost", lambda cur: None) is None
