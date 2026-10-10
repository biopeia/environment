import json

import pytest

from environment.identified_resource import IdentifiedFiniteResource, IdentifiedFiniteScalarField
from environment.resource import FiniteResourceState
from environment.static_scene import FrameDescriptor, PhysicalStepCorrelation


def test_identified_resource_checkpoint_preserves_owner_identity_and_state() -> None:
    owner = IdentifiedFiniteResource("resource.alpha", FiniteResourceState(remaining=3.5))

    encoded = owner.checkpoint_bytes()
    restored = IdentifiedFiniteResource.from_checkpoint_bytes(encoded)

    payload = json.loads(encoded)
    assert payload["checkpoint_type"] == "biopeia.environment.identified-finite-resource"
    assert payload["checkpoint_version"] == 1
    assert payload["state"]["checkpoint_type"] == "biopeia.environment.finite-resource-state"
    assert payload["state"]["checkpoint_version"] == 1
    assert encoded == owner.checkpoint_bytes()
    assert restored.resource_id == "resource.alpha"
    assert restored.state.checkpoint() == owner.state.checkpoint()


def test_identified_resource_checkpoint_rejects_invalid_identity_or_shape() -> None:
    with pytest.raises(ValueError, match="resource_id"):
        IdentifiedFiniteResource(" ", FiniteResourceState())

    payload = json.loads(
        IdentifiedFiniteResource("resource.alpha", FiniteResourceState()).checkpoint_bytes()
    )
    payload["resource_id"] = ""
    with pytest.raises(ValueError, match="resource_id"):
        IdentifiedFiniteResource.from_checkpoint_bytes(json.dumps(payload).encode())

    source_v1 = {
        "schema_version": 1,
        "resource_id": "resource.alpha",
        "state": {
            "schema_version": 1,
            "position": [3.0, 0.0, 0.18],
            "radius": 0.18,
            "field_radius": 6.0,
            "remaining": 200.0,
            "transfer_per_tick": 2.0,
        },
    }
    with pytest.raises(ValueError, match="checkpoint fields"):
        IdentifiedFiniteResource.from_checkpoint_bytes(json.dumps(source_v1).encode())


def test_identified_resource_checkpoint_rejects_unknown_fields_at_each_level() -> None:
    owner = IdentifiedFiniteResource("resource.alpha", FiniteResourceState(remaining=3.5))
    payload = json.loads(owner.checkpoint_bytes())

    payload["unexpected"] = "future-looking but unsupported"
    with pytest.raises(ValueError, match="checkpoint fields"):
        IdentifiedFiniteResource.from_checkpoint_bytes(json.dumps(payload).encode())

    payload = json.loads(owner.checkpoint_bytes())
    payload["state"]["unexpected"] = "unsupported nested field"
    with pytest.raises(ValueError, match="finite resource checkpoint contract"):
        IdentifiedFiniteResource.from_checkpoint_bytes(json.dumps(payload).encode())


def test_owner_checkpoint_validation_checks_identity_schema_and_bytes() -> None:
    owner = IdentifiedFiniteResource("resource.alpha", FiniteResourceState(remaining=3.5))
    encoded = owner.checkpoint_bytes()

    assert IdentifiedFiniteResource.validate_checkpoint(
        encoded, "resource.alpha", IdentifiedFiniteResource.OWNER_SCHEMA
    )
    assert not IdentifiedFiniteResource.validate_checkpoint(
        encoded, "resource.other", IdentifiedFiniteResource.OWNER_SCHEMA
    )
    assert not IdentifiedFiniteResource.validate_checkpoint(
        encoded, "resource.alpha", "unsupported-schema"
    )
    assert not IdentifiedFiniteResource.validate_checkpoint(
        b"not a checkpoint", "resource.alpha", IdentifiedFiniteResource.OWNER_SCHEMA
    )


def _frame(frame_id: str = "environment.frame") -> FrameDescriptor:
    return FrameDescriptor(
        frame_id=frame_id,
        parent_frame_id="world.frame",
        origin_m=(0.0, 0.0, 0.0),
        x_axis_in_parent=(1.0, 0.0, 0.0),
        y_axis_in_parent=(0.0, 1.0, 0.0),
        z_axis_in_parent=(0.0, 0.0, 1.0),
        handedness="RIGHT_HANDED",
        up_axis="Z",
    )


def _correlation() -> PhysicalStepCorrelation:
    return PhysicalStepCorrelation(
        world_id="world.alpha",
        causal_tick=17,
        physical_step_id="step.17",
        environment_id="environment.alpha",
        environment_revision="environment.rev-3",
    )


def test_scalar_field_uses_explicit_identity_range_frame_and_source_cut() -> None:
    field = IdentifiedFiniteScalarField(
        "resource.alpha",
        "field.rev-7",
        "environment.alpha",
        "environment.rev-3",
        "environment.frame",
        FiniteResourceState(position=(0.0, 0.0, 0.0), field_radius=2.0, remaining=1.0),
    )

    sample = field.sample_field((1.0, 0.0, 0.0), frame=_frame(), correlation=_correlation())

    assert sample.resource_id == "resource.alpha"
    assert sample.field_revision == "field.rev-7"
    assert sample.environment_id == "environment.alpha"
    assert sample.environment_revision == "environment.rev-3"
    assert (sample.world_id, sample.causal_tick, sample.physical_step_id) == (
        "world.alpha", 17, "step.17"
    )
    assert sample.frame_id == "environment.frame"
    assert sample.point_m == (1.0, 0.0, 0.0)
    assert (sample.quantity_kind, sample.unit, sample.valid_range) == (
        "dimensionless_scalar_field", "1", (0.0, 1.0)
    )
    assert sample.value == pytest.approx(0.25)


def test_scalar_field_is_zero_at_boundary_and_when_depleted() -> None:
    field = IdentifiedFiniteScalarField(
        "resource.alpha", "field.rev-1", "environment.alpha", "environment.rev-3", "environment.frame",
        FiniteResourceState(position=(0.0, 0.0, 0.0), field_radius=2.0, remaining=1.0),
    )
    assert field.sample_field((2.0, 0.0, 0.0), frame=_frame(), correlation=_correlation()).value == 0.0
    field.state.remaining = 0.0
    assert field.sample_field((0.0, 0.0, 0.0), frame=_frame(), correlation=_correlation()).value == 0.0


def test_scalar_field_rejects_wrong_frame_and_invalid_sampling_point() -> None:
    field = IdentifiedFiniteScalarField(
        "resource.alpha", "field.rev-1", "environment.alpha", "environment.rev-3", "environment.frame", FiniteResourceState()
    )
    with pytest.raises(ValueError, match="sampling frame"):
        field.sample_field((0.0, 0.0, 0.0), frame=_frame("other.frame"), correlation=_correlation())
    with pytest.raises(ValueError, match="sample point"):
        field.sample_field((float("nan"), 0.0, 0.0), frame=_frame(), correlation=_correlation())
    stale = PhysicalStepCorrelation(
        world_id="world.alpha", causal_tick=17, physical_step_id="step.17",
        environment_id="environment.alpha", environment_revision="environment.rev-2",
    )
    with pytest.raises(ValueError, match="active Environment"):
        field.sample_field((0.0, 0.0, 0.0), frame=_frame(), correlation=stale)


def test_scalar_field_checkpoint_is_versioned_closed_and_recoverable() -> None:
    field = IdentifiedFiniteScalarField(
        "resource.alpha", "field.rev-2", "environment.alpha", "environment.rev-3", "environment.frame", FiniteResourceState(remaining=3.0)
    )
    encoded = field.checkpoint_bytes()
    restored = IdentifiedFiniteScalarField.from_checkpoint_bytes(encoded)
    payload = json.loads(encoded)

    assert payload["checkpoint_version"] == 1
    assert payload["environment_id"] == "environment.alpha"
    assert payload["environment_revision"] == "environment.rev-3"
    assert restored.resource_id == field.resource_id
    assert restored.field_revision == field.field_revision
    assert restored.environment_id == field.environment_id
    assert restored.environment_revision == field.environment_revision
    assert restored.frame_id == field.frame_id
    assert restored.state.checkpoint() == field.state.checkpoint()
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="checkpoint fields"):
        IdentifiedFiniteScalarField.from_checkpoint_bytes(json.dumps(payload).encode())
