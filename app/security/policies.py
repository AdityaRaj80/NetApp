"""Adaptive encryption and access control policies for storage locations."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Sequence, Set

from cryptography.fernet import Fernet, InvalidToken

__all__ = [
    "AdaptiveSecurityManager",
    "security_manager",
    "AuthorizationError",
    "EncryptionError",
]


POLICY_VERSION = "2024.1"


class AuthorizationError(PermissionError):
    """Raised when the caller lacks roles required to perform an operation."""


class EncryptionError(RuntimeError):
    """Raised when encryption or decryption fails."""


@dataclass
class _LocationPolicy:
    name: str
    key_id: str
    fernet: Fernet
    allowed_roles: Set[str] = field(default_factory=set)
    key_source: str = "default"

    def authorize(self, principal_roles: Optional[Iterable[str]]) -> None:
        roles = _normalize_roles(principal_roles)
        if not roles & self.allowed_roles:
            raise AuthorizationError(
                f"principal lacks roles for {self.name}; required one of {sorted(self.allowed_roles)}"
            )

    def snapshot(self) -> Dict[str, object]:
        return {
            "location": self.name,
            "policy_version": POLICY_VERSION,
            "encryption": {
                "algorithm": "fernet",
                "key_id": self.key_id,
                "key_source": self.key_source,
            },
            "access_control": {
                "allowed_roles": sorted(self.allowed_roles),
            },
        }


_DEFAULT_POLICY_DEFINITIONS: Dict[str, Dict[str, object]] = {
    "s3": {
        "env_key": "S3_ENCRYPTION_KEY",
        "env_roles": "S3_ALLOWED_ROLES",
        "default_key": "L49jTE3mqXUgmwOvV2EaXiiZkJtQXoaKKKzlqxMFhkI=",
        "default_roles": {"analytics", "engineering", "system"},
        "key_id": "s3-default",
    },
    "azure": {
        "env_key": "AZURE_ENCRYPTION_KEY",
        "env_roles": "AZURE_ALLOWED_ROLES",
        "default_key": "0-BIKqiBt__oUvQx41iC89SdJpAis6ruT5mHWZn5d50=",
        "default_roles": {"operations", "engineering", "system"},
        "key_id": "azure-default",
    },
    "gcs": {
        "env_key": "GCS_ENCRYPTION_KEY",
        "env_roles": "GCS_ALLOWED_ROLES",
        "default_key": "FNLdlBuOKy23fIzUTBSHXjhJsfIgSkikUSU3mWk50oo=",
        "default_roles": {"compliance", "analytics", "system"},
        "key_id": "gcs-default",
    },
}


class AdaptiveSecurityManager:
    """Central manager for encryption and access control per storage location."""

    def __init__(self, definitions: Optional[Dict[str, Dict[str, object]]] = None):
        self._definitions = definitions or dict(_DEFAULT_POLICY_DEFINITIONS)
        self._policies: Dict[str, _LocationPolicy] = {}
        self._load_policies()

    # ------------------------------------------------------------------
    # public API
    def encrypt(
        self,
        location: str,
        data: Optional[bytes],
        principal_roles: Optional[Iterable[str]] = None,
    ) -> Optional[bytes]:
        if data is None:
            return None
        policy = self._policy_for(location)
        policy.authorize(principal_roles)
        return policy.fernet.encrypt(data)

    def decrypt(
        self,
        location: str,
        data: Optional[bytes],
        principal_roles: Optional[Iterable[str]] = None,
    ) -> Optional[bytes]:
        if data is None:
            return None
        policy = self._policy_for(location)
        policy.authorize(principal_roles)
        try:
            return policy.fernet.decrypt(data)
        except InvalidToken as exc:  # pragma: no cover - depends on runtime key config
            raise EncryptionError(f"failed to decrypt payload from {policy.name}") from exc

    def describe_policy(self, location: str) -> Dict[str, object]:
        policy = self._policy_for(location)
        return policy.snapshot()

    def allowed_roles(self, location: str) -> Sequence[str]:
        policy = self._policy_for(location)
        return sorted(policy.allowed_roles)

    # ------------------------------------------------------------------
    # internal helpers
    def _policy_for(self, location: str) -> _LocationPolicy:
        key = _normalize_location(location)
        if key not in self._policies:
            raise ValueError(f"no security policy configured for location '{location}'")
        return self._policies[key]

    def _load_policies(self) -> None:
        for location, config in self._definitions.items():
            key = _normalize_location(location)
            env_var = str(config.get("env_key") or "")
            default_key = str(config.get("default_key") or "")
            raw_key = os.getenv(env_var) or default_key
            key_source = f"env:{env_var}" if os.getenv(env_var) else "default"
            fernet_key = _coerce_fernet_key(raw_key, location)
            fernet = Fernet(fernet_key)
            base_roles: Set[str] = set(config.get("default_roles") or set())
            roles_env_var = str(config.get("env_roles") or "")
            env_roles = _normalize_roles(os.getenv(roles_env_var, "").split(",") if roles_env_var else None)
            allowed_roles = base_roles | env_roles | {"system"}
            key_id = str(config.get("key_id") or f"{key}-default")
            self._policies[key] = _LocationPolicy(
                name=key,
                key_id=key_id,
                fernet=fernet,
                allowed_roles=allowed_roles,
                key_source=key_source,
            )


def _coerce_fernet_key(raw_key: str, location: str) -> bytes:
    if not raw_key:
        raise ValueError(f"missing encryption key for location '{location}'")
    raw_key = raw_key.strip()
    try:
        decoded = base64.urlsafe_b64decode(raw_key)
    except Exception as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"invalid base64 key for location '{location}'") from exc
    if len(decoded) != 32:  # Fernet keys are 32 bytes before base64 encoding
        raise ValueError(f"incorrect key length for location '{location}'")
    return raw_key.encode()


def _normalize_roles(principal_roles: Optional[Iterable[str]]) -> Set[str]:
    roles: Set[str] = set()
    if principal_roles is None:
        return {"system"}
    for role in principal_roles:
        if role is None:
            continue
        text = str(role).strip().lower()
        if text:
            roles.add(text)
    return roles or {"system"}


def _normalize_location(location: str) -> str:
    if location is None:
        raise ValueError("location cannot be None")
    return str(location).strip().lower()


security_manager = AdaptiveSecurityManager()

