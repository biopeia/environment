"""Owner-side verification of an already restored Environment checkpoint.

The reference is supplied by the committed-cut authority. Environment checks
its restored state against that independent reference; it does not create a
durable store, prove power-loss safety, or decide whether a World cut committed.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required_identity(value: str | None, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class OwnerRestorationReference:
    """Independent committed reference passed to an Environment owner.

    ``owner_identity``, ``schema_version``, and ``checkpoint_sha256`` come
    from the committed owner reference, not from the candidate being checked.
    Environment and World bindings are included only where the particular
    owner checkpoint contract binds them.
    """

    owner_identity: str
    schema_version: str
    checkpoint_sha256: str
    environment_id: str | None = None
    environment_revision: str | None = None
    world_id: str | None = None

    def __post_init__(self) -> None:
        _required_identity(self.owner_identity, "owner_identity")
        _required_identity(self.schema_version, "schema_version")
        if not isinstance(self.checkpoint_sha256, str) or not _SHA256.fullmatch(
            self.checkpoint_sha256
        ):
            raise ValueError("checkpoint_sha256 must be a lowercase SHA-256 hex digest")
        if (self.environment_id is None) != (self.environment_revision is None):
            raise ValueError("Environment identity and revision must be supplied together")
        if self.environment_id is not None:
            _required_identity(self.environment_id, "environment_id")
            _required_identity(self.environment_revision, "environment_revision")
        if self.world_id is not None:
            _required_identity(self.world_id, "world_id")


def verify_restored_owner(
    *,
    checkpoint: bytes,
    owner_identity: str,
    schema_version: str,
    reference: OwnerRestorationReference,
    environment_id: str | None = None,
    environment_revision: str | None = None,
    world_id: str | None = None,
    requires_environment_binding: bool = False,
    requires_world_binding: bool = False,
) -> None:
    """Raise ``ValueError`` unless restored state matches its committed ref.

    ``checkpoint`` must be the canonical serialization of the restored owner
    object. The digest is checked against the independently supplied committed
    reference. This check is read-only and does not adopt state.
    """
    if not isinstance(reference, OwnerRestorationReference):
        raise ValueError("an independent OwnerRestorationReference is required")
    if not isinstance(checkpoint, bytes):
        raise ValueError("restored checkpoint must be bytes")
    if owner_identity != reference.owner_identity:
        raise ValueError("restored owner identity does not match committed reference")
    if schema_version != reference.schema_version:
        raise ValueError("restored schema version does not match committed reference")
    if requires_environment_binding and (
        reference.environment_id is None or reference.environment_revision is None
    ):
        raise ValueError("committed reference is missing required Environment binding")
    if requires_world_binding and reference.world_id is None:
        raise ValueError("committed reference is missing required World binding")
    if (environment_id, environment_revision) != (
        reference.environment_id,
        reference.environment_revision,
    ):
        raise ValueError("restored Environment identity/revision does not match committed reference")
    if world_id != reference.world_id:
        raise ValueError("restored World binding does not match committed reference")
    digest = hashlib.sha256(checkpoint).hexdigest()
    if digest != reference.checkpoint_sha256:
        raise ValueError("restored checkpoint content does not match committed reference")


__all__ = ["OwnerRestorationReference", "verify_restored_owner"]
