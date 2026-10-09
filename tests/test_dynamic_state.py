import json

import pytest

from environment import (
    DynamicEnvironmentCandidate,
    DynamicEnvironmentOwner,
    DynamicObjectState,
    FrameDescriptor,
    PhysicalStepCorrelation,
)


def state(position=(0.0, 0.0, 0.0)):
    return DynamicObjectState("object-1", "environment-frame", position)


def correlation(tick=0, **changes):
    values = {
        "world_id": "world-1",
        "causal_tick": tick,
        "physical_step_id": f"step-{tick}",
        "environment_id": "environment-1",
        "environment_revision": "revision-1",
    }
    values.update(changes)
    return PhysicalStepCorrelation(**values)


def owner():
    return DynamicEnvironmentOwner(
        owner_id="environment-owner-1",
        world_id="world-1",
        environment_id="environment-1",
        environment_revision="revision-1",
        frame=FrameDescriptor(
            "environment-frame", "world-frame", (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
            "RIGHT_HANDED", "Z",
        ),
        object_state=state(),
    )


def test_environment_owner_adopts_only_world_correlated_same_object_transition():
    current = owner()
    authorized = correlation()
    candidate = DynamicEnvironmentCandidate(authorized, state((1.25, -2.0, 0.5)))
    current.validate_and_adopt(candidate, expected_correlation=authorized)
    assert current.object_state.position_m == (1.25, -2.0, 0.5)
    assert current.last_accepted_correlation == authorized


@pytest.mark.parametrize(
    "candidate_correlation",
    [
        correlation(world_id="other-world"),
        correlation(physical_step_id="wrong-step"),
        correlation(environment_id="other-environment"),
        correlation(environment_revision="stale-revision"),
    ],
)
def test_rejects_wrong_world_step_environment_or_revision_without_mutation(candidate_correlation):
    current = owner()
    before = current.checkpoint_bytes()
    candidate = DynamicEnvironmentCandidate(candidate_correlation, state((9.0, 0.0, 0.0)))
    with pytest.raises(ValueError):
        current.validate_and_adopt(candidate, expected_correlation=correlation())
    assert current.checkpoint_bytes() == before


def test_bound_world_rejects_matching_candidate_and_expected_from_another_world():
    current = owner()
    before = current.checkpoint_bytes()
    other_world = correlation(world_id="other-world")
    with pytest.raises(ValueError, match="bound World"):
        current.validate_and_adopt(
            DynamicEnvironmentCandidate(other_world, state((9.0, 0.0, 0.0))),
            expected_correlation=other_world,
        )
    assert current.checkpoint_bytes() == before


def test_rejects_stale_tick_unknown_object_and_frame_without_mutation():
    current = owner()
    first = correlation()
    current.validate_and_adopt(
        DynamicEnvironmentCandidate(first, state((1.0, 0.0, 0.0))), expected_correlation=first
    )
    before = current.checkpoint_bytes()
    stale = correlation()
    with pytest.raises(ValueError, match="stale"):
        current.validate_and_adopt(
            DynamicEnvironmentCandidate(stale, state((2.0, 0.0, 0.0))), expected_correlation=stale
        )
    next_step = correlation(1)
    with pytest.raises(ValueError, match="identity/frame"):
        current.validate_and_adopt(
            DynamicEnvironmentCandidate(next_step, DynamicObjectState("other", "environment-frame", (2, 0, 0))),
            expected_correlation=next_step,
        )
    with pytest.raises(ValueError, match="identity/frame"):
        current.validate_and_adopt(
            DynamicEnvironmentCandidate(next_step, DynamicObjectState("object-1", "other-frame", (2, 0, 0))),
            expected_correlation=next_step,
        )
    assert current.checkpoint_bytes() == before


def test_checkpoint_restore_preserves_state_identity_and_next_step_continuity():
    current = owner()
    first = correlation()
    current.validate_and_adopt(
        DynamicEnvironmentCandidate(first, state((1.0, 2.0, 3.0))), expected_correlation=first
    )
    encoded = current.checkpoint_bytes()
    restored = DynamicEnvironmentOwner.from_checkpoint_bytes(encoded)
    assert restored.checkpoint_bytes() == encoded
    assert restored.owner_id == current.owner_id
    assert restored.world_id == current.world_id
    assert restored.environment_id == current.environment_id
    assert restored.object_state == current.object_state
    second = correlation(1)
    restored.validate_and_adopt(
        DynamicEnvironmentCandidate(second, state((2.0, 2.0, 3.0))), expected_correlation=second
    )
    assert restored.object_state.position_m == (2.0, 2.0, 3.0)
    assert restored.last_accepted_correlation == second


def test_initial_checkpoint_preserves_world_attachment_before_first_step():
    current = owner()
    restored = DynamicEnvironmentOwner.from_checkpoint_bytes(current.checkpoint_bytes())
    assert restored.world_id == "world-1"
    other_world = correlation(world_id="other-world")
    with pytest.raises(ValueError, match="bound World"):
        restored.validate_and_adopt(
            DynamicEnvironmentCandidate(other_world, state((1.0, 0.0, 0.0))),
            expected_correlation=other_world,
        )


def test_checkpoint_is_closed_and_requires_exact_schema():
    encoded = owner().checkpoint_bytes()
    payload = json.loads(encoded)
    payload["unexpected"] = "reject"
    with pytest.raises(ValueError, match="invalid dynamic Environment checkpoint"):
        DynamicEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())

    payload = json.loads(encoded)
    payload["schema_version"] = 1
    with pytest.raises(ValueError, match="invalid dynamic Environment checkpoint"):
        DynamicEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())

    payload = json.loads(encoded)
    payload["object_state"]["unexpected"] = "reject"
    with pytest.raises(ValueError, match="invalid dynamic Environment checkpoint"):
        DynamicEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())


def test_checkpoint_schema_and_checkpoint_reference_validation_are_explicit():
    current = owner()
    encoded = current.checkpoint_bytes()
    assert DynamicEnvironmentOwner.validate_checkpoint(
        encoded, "environment-owner-1", DynamicEnvironmentOwner.CHECKPOINT_SCHEMA
    )
    assert not DynamicEnvironmentOwner.validate_checkpoint(
        encoded, "other-owner", DynamicEnvironmentOwner.CHECKPOINT_SCHEMA
    )
    assert not DynamicEnvironmentOwner.validate_checkpoint(encoded, "environment-owner-1", "wrong-schema")


def test_checkpoint_rejects_last_correlation_from_another_world():
    current = owner()
    accepted = correlation()
    current.validate_and_adopt(
        DynamicEnvironmentCandidate(accepted, state((1.0, 0.0, 0.0))),
        expected_correlation=accepted,
    )
    payload = json.loads(current.checkpoint_bytes())
    payload["last_accepted_correlation"]["world_id"] = "other-world"
    with pytest.raises(ValueError, match="invalid dynamic Environment checkpoint"):
        DynamicEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())


def test_dynamic_state_rejects_non_finite_or_invalid_positions():
    with pytest.raises(ValueError, match="position_m"):
        state((float("nan"), 0.0, 0.0))
    with pytest.raises(ValueError, match="position_m"):
        state((0.0, 0.0))
