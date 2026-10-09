from dataclasses import replace
import json

import pytest

from environment.static_scene import (
    FrameDescriptor,
    PhysicalStepCorrelation,
    StaticEnvironmentOwner,
    StaticGroundPlane,
    StaticPhysicalScene,
    StaticSceneCandidate,
    StaticSphere,
    project_static_scene,
)


def scene(objects=None, spheres=()):
    return StaticPhysicalScene(
        environment_id="environment-1",
        environment_revision="rev-3",
        frame=FrameDescriptor(
            frame_id="environment-frame",
            parent_frame_id="world-frame",
            origin_m=(0.0, 0.0, 0.0),
            x_axis_in_parent=(1.0, 0.0, 0.0),
            y_axis_in_parent=(0.0, 1.0, 0.0),
            z_axis_in_parent=(0.0, 0.0, 1.0),
            handedness="RIGHT_HANDED",
            up_axis="Z",
        ),
        gravity_m_s2=(0.0, 0.0, -9.80665),
        objects=tuple(objects if objects is not None else (StaticGroundPlane("ground", (0, 0, 1)),)),
        spheres=tuple(spheres),
    )


def correlation(
    tick=0, *, world_id="world-1", step_id=None, environment_id="environment-1", revision="rev-3"
):
    return PhysicalStepCorrelation(world_id, tick, step_id or f"step-{tick}", environment_id, revision)


def test_projection_is_pure_and_collection_order_invariant():
    objects = (StaticGroundPlane("z-ground", (0, 0, 1)), StaticGroundPlane("a-wall", (1, 0, 0), 2))
    first, second = scene(objects), scene(reversed(objects))
    assert project_static_scene(first) == project_static_scene(second)
    assert first.objects == objects


def test_projection_canonicalizes_sphere_order_by_stable_identity():
    left = StaticSphere("z", (0, 0, 1), 0.2, "environment-frame")
    right = StaticSphere("a", (1, 0, 0), 0.1, "environment-frame")
    projected = project_static_scene(scene(spheres=(left, right)))
    assert tuple(sphere.object_id for sphere in projected.spheres) == ("a", "z")


def test_requires_explicit_sane_frame_units_and_stable_unique_identity():
    with pytest.raises(ValueError, match="gravity_m_s2"):
        replace(scene(), gravity_m_s2=(0, 0, float("nan")))
    with pytest.raises(ValueError, match="unit vector"):
        StaticGroundPlane("ground", (0, 0, 2))
    with pytest.raises(ValueError, match="unique"):
        scene((StaticGroundPlane("same", (0, 0, 1)), StaticGroundPlane("same", (1, 0, 0))))
    with pytest.raises(ValueError, match="unique"):
        scene(spheres=(StaticSphere("ground", (0, 0, 0), 1.0, "environment-frame"),))
    with pytest.raises(ValueError, match="scene frame"):
        scene(spheres=(StaticSphere("sphere", (0, 0, 0), 1.0, "other-frame"),))
    with pytest.raises(ValueError, match="right-handed"):
        FrameDescriptor(
            "bad-frame", "world", (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, -1),
            "RIGHT_HANDED", "Z"
        )


@pytest.mark.parametrize("tick", [-1, True, 1.0])
def test_correlation_requires_nonnegative_integer_tick(tick):
    with pytest.raises(ValueError, match="causal_tick"):
        PhysicalStepCorrelation("world", tick, "step", "env", "rev")


def test_owner_adopts_only_same_scene_and_next_correlation():
    owner = StaticEnvironmentOwner(scene(), "environment-owner")
    checkpoint_before = owner.checkpoint_bytes()
    wrong_world = correlation(world_id="different-world")
    with pytest.raises(ValueError, match="World-authorized"):
        owner.validate_and_adopt(
            StaticSceneCandidate(wrong_world, owner.scene), expected_correlation=correlation()
        )
    wrong_step = correlation(step_id="not-the-authorized-step")
    with pytest.raises(ValueError, match="World-authorized"):
        owner.validate_and_adopt(
            StaticSceneCandidate(wrong_step, owner.scene), expected_correlation=correlation()
        )
    wrong_revision = correlation(revision="old")
    with pytest.raises(ValueError, match="identity/revision"):
        owner.validate_and_adopt(
            StaticSceneCandidate(wrong_revision, owner.scene), expected_correlation=wrong_revision
        )
    wrong_environment = correlation(environment_id="other-environment")
    with pytest.raises(ValueError, match="identity/revision"):
        owner.validate_and_adopt(
            StaticSceneCandidate(wrong_environment, owner.scene), expected_correlation=wrong_environment
        )
    assert owner.checkpoint_bytes() == checkpoint_before

    owner.validate_and_adopt(
        StaticSceneCandidate(correlation(), owner.scene), expected_correlation=correlation()
    )
    assert owner.last_adopted_tick == 0
    committed_checkpoint = owner.checkpoint_bytes()
    with pytest.raises(ValueError, match="stale"):
        owner.validate_and_adopt(
            StaticSceneCandidate(correlation(), owner.scene), expected_correlation=correlation()
        )
    with pytest.raises(ValueError, match="stale"):
        owner.validate_and_adopt(
            StaticSceneCandidate(correlation(2), owner.scene), expected_correlation=correlation(2)
        )
    changed = replace(owner.scene, gravity_m_s2=(0, 0, -1))
    with pytest.raises(ValueError, match="rejects changed"):
        owner.validate_and_adopt(
            StaticSceneCandidate(correlation(1), changed), expected_correlation=correlation(1)
        )
    changed_geometry = replace(
        owner.scene,
        spheres=(StaticSphere("sphere", (1, 0, 0), 0.5, "environment-frame"),),
    )
    with pytest.raises(ValueError, match="rejects changed"):
        owner.validate_and_adopt(
            StaticSceneCandidate(correlation(1), changed_geometry), expected_correlation=correlation(1)
        )
    assert owner.last_adopted_tick == 0
    assert owner.checkpoint_bytes() == committed_checkpoint


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
    assert restored.scene.frame == owner.scene.frame
    assert restored.last_adopted_tick == -1
    assert not StaticEnvironmentOwner.validate_checkpoint(
        owner.checkpoint_bytes(), "another-owner", StaticEnvironmentOwner.CHECKPOINT_SCHEMA
    )


def test_checkpoint_persists_accepted_step_and_rejects_replay_after_restore():
    owner = StaticEnvironmentOwner(scene(), "env-owner")
    accepted = correlation()
    owner.validate_and_adopt(
        StaticSceneCandidate(accepted, owner.scene), expected_correlation=accepted
    )
    restored = StaticEnvironmentOwner.from_checkpoint_bytes(owner.checkpoint_bytes())
    assert restored.last_accepted_correlation == accepted
    assert restored.last_accepted_correlation.world_id == "world-1"
    assert restored.last_accepted_correlation.causal_tick == 0
    assert restored.last_accepted_correlation.physical_step_id == "step-0"
    assert restored.last_accepted_correlation.environment_id == "environment-1"
    assert restored.last_accepted_correlation.environment_revision == "rev-3"
    before_replay = restored.checkpoint_bytes()
    with pytest.raises(ValueError, match="stale"):
        restored.validate_and_adopt(
            StaticSceneCandidate(accepted, restored.scene), expected_correlation=accepted
        )
    assert restored.checkpoint_bytes() == before_replay


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.__setitem__("unexpected", True),
        lambda payload: payload["scene"].__setitem__("unexpected", True),
        lambda payload: payload["scene"]["frame"].__setitem__("unexpected", True),
        lambda payload: payload["scene"]["objects"][0].__setitem__("unexpected", True),
        lambda payload: payload["scene"].__setitem__("unexpected_spheres", []),
    ],
    ids=("root", "scene", "frame", "object", "scene-extra"),
)
def test_checkpoint_rejects_unknown_fields_at_each_scene_level(mutate):
    encoded = StaticEnvironmentOwner(scene(), "env-owner").checkpoint_bytes()
    payload = json.loads(encoded)
    mutate(payload)

    with pytest.raises(ValueError, match="invalid static Environment checkpoint"):
        StaticEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())


def test_checkpoint_rejects_unknown_correlation_fields_without_losing_valid_state():
    owner = StaticEnvironmentOwner(scene(), "env-owner")
    accepted = correlation()
    owner.validate_and_adopt(
        StaticSceneCandidate(accepted, owner.scene), expected_correlation=accepted
    )
    valid_checkpoint = owner.checkpoint_bytes()
    payload = json.loads(valid_checkpoint)
    payload["last_accepted_correlation"]["unexpected"] = True

    with pytest.raises(ValueError, match="invalid static Environment checkpoint"):
        StaticEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())

    restored = StaticEnvironmentOwner.from_checkpoint_bytes(valid_checkpoint)
    assert restored.last_accepted_correlation == accepted
    assert restored.checkpoint_bytes() == valid_checkpoint


def test_checkpoint_rejects_boolean_schema_version():
    payload = json.loads(StaticEnvironmentOwner(scene(), "env-owner").checkpoint_bytes())
    payload["schema_version"] = True

    with pytest.raises(ValueError, match="invalid static Environment checkpoint"):
        StaticEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())


def test_checkpoint_v3_persists_spheres_and_rejects_v2_without_compatibility():
    sphere = StaticSphere("sphere-a", (1.25, -2.0, 0.5), 0.2, "environment-frame")
    owner = StaticEnvironmentOwner(scene(spheres=(sphere,)), "env-owner")
    encoded = owner.checkpoint_bytes()
    payload = json.loads(encoded)
    assert payload["schema_version"] == 3
    assert payload["scene"]["spheres"] == [
        {"object_id": "sphere-a", "center_m": [1.25, -2.0, 0.5], "radius_m": 0.2,
         "frame_id": "environment-frame"}
    ]
    restored = StaticEnvironmentOwner.from_checkpoint_bytes(encoded)
    assert restored.scene.spheres == (sphere,)
    payload["schema_version"] = 2
    with pytest.raises(ValueError, match="invalid static Environment checkpoint"):
        StaticEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())


def test_checkpoint_rejects_unknown_sphere_fields_and_invalid_sphere_geometry():
    encoded = StaticEnvironmentOwner(
        scene(spheres=(StaticSphere("sphere-a", (0, 0, 0), 0.25, "environment-frame"),)),
        "env-owner",
    ).checkpoint_bytes()
    payload = json.loads(encoded)
    payload["scene"]["spheres"][0]["extra"] = "not accepted"
    with pytest.raises(ValueError, match="invalid static Environment checkpoint"):
        StaticEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())
    payload = json.loads(encoded)
    payload["scene"]["spheres"][0]["radius_m"] = float("nan")
    with pytest.raises(ValueError, match="invalid static Environment checkpoint"):
        StaticEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())


def test_checkpoint_rejects_duplicate_sphere_identity():
    owner = StaticEnvironmentOwner(
        scene(spheres=(StaticSphere("sphere-a", (0, 0, 0), 0.25, "environment-frame"),)),
        "env-owner",
    )
    payload = json.loads(owner.checkpoint_bytes())
    payload["scene"]["spheres"].append(payload["scene"]["spheres"][0])
    with pytest.raises(ValueError, match="invalid static Environment checkpoint"):
        StaticEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())
