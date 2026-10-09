"""Stable owner identity for one finite resource state.

The identity belongs to the Environment owner boundary and is carried by its
checkpoint. It is not inferred from a caller's intervention request.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .resource import FiniteResourceState


@dataclass(slots=True)
class IdentifiedFiniteResource:
    """Environment-owned resource state with a stable, checkpointed identity."""

    resource_id: str
    state: FiniteResourceState

    SCHEMA_VERSION = 1

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ValueError("resource_id must be a non-empty string")
        if not isinstance(self.state, FiniteResourceState):
            raise ValueError("state must be FiniteResourceState")

    def checkpoint_bytes(self) -> bytes:
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "resource_id": self.resource_id,
            "state": self.state.checkpoint(),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

    @classmethod
    def from_checkpoint_bytes(cls, encoded: bytes) -> IdentifiedFiniteResource:
        if not isinstance(encoded, bytes):
            raise ValueError("checkpoint must be bytes")
        try:
            payload: Any = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid identified resource checkpoint JSON") from exc
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != cls.SCHEMA_VERSION
            or not isinstance(payload.get("resource_id"), str)
            or not isinstance(payload.get("state"), dict)
        ):
            raise ValueError("invalid identified resource checkpoint fields")
        return cls(
            resource_id=payload["resource_id"],
            state=FiniteResourceState.from_checkpoint(payload["state"]),
        )

    @classmethod
    def validate_checkpoint(cls, encoded: bytes, owner_identity: str, schema_version: str) -> bool:
        """Validate recoverable owner bytes without issuing a World receipt."""
        if schema_version != "environment-identified-resource-v1":
            return False
        try:
            checkpoint = cls.from_checkpoint_bytes(encoded)
        except (TypeError, ValueError):
            return False
        return checkpoint.resource_id == owner_identity

    @classmethod
    def verify_restoration(cls, encoded: bytes, owner_identity: str, schema_version: str) -> bool:
        """Verify a restored checkpoint through the same owner codec boundary."""
        return cls.validate_checkpoint(encoded, owner_identity, schema_version)


__all__ = ["IdentifiedFiniteResource"]
