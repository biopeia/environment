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

    CHECKPOINT_TYPE = "biopeia.environment.identified-finite-resource"
    CHECKPOINT_VERSION = 1
    OWNER_SCHEMA = "environment-identified-resource-v2"

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ValueError("resource_id must be a non-empty string")
        if not isinstance(self.state, FiniteResourceState):
            raise ValueError("state must be FiniteResourceState")

    def checkpoint_bytes(self) -> bytes:
        payload = {
            "checkpoint_type": self.CHECKPOINT_TYPE,
            "checkpoint_version": self.CHECKPOINT_VERSION,
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
            or set(payload)
            != {"checkpoint_type", "checkpoint_version", "resource_id", "state"}
            or payload.get("checkpoint_type") != cls.CHECKPOINT_TYPE
            or isinstance(payload.get("checkpoint_version"), bool)
            or payload.get("checkpoint_version") != cls.CHECKPOINT_VERSION
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
        if schema_version != cls.OWNER_SCHEMA:
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
