from dataclasses import replace

import pytest

from environment.static_scene import (
    PhysicalStepCorrelation,
    StaticEnvironmentOwner,
    StaticGroundPlane,
    StaticPhysicalScene,
    StaticSceneCandidate,
    project_static_scene,
)


def scene(objects=None):
    return StaticPhysicalScene(
        environment_id="environment-1",
        environment_revision="rev-3",
        frame_id="world-frame",
        gravity_m_s2=(0.0, 0.0, -9.80665),
        objects=tuple(objects if objects is not None else (StaticGroundPlane("ground", (0, 0, 1)),)),
    )


def correlation(tick=0, *, environment_id="environment-1", revision="rev-3"):
    return PhysicalStepCorrelation("world-1", tick, f"step-{tick}", environment_id, revision)


def test_projection_is_pure_and_collection_order_invariant():
    objects = (StaticGroundPlane("z-ground", (0, 0, 1)), StaticGroundPlane("a-wall", (1, 0, 0), 2))
    first, second = scene(objects), scene(reversed(objects))
    assert project_static_scene(first) == project_static_scene(second)
    assert first.objects == objects


def test_requires_explicit_sane_frame_units_and_stable_unique_identity():
    with pytest.raises(ValueError, match="frame_id"):
        replace(scene(), frame_id=" ")
    with pytest.raises(ValueError, match="gravity_m_s2"):
        replace(scene(), gravity_m_s2=(0, 0, float("nan")))
    with pytest.raises(ValueError, match="unit vector"):
        StaticGroundPlane("ground", (0, 0, 2))
    with pytest.raises(ValueError, match="unique"):
        scene((StaticGroundPlane("same", (0, 0, 1)), StaticGroundPlane("same", (1, 0, 0))))


@pytest.mark.parametrize("tick", [-1, True, 1.0])
def test_correlation_requires_nonnegative_integer_tick(tick):
    with pytest.raises(ValueError, match="causal_tick"):
        PhysicalStepCorrelation("world", tick, "step", "env", "rev")


def test_owner_adopts_only_same_scene_and_next_correlation():
    owner = StaticEnvironmentOwner(scene(), "environment-owner")
    owner.validate_and_adopt(StaticSceneCandidate(correlation(), owner.scene))
    assert owner.last_adopted_tick == 0
    with pytest.raises(ValueError, match="stale"):
        owner.validate_and_adopt(StaticSceneCandidate(correlation(), owner.scene))
    with pytest.raises(ValueError, match="identity/revision"):
        owner.validate_and_adopt(StaticSceneCandidate(correlation(1, revision="old"), owner.scene))
    changed = replace(owner.scene, gravity_m_s2=(0, 0, -1))
    with pytest.raises(ValueError, match="rejects changed"):
        owner.validate_and_adopt(StaticSceneCandidate(correlation(1), changed))
    assert owner.last_adopted_tick == 0


def test_checkpoint_is_deterministic_and_bound_to_owner_identity():
    owner = StaticEnvironmentOwner(scene((StaticGroundPlane("z", (0, 0, 1)), StaticGroundPlane("a", (1, 0, 0)))), "env-owner")
    reordered = StaticEnvironmentOwner(scene((StaticGroundPlane("a", (1, 0, 0)), StaticGroundPlane("z", (0, 0, 1)))), "env-owner")
    assert owner.checkpoint_bytes() == reordered.checkpoint_bytes()
    assert StaticEnvironmentOwner.validate_checkpoint(
        owner.checkpoint_bytes(), "env-owner", StaticEnvironmentOwner.CHECKPOINT_SCHEMA
    )
    restored = StaticEnvironmentOwner.from_checkpoint_bytes(owner.checkpoint_bytes())
    assert restored.owner_id == owner.owner_id
    assert restored.scene == owner.scene
    assert restored.last_adopted_tick == -1
    assert not StaticEnvironmentOwner.validate_checkpoint(
        owner.checkpoint_bytes(), "another-owner", StaticEnvironmentOwner.CHECKPOINT_SCHEMA
    )
