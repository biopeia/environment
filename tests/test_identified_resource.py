import hashlib
import json
from types import SimpleNamespace

import pytest

from environment import (
    EnvironmentObservationContext,
    FiniteResourceState,
    FiniteScalarFieldSample,
    FiniteScalarFieldObservationProjection,
    FrameDescriptor,
    IdentifiedFiniteResource,
    IdentifiedFiniteScalarField,
    PhysicalStepCorrelation,
    project_committed_resource_state,
)


def test_identified_resource_checkpoint_preserves_owner_identity_and_state() -> None:
    owner = IdentifiedFiniteResource(
        "resource.alpha", FiniteResourceState(remaining=3.5)
    )

    encoded = owner.checkpoint_bytes()
    restored = IdentifiedFiniteResource.from_checkpoint_bytes(encoded)

    payload = json.loads(encoded)
    assert (
        payload["checkpoint_type"] == "biopeia.environment.identified-finite-resource"
    )
    assert payload["checkpoint_version"] == 1
    assert (
        payload["state"]["checkpoint_type"]
        == "biopeia.environment.finite-resource-state"
    )
    assert payload["state"]["checkpoint_version"] == 1
    assert encoded == owner.checkpoint_bytes()
    assert restored.resource_id == "resource.alpha"
    assert restored.state.checkpoint() == owner.state.checkpoint()


def test_committed_resource_projection_requires_exact_world_owner_reference() -> None:
    owner = IdentifiedFiniteResource("resource.alpha", FiniteResourceState(remaining=2.75))
    encoded = owner.checkpoint_bytes()
    reference = SimpleNamespace(
        owner="environment",
        owner_identity=owner.resource_id,
        checkpoint_id="environment-cut-7",
        schema_version=owner.OWNER_SCHEMA,
        locator="not-opened-by-projection",
        sha256=hashlib.sha256(encoded).hexdigest(),
    )
    cut = SimpleNamespace(
        world_id="world.alpha",
        causal_tick=7,
        commit_id="commit-7",
        owner_checkpoint_references=(reference,),
    )
    projection = project_committed_resource_state(
        encoded,
        committed_cut=cut,
        owner_reference=reference,
    )
    assert projection.remaining == 2.75
    assert projection.resource_id == owner.resource_id
    assert projection.world_id == "world.alpha"
    assert projection.causal_tick == 7
    assert projection.commit_id == "commit-7"
    assert projection.source_owner_checkpoint_sha256 == reference.sha256

    with pytest.raises(ValueError, match="not in the supplied World cut"):
        project_committed_resource_state(
            encoded,
            committed_cut=SimpleNamespace(
                world_id="world.alpha",
                causal_tick=7,
                commit_id="commit-7",
                owner_checkpoint_references=(),
            ),
            owner_reference=reference,
        )

    with pytest.raises(ValueError, match="not in the supplied World cut"):
        project_committed_resource_state(
            encoded,
            committed_cut=cut,
            owner_reference=SimpleNamespace(
                owner="environment",
                owner_identity=owner.resource_id,
                checkpoint_id="environment-cut-7",
                schema_version=owner.OWNER_SCHEMA,
                locator="unused",
                sha256="0" * 64,
            ),
        )


def test_identified_resource_checkpoint_rejects_invalid_identity_or_shape() -> None:
    with pytest.raises(ValueError, match="resource_id"):
        IdentifiedFiniteResource(" ", FiniteResourceState())

    payload = json.loads(
        IdentifiedFiniteResource(
            "resource.alpha", FiniteResourceState()
        ).checkpoint_bytes()
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
    owner = IdentifiedFiniteResource(
        "resource.alpha", FiniteResourceState(remaining=3.5)
    )
    payload = json.loads(owner.checkpoint_bytes())

    payload["unexpected"] = "future-looking but unsupported"
    with pytest.raises(ValueError, match="checkpoint fields"):
        IdentifiedFiniteResource.from_checkpoint_bytes(json.dumps(payload).encode())

    payload = json.loads(owner.checkpoint_bytes())
    payload["state"]["unexpected"] = "unsupported nested field"
    with pytest.raises(ValueError, match="finite resource checkpoint contract"):
        IdentifiedFiniteResource.from_checkpoint_bytes(json.dumps(payload).encode())


def test_owner_checkpoint_validation_checks_identity_schema_and_bytes() -> None:
    owner = IdentifiedFiniteResource(
        "resource.alpha", FiniteResourceState(remaining=3.5)
    )
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


def _observation_context(**changes: object) -> EnvironmentObservationContext:
    values: dict[str, object] = {
        "world_id": "world.alpha",
        "source_causal_tick": 17,
        "target_causal_tick": 18,
        "physical_step_id": "step.17",
        "environment_id": "environment.alpha",
        "environment_revision": "environment.rev-3",
        "resource_id": "resource.alpha",
        "field_revision": "field.rev-7",
    }
    values.update(changes)
    return EnvironmentObservationContext(**values)  # type: ignore[arg-type]


def test_scalar_field_uses_explicit_identity_range_frame_and_source_cut() -> None:
    field = IdentifiedFiniteScalarField(
        "resource.alpha",
        "field.rev-7",
        "environment.alpha",
        "environment.rev-3",
        "environment.frame",
        FiniteResourceState(position=(0.0, 0.0, 0.0), field_radius=2.0, remaining=1.0),
    )

    sample = field.sample_field(
        (1.0, 0.0, 0.0), frame=_frame(), correlation=_correlation()
    )

    assert sample.resource_id == "resource.alpha"
    assert sample.field_revision == "field.rev-7"
    assert sample.environment_id == "environment.alpha"
    assert sample.environment_revision == "environment.rev-3"
    assert (sample.world_id, sample.causal_tick, sample.physical_step_id) == (
        "world.alpha",
        17,
        "step.17",
    )
    assert sample.frame_id == "environment.frame"
    assert sample.point_m == (1.0, 0.0, 0.0)
    assert field.coordinate_unit == "m"
    assert field.frame_id == sample.frame_id
    assert (sample.quantity_kind, sample.unit, sample.valid_range) == (
        "dimensionless_scalar_field",
        "1",
        (0.0, 1.0),
    )
    assert sample.value == pytest.approx(0.25)


def test_scalar_field_is_zero_at_boundary_and_when_depleted() -> None:
    field = IdentifiedFiniteScalarField(
        "resource.alpha",
        "field.rev-1",
        "environment.alpha",
        "environment.rev-3",
        "environment.frame",
        FiniteResourceState(position=(0.0, 0.0, 0.0), field_radius=2.0, remaining=1.0),
    )
    assert (
        field.sample_field(
            (2.0, 0.0, 0.0), frame=_frame(), correlation=_correlation()
        ).value
        == 0.0
    )
    field.state.remaining = 0.0
    assert (
        field.sample_field(
            (0.0, 0.0, 0.0), frame=_frame(), correlation=_correlation()
        ).value
        == 0.0
    )


def test_scalar_field_rejects_wrong_frame_and_invalid_sampling_point() -> None:
    field = IdentifiedFiniteScalarField(
        "resource.alpha",
        "field.rev-1",
        "environment.alpha",
        "environment.rev-3",
        "environment.frame",
        FiniteResourceState(),
    )
    with pytest.raises(ValueError, match="sampling frame"):
        field.sample_field(
            (0.0, 0.0, 0.0), frame=_frame("other.frame"), correlation=_correlation()
        )
    with pytest.raises(ValueError, match="sample point"):
        field.sample_field(
            (float("nan"), 0.0, 0.0), frame=_frame(), correlation=_correlation()
        )
    stale = PhysicalStepCorrelation(
        world_id="world.alpha",
        causal_tick=17,
        physical_step_id="step.17",
        environment_id="environment.alpha",
        environment_revision="environment.rev-2",
    )
    with pytest.raises(ValueError, match="active Environment"):
        field.sample_field((0.0, 0.0, 0.0), frame=_frame(), correlation=stale)


def test_scalar_field_observation_projection_is_distinct_from_source_sample() -> None:
    field = IdentifiedFiniteScalarField(
        "resource.alpha",
        "field.rev-7",
        "environment.alpha",
        "environment.rev-3",
        "environment.frame",
        FiniteResourceState(position=(0.0, 0.0, 0.0), field_radius=2.0, remaining=1.0),
    )

    source_checkpoint = field.checkpoint_bytes()
    source = field.sample_field(
        (1.0, 0.0, 0.0), frame=_frame(), correlation=_correlation()
    )
    # Model owner adoption by changing the current authoritative field state
    # before requesting the target-cut projection.
    field.state.position = (1.0, 0.0, 0.0)
    projection = field.project_observation(
        (1.0, 0.0, 0.0), frame=_frame(), context=_observation_context()
    )

    assert source.causal_tick == 17
    assert projection.source_causal_tick == 17
    assert projection.target_causal_tick == 18
    assert projection.physical_step_id == "step.17"
    assert projection.world_id == "world.alpha"
    assert projection.resource_id == "resource.alpha"
    assert projection.field_revision == "field.rev-7"
    assert projection.environment_id == "environment.alpha"
    assert projection.environment_revision == "environment.rev-3"
    assert projection.frame_id == "environment.frame"
    assert projection.point_m == (1.0, 0.0, 0.0)
    assert projection.semantic_family_id == "biopeia.environment.finite-scalar-field"
    assert projection.semantic_revision == "1"
    assert (projection.quantity_kind, projection.unit, projection.valid_range) == (
        "dimensionless_scalar_field",
        "1",
        (0.0, 1.0),
    )
    assert source.value == pytest.approx(0.25)
    assert projection.value == pytest.approx(1.0)
    assert source.source_owner_checkpoint_sha256 == hashlib.sha256(source_checkpoint).hexdigest()
    assert projection.source_owner_checkpoint_sha256 == hashlib.sha256(
        field.checkpoint_bytes()
    ).hexdigest()
    assert projection.semantic_subject_type == "environment.finite_resource_field"
    assert projection.semantic_authority == "ENVIRONMENT"
    assert projection.semantic_asserter == "environment.identified_finite_scalar_field"
    assert projection.semantic_producer == (
        "environment.identified_finite_scalar_field.project_observation"
    )
    assert projection.epistemic_basis == "DOMAIN_DERIVED"
    assert projection.acquisition_basis == "environment_field_evaluation"


def test_scalar_field_projection_rejects_invalid_checkpoint_digest() -> None:
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        FiniteScalarFieldObservationProjection(
            resource_id="resource.alpha",
            field_revision="field.rev-7",
            environment_id="environment.alpha",
            environment_revision="environment.rev-3",
            world_id="world.alpha",
            source_causal_tick=17,
            target_causal_tick=18,
            physical_step_id="step.17",
            frame_id="environment.frame",
            point_m=(0.0, 0.0, 0.0),
            value=0.5,
            source_owner_checkpoint_sha256="not-a-digest",
        )


def test_scalar_field_sample_rejects_invalid_checkpoint_digest() -> None:
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        FiniteScalarFieldSample(
            resource_id="resource.alpha",
            field_revision="field.rev-7",
            world_id="world.alpha",
            causal_tick=17,
            physical_step_id="step.17",
            environment_id="environment.alpha",
            environment_revision="environment.rev-3",
            frame_id="environment.frame",
            point_m=(0.0, 0.0, 0.0),
            value=0.5,
            source_owner_checkpoint_sha256="not-a-digest",
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"environment_id": "environment.other"}, "Environment identity"),
        ({"environment_revision": "environment.rev-old"}, "Environment identity"),
        ({"resource_id": "resource.other"}, "resource identity"),
        ({"field_revision": "field.rev-old"}, "resource identity"),
    ],
)
def test_scalar_field_observation_projection_rejects_stale_identity(
    change: dict[str, object], message: str
) -> None:
    field = IdentifiedFiniteScalarField(
        "resource.alpha",
        "field.rev-7",
        "environment.alpha",
        "environment.rev-3",
        "environment.frame",
        FiniteResourceState(),
    )
    with pytest.raises(ValueError, match=message):
        field.project_observation(
            (0.0, 0.0, 0.0), frame=_frame(), context=_observation_context(**change)
        )


def test_scalar_field_observation_projection_rejects_wrong_frame_point_and_cut() -> (
    None
):
    field = IdentifiedFiniteScalarField(
        "resource.alpha",
        "field.rev-7",
        "environment.alpha",
        "environment.rev-3",
        "environment.frame",
        FiniteResourceState(),
    )
    with pytest.raises(ValueError, match="sampling frame"):
        field.project_observation(
            (0.0, 0.0, 0.0), frame=_frame("other.frame"), context=_observation_context()
        )
    with pytest.raises(ValueError, match="sample point"):
        field.project_observation(
            (float("inf"), 0.0, 0.0), frame=_frame(), context=_observation_context()
        )
    with pytest.raises(ValueError, match="immediately follow"):
        _observation_context(target_causal_tick=19)


def test_scalar_field_observation_projection_value_rejects_out_of_range() -> None:
    with pytest.raises(ValueError, match="within \\[0, 1\\]"):
        FiniteScalarFieldObservationProjection(
            resource_id="resource.alpha",
            field_revision="field.rev-7",
            environment_id="environment.alpha",
            environment_revision="environment.rev-3",
            world_id="world.alpha",
            source_causal_tick=17,
            target_causal_tick=18,
            physical_step_id="step.17",
            frame_id="environment.frame",
            point_m=(0.0, 0.0, 0.0),
            value=1.1,
            source_owner_checkpoint_sha256="0" * 64,
        )


def test_scalar_field_checkpoint_is_versioned_closed_and_recoverable() -> None:
    field = IdentifiedFiniteScalarField(
        "resource.alpha",
        "field.rev-2",
        "environment.alpha",
        "environment.rev-3",
        "environment.frame",
        FiniteResourceState(remaining=3.0),
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
