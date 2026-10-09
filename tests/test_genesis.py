from dataclasses import replace
import json

import pytest

from environment import (
    GENERATOR_ID,
    GENERATOR_REVISION,
    EnvironmentGenesisConfig,
    EnvironmentGenesisSpec,
    FrameDescriptor,
    StaticGroundPlane,
    StaticEnvironmentOwner,
    generate_procedural_environment,
)


def _frame() -> FrameDescriptor:
    return FrameDescriptor(
        frame_id="env-frame",
        parent_frame_id="world-frame",
        origin_m=(0.0, 0.0, 0.0),
        x_axis_in_parent=(1.0, 0.0, 0.0),
        y_axis_in_parent=(0.0, 1.0, 0.0),
        z_axis_in_parent=(0.0, 0.0, 1.0),
        handedness="RIGHT_HANDED",
        up_axis="Z",
    )


def _spec(seed: int = 42) -> EnvironmentGenesisSpec:
    return EnvironmentGenesisSpec(
        environment_seed=seed,
        generator_id=GENERATOR_ID,
        generator_revision=GENERATOR_REVISION,
        configuration=EnvironmentGenesisConfig(
            environment_id="environment-test",
            environment_revision="revision-1",
            frame=_frame(),
            gravity_m_s2=(0.0, 0.0, -9.81),
            ground_plane=StaticGroundPlane("ground", (0.0, 0.0, 1.0), 0.0),
            bounds_min_m=(-2.0, -1.0, 0.0),
            bounds_max_m=(2.0, 1.0, 3.0),
            sphere_count=12,
            minimum_radius_m=0.05,
            maximum_radius_m=0.25,
        ),
    )


def test_same_complete_spec_generates_same_scene_and_explicit_provenance():
    spec = _spec()
    first = generate_procedural_environment(spec)
    second = generate_procedural_environment(spec)

    assert first == second
    assert first.scene.genesis.generator_id == GENERATOR_ID
    assert first.scene.genesis.generator_revision == GENERATOR_REVISION
    assert first.scene.genesis.environment_seed == 42
    assert len(first.scene.spheres) == 12
    assert first.scene.frame == spec.configuration.frame
    assert first.scene.gravity_m_s2 == (0.0, 0.0, -9.81)
    assert first.scene.objects == (spec.configuration.ground_plane,)
    assert {sphere.object_id for sphere in first.scene.spheres} == {
        f"sphere-{index:06d}" for index in range(12)
    }
    assert first.scene.genesis.configuration["sphere_count"] == 12
    for sphere in first.scene.spheres:
        assert sphere.frame_id == "env-frame"
        assert all(-2.0 <= coordinate <= 2.0 for coordinate in sphere.center_m[:1])
        assert -1.0 <= sphere.center_m[1] <= 1.0
        assert 0.0 <= sphere.center_m[2] <= 3.0
        assert 0.05 <= sphere.radius_m <= 0.25


def test_generated_geometry_is_scene_authority_and_checkpoint_restores_it():
    generated = generate_procedural_environment(_spec())
    owner = StaticEnvironmentOwner(generated.scene, "environment-owner")
    restored = StaticEnvironmentOwner.from_checkpoint_bytes(owner.checkpoint_bytes())

    assert restored.scene.spheres == generated.scene.spheres
    assert restored.scene.genesis == generated.scene.genesis
    assert restored.scene.genesis.configuration["sphere_count"] == 12
    assert restored.checkpoint_bytes() == owner.checkpoint_bytes()


def test_checkpoint_keeps_generator_configuration_structured_and_opaque_on_restore():
    owner = StaticEnvironmentOwner(generate_procedural_environment(_spec()).scene, "environment-owner")
    payload = json.loads(owner.checkpoint_bytes())
    payload["scene"]["genesis"]["configuration"]["future_generator_input"] = {"mode": "opaque"}

    restored = StaticEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())

    assert restored.scene.genesis.configuration["future_generator_input"] == {"mode": "opaque"}
    assert json.loads(restored.checkpoint_bytes())["scene"]["genesis"]["configuration"]["future_generator_input"] == {
        "mode": "opaque"
    }


@pytest.mark.parametrize("mutate", [
    lambda provenance: provenance.__setitem__("unexpected", "field"),
    lambda provenance: provenance.__setitem__("configuration", []),
])
def test_checkpoint_rejects_malformed_genesis_provenance_shape(mutate):
    owner = StaticEnvironmentOwner(generate_procedural_environment(_spec()).scene, "environment-owner")
    payload = json.loads(owner.checkpoint_bytes())
    mutate(payload["scene"]["genesis"])

    with pytest.raises(ValueError, match="invalid static Environment checkpoint"):
        StaticEnvironmentOwner.from_checkpoint_bytes(json.dumps(payload).encode())


def test_seed_and_configuration_are_causal_generator_inputs():
    baseline = generate_procedural_environment(_spec())
    other_seed = generate_procedural_environment(_spec(seed=43))
    config = replace(_spec().configuration, sphere_count=13)
    other_config = generate_procedural_environment(
        EnvironmentGenesisSpec(42, GENERATOR_ID, GENERATOR_REVISION, config)
    )

    assert baseline != other_seed
    assert baseline != other_config
    assert len(other_config.scene.spheres) == 13


@pytest.mark.parametrize(
    "updates",
    [
        {"bounds_min_m": (1.0, 0.0, 0.0), "bounds_max_m": (1.0, 1.0, 1.0)},
        {"sphere_count": -1},
        {"minimum_radius_m": 0.5, "maximum_radius_m": 0.1},
        {"maximum_radius_m": float("inf")},
    ],
)
def test_rejects_invalid_generation_configuration(updates):
    with pytest.raises(ValueError):
        replace(_spec().configuration, **updates)


def test_rejects_unknown_generator_contract_and_non_integer_seed():
    with pytest.raises(ValueError, match="unsupported"):
        generate_procedural_environment(
            replace(_spec(), generator_revision="future")
        )
    with pytest.raises(ValueError, match="environment_seed"):
        EnvironmentGenesisSpec(True, GENERATOR_ID, GENERATOR_REVISION, _spec().configuration)
