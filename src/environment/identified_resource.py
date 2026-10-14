"""Stable owner identity for one finite resource state.

The identity belongs to the Environment owner boundary and is carried by its
checkpoint. It is not inferred from a caller's intervention request.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol

from .resource import FiniteResourceState
from .restoration import OwnerRestorationReference, verify_restored_owner
from .static_scene import FrameDescriptor, PhysicalStepCorrelation


FINITE_SCALAR_FIELD_FAMILY_ID = "biopeia.environment.finite-scalar-field"
FINITE_SCALAR_FIELD_SEMANTIC_REVISION = "1"
FINITE_SCALAR_FIELD_SUBJECT_TYPE = "environment.finite_resource_field"
FINITE_SCALAR_FIELD_AUTHORITY = "ENVIRONMENT"
FINITE_SCALAR_FIELD_EPISTEMIC_BASIS = "DOMAIN_DERIVED"
FINITE_SCALAR_FIELD_ACQUISITION_BASIS = "environment_field_evaluation"
FINITE_SCALAR_FIELD_ASSERTER = "environment.identified_finite_scalar_field"
FINITE_SCALAR_FIELD_PRODUCER = (
    "environment.identified_finite_scalar_field.project_observation"
)


def _validate_owner_checkpoint_digest(value: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("source owner checkpoint digest must be lowercase SHA-256")


class _CommittedCheckpointReference(Protocol):
    """Structural view of a World-issued owner checkpoint reference."""

    owner: str
    owner_identity: str
    checkpoint_id: str
    schema_version: str
    sha256: str


class _CommittedWorldCutReceipt(Protocol):
    """Structural view of World evidence; World remains the trust boundary."""

    world_id: str
    causal_tick: int
    commit_id: str
    owner_checkpoint_references: tuple[_CommittedCheckpointReference, ...]


@dataclass(frozen=True, slots=True)
class ResourceStateObservationProjection:
    """Environment-owned post-adoption resource state at one committed cut.

    ``remaining`` is copied from the exact referenced owner checkpoint. Its
    numeric representation has no declared physical unit or transfer meaning.
    """

    resource_id: str
    remaining: float
    world_id: str
    causal_tick: int
    commit_id: str
    checkpoint_id: str
    checkpoint_type: str
    checkpoint_version: int
    checkpoint_schema: str
    source_owner_checkpoint_sha256: str

    semantic_family_id: ClassVar[str] = "biopeia.environment.resource_state_snapshot"
    semantic_revision: ClassVar[str] = "1"
    semantic_authority: ClassVar[str] = "ENVIRONMENT"
    semantic_asserter: ClassVar[str] = "environment.identified_finite_resource"
    semantic_producer: ClassVar[str] = "environment.identified_finite_resource.project_committed_state"


def project_committed_resource_state(
    checkpoint_bytes: bytes,
    *,
    committed_cut: _CommittedWorldCutReceipt,
    owner_reference: _CommittedCheckpointReference,
) -> ResourceStateObservationProjection:
    """Project only the exact Environment checkpoint in a World cut.

    The World publication boundary remains responsible for proving the receipt
    is committed. This owner function proves the reference belongs to the
    supplied receipt and that the value was decoded from its exact bytes. The
    receipt is correlation context, not independent proof of commit authority.
    """
    if not isinstance(checkpoint_bytes, bytes):
        raise ValueError("Environment checkpoint snapshot must be bytes")
    world_id = getattr(committed_cut, "world_id", None)
    causal_tick = getattr(committed_cut, "causal_tick", None)
    commit_id = getattr(committed_cut, "commit_id", None)
    cut_references = getattr(committed_cut, "owner_checkpoint_references", None)
    if not isinstance(world_id, str) or not world_id.strip():
        raise ValueError("World committed-cut receipt must identify a World")
    if type(causal_tick) is not int or causal_tick < 0:
        raise ValueError("World committed-cut receipt must identify a valid causal tick")
    if not isinstance(commit_id, str) or not commit_id.strip():
        raise ValueError("World committed-cut receipt must identify a commit")
    if not isinstance(cut_references, tuple) or owner_reference not in cut_references:
        raise ValueError("Environment owner reference is not in the supplied World cut")
    expected_digest = hashlib.sha256(checkpoint_bytes).hexdigest()
    if (
        getattr(owner_reference, "owner", None) != "environment"
        or getattr(owner_reference, "schema_version", None) != IdentifiedFiniteResource.OWNER_SCHEMA
        or getattr(owner_reference, "sha256", None) != expected_digest
    ):
        raise ValueError("checkpoint does not match the committed Environment owner reference")
    checkpoint_id = getattr(owner_reference, "checkpoint_id", None)
    owner_identity = getattr(owner_reference, "owner_identity", None)
    if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
        raise ValueError("committed Environment checkpoint id is required")
    if not isinstance(owner_identity, str) or not owner_identity.strip():
        raise ValueError("committed Environment owner identity is required")
    restored = IdentifiedFiniteResource.from_checkpoint_bytes(checkpoint_bytes)
    if restored.resource_id != owner_identity:
        raise ValueError("checkpoint resource identity differs from committed owner reference")
    return ResourceStateObservationProjection(
        resource_id=restored.resource_id,
        remaining=restored.state.remaining,
        world_id=world_id,
        causal_tick=causal_tick,
        commit_id=commit_id,
        checkpoint_id=checkpoint_id,
        checkpoint_type=IdentifiedFiniteResource.CHECKPOINT_TYPE,
        checkpoint_version=IdentifiedFiniteResource.CHECKPOINT_VERSION,
        checkpoint_schema=IdentifiedFiniteResource.OWNER_SCHEMA,
        source_owner_checkpoint_sha256=expected_digest,
    )


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
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()

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
    def validate_checkpoint(
        cls, encoded: bytes, owner_identity: str, schema_version: str
    ) -> bool:
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
    source_owner_checkpoint_sha256: str

    quantity_kind = "dimensionless_scalar_field"
    unit = "1"
    valid_range = (0.0, 1.0)

    def __post_init__(self) -> None:
        _validate_owner_checkpoint_digest(self.source_owner_checkpoint_sha256)
        for name in (
            "resource_id",
            "field_revision",
            "world_id",
            "physical_step_id",
            "environment_id",
            "environment_revision",
            "frame_id",
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


@dataclass(frozen=True, slots=True)
class EnvironmentObservationContext:
    """Owner-local correlation for a post-adoption field observation.

    This is correlation data, not proof that World committed ``target_causal_tick``.
    The caller must invoke the Environment projection only after the relevant
    owner state has been adopted; World independently verifies the commit before
    publishing any resulting projection.
    """

    world_id: str
    source_causal_tick: int
    target_causal_tick: int
    physical_step_id: str
    environment_id: str
    environment_revision: str
    resource_id: str
    field_revision: str

    def __post_init__(self) -> None:
        for name in (
            "world_id",
            "physical_step_id",
            "environment_id",
            "environment_revision",
            "resource_id",
            "field_revision",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
            object.__setattr__(self, name, value.strip())
        if (
            type(self.source_causal_tick) is not int
            or type(self.target_causal_tick) is not int
            or self.source_causal_tick < 0
            or self.target_causal_tick != self.source_causal_tick + 1
        ):
            raise ValueError("target causal tick must immediately follow source tick")


@dataclass(frozen=True, slots=True)
class FiniteScalarFieldObservationProjection:
    """Environment-owned field sample at an explicit location and applicability.

    The projection describes the Environment field's value at ``point_m`` for
    the target causal applicability. It does not identify the receptor or prove
    owner adoption or a World commit; Embodiment owns receptor identity and
    World owns commit.
    """

    resource_id: str
    field_revision: str
    environment_id: str
    environment_revision: str
    world_id: str
    source_causal_tick: int
    target_causal_tick: int
    physical_step_id: str
    frame_id: str
    point_m: tuple[float, float, float]
    value: float
    source_owner_checkpoint_sha256: str

    quantity_kind: ClassVar[str] = "dimensionless_scalar_field"
    unit: ClassVar[str] = "1"
    valid_range: ClassVar[tuple[float, float]] = (0.0, 1.0)
    semantic_family_id: ClassVar[str] = FINITE_SCALAR_FIELD_FAMILY_ID
    semantic_revision: ClassVar[str] = FINITE_SCALAR_FIELD_SEMANTIC_REVISION
    semantic_subject_type: ClassVar[str] = FINITE_SCALAR_FIELD_SUBJECT_TYPE
    semantic_authority: ClassVar[str] = FINITE_SCALAR_FIELD_AUTHORITY
    semantic_asserter: ClassVar[str] = FINITE_SCALAR_FIELD_ASSERTER
    semantic_producer: ClassVar[str] = FINITE_SCALAR_FIELD_PRODUCER
    epistemic_basis: ClassVar[str] = FINITE_SCALAR_FIELD_EPISTEMIC_BASIS
    acquisition_basis: ClassVar[str] = FINITE_SCALAR_FIELD_ACQUISITION_BASIS

    def __post_init__(self) -> None:
        for name in (
            "resource_id",
            "field_revision",
            "environment_id",
            "environment_revision",
            "world_id",
            "physical_step_id",
            "frame_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
            object.__setattr__(self, name, value.strip())
        _validate_owner_checkpoint_digest(self.source_owner_checkpoint_sha256)
        if (
            type(self.source_causal_tick) is not int
            or type(self.target_causal_tick) is not int
            or self.source_causal_tick < 0
            or self.target_causal_tick != self.source_causal_tick + 1
        ):
            raise ValueError(
                "observation causal tick must immediately follow source tick"
            )
        if (
            not isinstance(self.point_m, tuple)
            or len(self.point_m) != 3
            or any(
                isinstance(component, bool)
                or not isinstance(component, (int, float))
                or not math.isfinite(component)
                for component in self.point_m
            )
        ):
            raise ValueError("point_m must contain three finite metre coordinates")
        normalized = tuple(float(component) for component in self.point_m)
        object.__setattr__(self, "point_m", normalized)
        if (
            isinstance(self.value, bool)
            or not isinstance(self.value, (int, float))
            or not math.isfinite(self.value)
            or not 0.0 <= self.value <= 1.0
        ):
            raise ValueError("value must be finite and within [0, 1]")
        object.__setattr__(self, "value", float(self.value))


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
        for name in (
            "resource_id",
            "field_revision",
            "environment_id",
            "environment_revision",
            "frame_id",
        ):
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
            raise ValueError(
                "correlation must be a World-derived PhysicalStepCorrelation"
            )
        if (
            correlation.environment_id != self.environment_id
            or correlation.environment_revision != self.environment_revision
        ):
            raise ValueError(
                "correlation must match the active Environment identity and revision"
            )
        if isinstance(point_m, (str, bytes)):
            raise ValueError("sample point must contain three finite metre coordinates")
        try:
            coordinates = tuple(point_m)
            if len(coordinates) != 3 or any(
                isinstance(value, bool) for value in coordinates
            ):
                raise ValueError
            normalized = tuple(float(value) for value in coordinates)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "sample point must contain three finite metre coordinates"
            ) from exc
        if not all(math.isfinite(value) for value in normalized):
            raise ValueError("sample point must contain three finite metre coordinates")
        source_checkpoint = self.checkpoint_bytes()
        source_owner = self.from_checkpoint_bytes(source_checkpoint)
        if (
            source_owner.environment_id != correlation.environment_id
            or source_owner.environment_revision != correlation.environment_revision
            or source_owner.frame_id != frame.frame_id
        ):
            raise ValueError("checkpoint snapshot does not match sampling context")
        return FiniteScalarFieldSample(
            resource_id=source_owner.resource_id,
            field_revision=source_owner.field_revision,
            world_id=correlation.world_id,
            causal_tick=correlation.causal_tick,
            physical_step_id=correlation.physical_step_id,
            environment_id=source_owner.environment_id,
            environment_revision=source_owner.environment_revision,
            frame_id=source_owner.frame_id,
            point_m=normalized,
            value=source_owner.state.field_at(normalized),
            source_owner_checkpoint_sha256=hashlib.sha256(source_checkpoint).hexdigest(),
        )

    def project_observation(
        self,
        point_m: tuple[float, float, float],
        *,
        frame: FrameDescriptor,
        context: EnvironmentObservationContext,
    ) -> FiniteScalarFieldObservationProjection:
        """Project the field at an adopted-state location and target applicability.

        Call only after Environment has adopted the state for
        ``context.target_causal_tick``. This method validates Environment-local
        identity/revision/frame and computes the value from the current owner
        state. It cannot verify that adoption occurred or authenticate World
        commit; the World publication path must verify the exact committed cut
        and owner reference independently.
        """
        if not isinstance(frame, FrameDescriptor) or frame.frame_id != self.frame_id:
            raise ValueError("sampling frame must match the resource field frame")
        if not isinstance(context, EnvironmentObservationContext):
            raise TypeError("context must be EnvironmentObservationContext")
        if (
            context.environment_id != self.environment_id
            or context.environment_revision != self.environment_revision
        ):
            raise ValueError(
                "context must match the active Environment identity and revision"
            )
        if (
            context.resource_id != self.resource_id
            or context.field_revision != self.field_revision
        ):
            raise ValueError(
                "context must match the active resource identity and field revision"
            )
        if isinstance(point_m, (str, bytes)):
            raise ValueError("sample point must contain three finite metre coordinates")
        try:
            coordinates = tuple(point_m)
            if len(coordinates) != 3 or any(
                isinstance(value, bool) for value in coordinates
            ):
                raise ValueError
            normalized = tuple(float(value) for value in coordinates)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "sample point must contain three finite metre coordinates"
            ) from exc
        if not all(math.isfinite(value) for value in normalized):
            raise ValueError("sample point must contain three finite metre coordinates")
        source_checkpoint = self.checkpoint_bytes()
        source_owner = self.from_checkpoint_bytes(source_checkpoint)
        if (
            source_owner.resource_id != context.resource_id
            or source_owner.field_revision != context.field_revision
            or source_owner.environment_id != context.environment_id
            or source_owner.environment_revision != context.environment_revision
            or source_owner.frame_id != frame.frame_id
        ):
            raise ValueError("checkpoint snapshot does not match observation context")
        return FiniteScalarFieldObservationProjection(
            resource_id=source_owner.resource_id,
            field_revision=source_owner.field_revision,
            environment_id=source_owner.environment_id,
            environment_revision=source_owner.environment_revision,
            world_id=context.world_id,
            source_causal_tick=context.source_causal_tick,
            target_causal_tick=context.target_causal_tick,
            physical_step_id=context.physical_step_id,
            frame_id=source_owner.frame_id,
            point_m=normalized,
            value=source_owner.state.field_at(normalized),
            source_owner_checkpoint_sha256=hashlib.sha256(source_checkpoint).hexdigest(),
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
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()

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
            "checkpoint_type",
            "checkpoint_version",
            "resource_id",
            "field_revision",
            "environment_id",
            "environment_revision",
            "frame_id",
            "state",
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
    def validate_checkpoint(
        cls, encoded: bytes, owner_identity: str, schema_version: str
    ) -> bool:
        if schema_version != cls.OWNER_SCHEMA:
            return False
        try:
            checkpoint = cls.from_checkpoint_bytes(encoded)
        except (TypeError, ValueError):
            return False
        return checkpoint.resource_id == owner_identity


__all__ = [
    "EnvironmentObservationContext",
    "FiniteScalarFieldObservationProjection",
    "FiniteScalarFieldSample",
    "ResourceStateObservationProjection",
    "project_committed_resource_state",
    "IdentifiedFiniteResource",
    "IdentifiedFiniteScalarField",
]
