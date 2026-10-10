from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from environment import (
    DynamicEnvironmentOwner,
    DynamicObjectState,
    FiniteResourceState,
    FrameDescriptor,
    DynamicEnvironmentCandidate,
    IdentifiedFiniteResource,
    IdentifiedFiniteScalarField,
    OwnerRestorationReference,
    PhysicalStepCorrelation,
    StaticEnvironmentOwner,
    StaticGroundPlane,
    StaticPhysicalScene,
)


def _reference(
    owner,
    *,
    owner_identity: str,
    schema_version: str,
    environment_id: str | None = None,
    environment_revision: str | None = None,
    world_id: str | None = None,
) -> OwnerRestorationReference:
    return OwnerRestorationReference(
        owner_identity=owner_identity,
        schema_version=schema_version,
        checkpoint_sha256=hashlib.sha256(owner.checkpoint_bytes()).hexdigest(),
        environment_id=environment_id,
        environment_revision=environment_revision,
        world_id=world_id,
    )


def _frame() -> FrameDescriptor:
    return FrameDescriptor(
        "env.frame", "world.frame", (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
        "RIGHT_HANDED", "Z",
    )


def _static_owner(*, world_id: str = "world-1", revision: str = "env.rev-1"):
    scene = StaticPhysicalScene(
        environment_id="env-1",
        environment_revision=revision,
        frame=_frame(),
        gravity_m_s2=(0, 0, -9.8),
        objects=(StaticGroundPlane("ground", (0, 0, 1)),),
    )
    return StaticEnvironmentOwner(scene, "env-owner-1", world_id=world_id)


def _dynamic_owner(*, world_id: str = "world-1", revision: str = "env.rev-1"):
    return DynamicEnvironmentOwner(
        owner_id="env-owner-1",
        world_id=world_id,
        environment_id="env-1",
        environment_revision=revision,
        frame=_frame(),
        object_state=DynamicObjectState("object-1", "env.frame", (0, 0, 0)),
    )


@pytest.mark.parametrize(
    "owner_factory,identity,schema,context",
    [
        (_static_owner, "env-owner-1", StaticEnvironmentOwner.CHECKPOINT_SCHEMA,
         {"environment_id": "env-1", "environment_revision": "env.rev-1", "world_id": "world-1"}),
        (_dynamic_owner, "env-owner-1", DynamicEnvironmentOwner.CHECKPOINT_SCHEMA,
         {"environment_id": "env-1", "environment_revision": "env.rev-1", "world_id": "world-1"}),
    ],
)
def test_restored_scene_and_dynamic_owners_verify_against_committed_reference(
    owner_factory, identity, schema, context
):
    original = owner_factory()
    restored = type(original).from_checkpoint_bytes(original.checkpoint_bytes())
    reference = _reference(
        original, owner_identity=identity, schema_version=schema, **context
    )

    assert restored.verify_restoration(reference) is None
    assert restored.checkpoint_bytes() == original.checkpoint_bytes()


def test_restored_dynamic_owner_continues_from_the_verified_accepted_tick():
    owner = _dynamic_owner()
    first = PhysicalStepCorrelation("world-1", 0, "step-0", "env-1", "env.rev-1")
    owner.validate_and_adopt(
        DynamicEnvironmentCandidate(
            first, DynamicObjectState("object-1", "env.frame", (1, 0, 0))
        ),
        expected_correlation=first,
    )
    encoded = owner.checkpoint_bytes()
    reference = _reference(
        owner,
        owner_identity=owner.owner_id,
        schema_version=owner.CHECKPOINT_SCHEMA,
        environment_id=owner.environment_id,
        environment_revision=owner.environment_revision,
        world_id=owner.world_id,
    )
    restored = DynamicEnvironmentOwner.from_checkpoint_bytes(encoded)
    restored.verify_restoration(reference)

    second = PhysicalStepCorrelation("world-1", 1, "step-1", "env-1", "env.rev-1")
    restored.validate_and_adopt(
        DynamicEnvironmentCandidate(
            second, DynamicObjectState("object-1", "env.frame", (2, 0, 0))
        ),
        expected_correlation=second,
    )
    assert restored.last_adopted_tick == 1
    assert restored.object_state.position_m == (2.0, 0.0, 0.0)


@pytest.mark.parametrize(
    "owner_factory,identity,schema,context",
    [
        (_static_owner, "env-owner-1", StaticEnvironmentOwner.CHECKPOINT_SCHEMA,
         {"environment_id": "env-1", "environment_revision": "env.rev-1", "world_id": "world-1"}),
        (_dynamic_owner, "env-owner-1", DynamicEnvironmentOwner.CHECKPOINT_SCHEMA,
         {"environment_id": "env-1", "environment_revision": "env.rev-1", "world_id": "world-1"}),
    ],
)
def test_restoration_rejects_mismatched_owner_environment_revision_world_and_digest_without_mutation(
    owner_factory, identity, schema, context
):
    original = owner_factory()
    restored = type(original).from_checkpoint_bytes(original.checkpoint_bytes())
    valid = _reference(original, owner_identity=identity, schema_version=schema, **context)
    before = restored.checkpoint_bytes()

    invalid_references = (
        replace(valid, owner_identity="other-owner"),
        replace(valid, schema_version="other-schema"),
        replace(valid, checkpoint_sha256="0" * 64),
        replace(valid, environment_id="other-environment"),
        replace(valid, environment_revision="other-revision"),
        replace(valid, world_id="other-world"),
    )
    for reference in invalid_references:
        with pytest.raises(ValueError):
            restored.verify_restoration(reference)
        assert restored.checkpoint_bytes() == before


@pytest.mark.parametrize("factory,schema", [(_static_owner, StaticEnvironmentOwner.CHECKPOINT_SCHEMA),
                                               (_dynamic_owner, DynamicEnvironmentOwner.CHECKPOINT_SCHEMA)])
def test_environment_owners_fail_closed_when_required_context_is_absent(factory, schema):
    owner = factory()
    reference = _reference(owner, owner_identity=owner.owner_id, schema_version=schema)
    before = owner.checkpoint_bytes()

    with pytest.raises(ValueError, match="missing required Environment binding"):
        owner.verify_restoration(reference)
    assert owner.checkpoint_bytes() == before

    with pytest.raises(ValueError, match="missing required World binding"):
        owner.verify_restoration(
            replace(reference, environment_id="env-1", environment_revision="env.rev-1")
        )
    assert owner.checkpoint_bytes() == before


def test_resource_owner_verifies_identity_schema_and_exact_content_digest():
    source = IdentifiedFiniteResource("resource-1", FiniteResourceState(remaining=3.0))
    encoded = source.checkpoint_bytes()
    restored = IdentifiedFiniteResource.from_checkpoint_bytes(encoded)
    reference = _reference(
        source,
        owner_identity="resource-1",
        schema_version=IdentifiedFiniteResource.OWNER_SCHEMA,
    )
    restored.verify_restoration(reference)

    changed = IdentifiedFiniteResource("resource-1", FiniteResourceState(remaining=2.0))
    with pytest.raises(ValueError, match="content"):
        changed.verify_restoration(reference)

    with pytest.raises(ValueError, match="Environment identity/revision"):
        restored.verify_restoration(replace(reference, environment_id="env-1", environment_revision="rev-1"))


def test_scalar_field_owner_verifies_environment_identity_and_revision():
    source = IdentifiedFiniteScalarField(
        "resource-1", "field.rev-1", "env-1", "env.rev-1", "env.frame",
        FiniteResourceState(position=(0, 0, 0), field_radius=2.0, remaining=1.0),
    )
    restored = IdentifiedFiniteScalarField.from_checkpoint_bytes(source.checkpoint_bytes())
    reference = _reference(
        source,
        owner_identity="resource-1",
        schema_version=IdentifiedFiniteScalarField.OWNER_SCHEMA,
        environment_id="env-1",
        environment_revision="env.rev-1",
    )
    restored.verify_restoration(reference)

    with pytest.raises(ValueError, match="Environment identity/revision"):
        restored.verify_restoration(replace(reference, environment_revision="stale"))
    with pytest.raises(ValueError, match="World binding"):
        restored.verify_restoration(replace(reference, world_id="world-1"))


@pytest.mark.parametrize(
    "values",
    [
        ("", "schema", "a" * 64),
        ("owner", "", "a" * 64),
        ("owner", "schema", "invalid"),
    ],
)
def test_reference_rejects_missing_identity_schema_or_invalid_checkpoint_digest(values):
    with pytest.raises(ValueError):
        OwnerRestorationReference(*values)


def test_reference_rejects_partial_environment_binding():
    with pytest.raises(ValueError, match="supplied together"):
        OwnerRestorationReference("owner", "schema", "a" * 64, environment_id="env")


def test_malformed_checkpoint_is_rejected_before_restoration_verification():
    with pytest.raises(ValueError, match="invalid dynamic Environment checkpoint"):
        DynamicEnvironmentOwner.from_checkpoint_bytes(b"tampered")

    source = _dynamic_owner()
    payload = json.loads(source.checkpoint_bytes())
    payload["owner_id"] = "forged-owner"
    tampered = DynamicEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())
    reference = _reference(
        source,
        owner_identity="env-owner-1",
        schema_version=DynamicEnvironmentOwner.CHECKPOINT_SCHEMA,
        environment_id="env-1",
        environment_revision="env.rev-1",
        world_id="world-1",
    )
    with pytest.raises(ValueError, match="owner identity"):
        tampered.verify_restoration(reference)
