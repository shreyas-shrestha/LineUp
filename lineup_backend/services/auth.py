"""Token verification and user lookup.

Two token formats are accepted, never both:

* ``firebase`` mode (``FIREBASE_CREDENTIALS`` set): Firebase ID tokens verified
  with the Admin SDK.
* ``dev`` mode (development/testing without Firebase): HS256 JWTs issued by
  ``POST /auth/dev-login`` and signed with ``LINEUP_DEV_SECRET``.

In production without Firebase the mode is ``disabled`` and every protected
route answers 503 so a misconfigured deploy fails loudly instead of open.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Tuple

import jwt

from lineup_backend.config import AppConfig
from lineup_backend.services.billing import Ledger
from lineup_backend.services.users import new_user_doc
from lineup_backend.storage.base import Store

logger = logging.getLogger(__name__)

DEV_ISSUER = "lineup-dev"
DEV_AUDIENCE = "lineup"


class AuthError(Exception):
    """Authentication failure with an HTTP status and a stable error code."""

    def __init__(self, message: str, status: int = 401, code: str = "unauthorized") -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


@dataclass
class Principal:
    uid: str
    email: Optional[str] = None
    name: Optional[str] = None
    photo_url: Optional[str] = None
    provider: str = "firebase"


def dev_uid_for(email: str) -> str:
    digest = hashlib.sha1(email.strip().lower().encode("utf-8")).hexdigest()[:16]
    return f"dev_{digest}"


class AuthService:
    def __init__(
        self,
        config: AppConfig,
        store: Store,
        ledger: Ledger,
        verify_id_token: Optional[Callable[[str], Dict[str, Any]]] = None,
    ) -> None:
        self.config = config
        self.store = store
        self.ledger = ledger
        self.dev_secret = config.dev_secret or secrets.token_urlsafe(32)
        self._verify_id_token = verify_id_token
        self.mode = self._detect_mode()
        logger.info("Auth mode: %s", self.mode)
        if self.mode == "firebase":
            status = config.firebase_web_status()
            if status != "ok":
                logger.error(
                    "FIREBASE_WEB_CONFIG is %s: the browser cannot sign in and the page will say "
                    "'Sign-in is not configured on this server'. It must be the config object as strict "
                    'JSON with quoted keys, e.g. {"apiKey": "...", "authDomain": "...", "projectId": "...", '
                    '"appId": "..."} - not the `const firebaseConfig = {...}` snippet the console shows.',
                    status,
                )

    # -- setup -------------------------------------------------------------

    def _detect_mode(self) -> str:
        if self._verify_id_token is not None:
            return "firebase"
        if self.config.firebase_credentials:
            try:
                import firebase_admin
                from firebase_admin import auth as firebase_auth
                from firebase_admin import credentials

                if not firebase_admin._apps:  # noqa: SLF001 - documented idempotency check
                    firebase_admin.initialize_app(credentials.Certificate(json.loads(self.config.firebase_credentials)))
                self._verify_id_token = firebase_auth.verify_id_token
                return "firebase"
            except Exception as exc:  # noqa: BLE001 - fall through to dev/disabled
                logger.error("Firebase Auth initialisation failed (%s: %s)", type(exc).__name__, exc)
        if not self.config.is_production:
            return "dev"
        return "disabled"

    @property
    def dev_login_enabled(self) -> bool:
        return self.mode == "dev"

    @property
    def enabled(self) -> bool:
        return self.mode in ("firebase", "dev")

    def public_config(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "devLogin": self.dev_login_enabled,
            "firebase": self.config.firebase_web() if self.mode == "firebase" else None,
        }

    # -- dev tokens --------------------------------------------------------

    def issue_dev_token(self, uid: str, email: str, name: str) -> Tuple[str, int]:
        if not self.dev_login_enabled:
            raise AuthError("Developer sign-in is not available", 404, "not_found")
        now = int(time.time())
        expires = now + int(self.config.dev_token_ttl)
        payload = {"sub": uid, "email": email, "name": name, "iat": now, "exp": expires, "iss": DEV_ISSUER, "aud": DEV_AUDIENCE}
        token = jwt.encode(payload, self.dev_secret, algorithm="HS256")
        return token, expires

    def _verify_dev_token(self, token: str) -> Principal:
        try:
            claims = jwt.decode(token, self.dev_secret, algorithms=["HS256"], issuer=DEV_ISSUER, audience=DEV_AUDIENCE)
        except jwt.ExpiredSignatureError:
            raise AuthError("Your session has expired. Sign in again.", 401, "token_expired") from None
        except jwt.InvalidTokenError:
            raise AuthError("Invalid authentication token", 401, "invalid_token") from None
        uid = str(claims.get("sub") or "")
        if not uid:
            raise AuthError("Invalid authentication token", 401, "invalid_token")
        return Principal(uid=uid, email=claims.get("email"), name=claims.get("name"), provider="dev")

    # -- verification ------------------------------------------------------

    def verify(self, token: str) -> Principal:
        if self.mode == "disabled":
            raise AuthError("Authentication is not configured on this server", 503, "auth_not_configured")
        if self.mode == "dev":
            return self._verify_dev_token(token)
        assert self._verify_id_token is not None
        try:
            decoded = self._verify_id_token(token)
        except Exception as exc:  # noqa: BLE001 - invalid/expired/revoked all map to 401
            name = type(exc).__name__
            code = "token_expired" if "Expired" in name else "invalid_token"
            logger.info("Firebase token rejected: %s", name)
            raise AuthError("Invalid or expired authentication token", 401, code) from None
        uid = str((decoded or {}).get("uid") or (decoded or {}).get("sub") or "")
        if not uid:
            raise AuthError("Invalid authentication token", 401, "invalid_token")
        return Principal(
            uid=uid,
            email=decoded.get("email"),
            name=decoded.get("name"),
            photo_url=decoded.get("picture"),
            provider="firebase",
        )

    # -- users -------------------------------------------------------------

    def get_or_create_user(self, principal: Principal) -> Tuple[Dict[str, Any], bool]:
        """Load the user document, creating it (with signup credits) on first sight.

        Consumer-only mode has no onboarding step: every account is a client
        from its first request, and accounts created before the cut are
        promoted the same way.
        """
        existing = self.store.users.get(principal.uid)
        if existing is not None and not self._profile_patch(existing, principal):
            return existing, False  # hot path: no write per request
        created = {"value": False}
        default_role = "client" if self.config.consumer_only else None

        def mutate(current: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            if current is not None:
                return self._profile_patch(current, principal) or None
            created["value"] = True
            return new_user_doc(principal.uid, principal.email, principal.name, principal.photo_url, role=default_role, provider=principal.provider)

        user = self.store.users.modify(principal.uid, mutate)
        if created["value"]:
            self.ledger.record_signup(principal.uid, int(user.get("credits", 0) or 0))
        return user, created["value"]

    def _profile_patch(self, current: Dict[str, Any], principal: Principal) -> Dict[str, Any]:
        patch: Dict[str, Any] = {}
        if principal.email and not current.get("email"):
            patch["email"] = principal.email.lower()
        if principal.photo_url and principal.photo_url != current.get("photoUrl"):
            patch["photoUrl"] = principal.photo_url
        if self.config.consumer_only and not current.get("role"):
            patch["role"] = "client"
            patch["onboardedAt"] = datetime.now(timezone.utc).isoformat()
        return patch

    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self.store.users.find_one(email=email.strip().lower())
