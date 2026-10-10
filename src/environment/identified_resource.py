"""Stable owner identity for one finite resource state.

The identity belongs to the Environment owner boundary and is carried by its
checkpoint. It is not inferred from a caller's intervention request.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, ClassVar

from .resource import FiniteResourceState
from .restoration import OwnerRestorationReference, verify_restored_owner
from .static_scene import FrameDescriptor, PhysicalStepCorrelation


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

    def verify_restoration(self, reference: OwnerRestorationReference) -> None:
        """Verify this restored resource against an independent committed ref."""
        verify_restored_owner(
            checkpoint=self.checkpoint_bytes(),
            owner_identity=self.resource_id,
            schema_version=self.OWNER_SCHEMA,
            reference=reference,
        )

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

@dataclass(frozen=True, slots=True)
class FiniteScalarFieldSample:
    """Objective Environment scalar value with explicit identity and applicability."""

    resource_id: str
    field_revision: str
    world_id: str
    causal_tick: int
    physical_step_id: str
    environment_id: str
    environment_revision: str
    frame_id: str
    point_m: tuple[float, float, float]
    value: float

    quantity_kind = "dimensionless_scalar_field"
    unit = "1"
    valid_range = (0.0, 1.0)

    def __post_init__(self) -> None:
        for name in (
            "resource_id", "field_revision", "world_id", "physical_step_id",
            "environment_id", "environment_revision", "frame_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if type(self.causal_tick) is not int or self.causal_tick < 0:
            raise ValueError("causal_tick must be a non-negative integer")
        if (
            not isinstance(self.point_m, tuple)
            or len(self.point_m) != 3
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in self.point_m
            )
        ):
            raise ValueError("point_m must contain three finite metre coordinates")
        if (
            isinstance(self.value, bool)
            or not isinstance(self.value, (int, float))
            or not math.isfinite(self.value)
            or not 0.0 <= self.value <= 1.0
        ):
            raise ValueError("value must be finite and within [0, 1]")


@dataclass(slots=True)
class IdentifiedFiniteScalarField:
    """Target-authored scalar-field projection over finite resource state.

    This is deliberately separate from ``IdentifiedFiniteResource`` so adding
    the sensing fixture does not change the existing material-transfer owner
    contract or its checkpoint/API. For this wrapper only, ``state.position``,
    ``state.radius`` and ``state.field_radius`` are interpreted as coordinates
    and lengths in metres in ``frame_id``. The wrapped state stores numeric
    values only; this explicit binding is what makes distance/radius ratios and
    caller ``point_m`` samples dimensionally coherent. It does not redefine
    units for other uses of ``FiniteResourceState``.
    """

    resource_id: str
    field_revision: str
    environment_id: str
    environment_revision: str
    frame_id: str
    state: FiniteResourceState

    CHECKPOINT_TYPE = "biopeia.environment.identified-finite-scalar-field"
    CHECKPOINT_VERSION = 1
    OWNER_SCHEMA = "environment-identified-finite-scalar-field-v1"
    coordinate_unit: ClassVar[str] = "m"

    def __post_init__(self) -> None:
        for name in ("resource_id", "field_revision", "environment_id", "environment_revision", "frame_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.state, FiniteResourceState):
            raise ValueError("state must be FiniteResourceState")

    def sample_field(
        self,
        point_m: tuple[float, float, float],
        *,
        frame: FrameDescriptor,
        correlation: PhysicalStepCorrelation,
    ) -> FiniteScalarFieldSample:
        """Sample the fixture profile using frame-local metre coordinates.

        The field state's position and radius values use the same ``frame_id``
        and metre unit as ``point_m``. The returned scalar is dimensionless.
        """
        if not isinstance(frame, FrameDescriptor) or frame.frame_id != self.frame_id:
            raise ValueError("sampling frame must match the resource field frame")
        if not isinstance(correlation, PhysicalStepCorrelation):
            raise ValueError("correlation must be a World-derived PhysicalStepCorrelation")
        if (
            correlation.environment_id != self.environment_id
            or correlation.environment_revision != self.environment_revision
        ):
            raise ValueError("correlation must match the active Environment identity and revision")
        if isinstance(point_m, (str, bytes)):
            raise ValueError("sample point must contain three finite metre coordinates")
        try:
            coordinates = tuple(point_m)
            if len(coordinates) != 3 or any(isinstance(value, bool) for value in coordinates):
                raise ValueError
            normalized = tuple(float(value) for value in coordinates)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("sample point must contain three finite metre coordinates") from exc
        if not all(math.isfinite(value) for value in normalized):
            raise ValueError("sample point must contain three finite metre coordinates")
        return FiniteScalarFieldSample(
            resource_id=self.resource_id,
            field_revision=self.field_revision,
            world_id=correlation.world_id,
            causal_tick=correlation.causal_tick,
            physical_step_id=correlation.physical_step_id,
            environment_id=self.environment_id,
            environment_revision=self.environment_revision,
            frame_id=self.frame_id,
            point_m=normalized,
            value=self.state.field_at(normalized),
        )

    def checkpoint_bytes(self) -> bytes:
        payload = {
            "checkpoint_type": self.CHECKPOINT_TYPE,
            "checkpoint_version": self.CHECKPOINT_VERSION,
            "resource_id": self.resource_id,
            "field_revision": self.field_revision,
            "environment_id": self.environment_id,
            "environment_revision": self.environment_revision,
            "frame_id": self.frame_id,
            "state": self.state.checkpoint(),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

    def verify_restoration(self, reference: OwnerRestorationReference) -> None:
        """Verify this restored field against an independent committed ref."""
        verify_restored_owner(
            checkpoint=self.checkpoint_bytes(),
            owner_identity=self.resource_id,
            schema_version=self.OWNER_SCHEMA,
            reference=reference,
            environment_id=self.environment_id,
            environment_revision=self.environment_revision,
            requires_environment_binding=True,
        )

    @classmethod
    def from_checkpoint_bytes(cls, encoded: bytes) -> IdentifiedFiniteScalarField:
        if not isinstance(encoded, bytes):
            raise ValueError("checkpoint must be bytes")
        try:
            payload: Any = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid scalar field checkpoint JSON") from exc
        expected = {
            "checkpoint_type", "checkpoint_version", "resource_id",
            "field_revision", "environment_id", "environment_revision", "frame_id", "state",
        }
        if (
            not isinstance(payload, dict)
            or set(payload) != expected
            or payload.get("checkpoint_type") != cls.CHECKPOINT_TYPE
            or type(payload.get("checkpoint_version")) is not int
            or payload["checkpoint_version"] != cls.CHECKPOINT_VERSION
            or not isinstance(payload.get("state"), dict)
        ):
            raise ValueError("invalid scalar field checkpoint fields")
        return cls(
            resource_id=payload["resource_id"],
            field_revision=payload["field_revision"],
            environment_id=payload["environment_id"],
            environment_revision=payload["environment_revision"],
            frame_id=payload["frame_id"],
            state=FiniteResourceState.from_checkpoint(payload["state"]),
        )

    @classmethod
    def validate_checkpoint(cls, encoded: bytes, owner_identity: str, schema_version: str) -> bool:
        if schema_version != cls.OWNER_SCHEMA:
            return False
        try:
            checkpoint = cls.from_checkpoint_bytes(encoded)
        except (TypeError, ValueError):
            return False
        return checkpoint.resource_id == owner_identity


__all__ = ["FiniteScalarFieldSample", "IdentifiedFiniteResource", "IdentifiedFiniteScalarField"]
