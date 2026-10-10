from dataclasses import replace

import pytest

from environment import (
    EnvironmentPhysicalProjection,
    FrameDescriptor,
    PhysicalStepCorrelation,
    StaticEnvironmentOwner,
    StaticGroundPlane,
    StaticPhysicalScene,
    StaticSphere,
)


def _scene(*, friction: float = 0.0) -> StaticPhysicalScene:
    return StaticPhysicalScene(
        environment_id="environment-1",
        environment_revision="environment-r3",
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
        gravity_m_s2=(0.0, 0.0, -9.81),
        objects=(StaticGroundPlane("ground-z", (0.0, 0.0, 1.0), 0.0, friction),),
        spheres=(StaticSphere("obstacle-a", (1.0, 0.0, 0.5), 0.25, "environment-frame", friction),),
    )


def _correlation(tick: int = 0, *, world: str = "world-1", revision: str = "environment-r3"):
    return PhysicalStepCorrelation(
        world_id=world,
        causal_tick=tick,
        physical_step_id=f"physical-step-{tick}",
        environment_id="environment-1",
        environment_revision=revision,
    )


def test_owner_projection_binds_geometry_revision_units_and_world_step():
    owner = StaticEnvironmentOwner(_scene(friction=0.2), "env-owner", world_id="world-1")
    projected = owner.project_physical_step(_correlation())

    assert isinstance(projected, EnvironmentPhysicalProjection)
    assert projected.correlation == _correlation()
    assert projected.scene.environment_id == "environment-1"
    assert projected.scene.environment_revision == "environment-r3"
    assert projected.scene.frame.frame_id == "environment-frame"
    assert projected.scene.gravity_m_s2 == (0.0, 0.0, -9.81)
    assert projected.length_unit == "m"
    assert projected.gravity_unit == "m/s^2"
    assert projected.sliding_friction_unit == "1"
    assert {item.object_id for item in (*projected.scene.objects, *projected.scene.spheres)} == {
        "ground-z", "obstacle-a"
    }
    assert projected.scene.objects[0].sliding_friction_coefficient == 0.2
    assert projected.geometry_revision and len(projected.geometry_revision) == 64


def test_projection_fails_closed_for_missing_contact_data_and_stale_world_context():
    missing_contact = StaticEnvironmentOwner(
        replace(_scene(), objects=(StaticGroundPlane("ground-z", (0.0, 0.0, 1.0)),)),
        "env-owner",
        world_id="world-1",
    )
    with pytest.raises(ValueError, match="explicit sliding friction"):
        missing_contact.project_physical_step(_correlation())

    owner = StaticEnvironmentOwner(_scene(), "env-owner", world_id="world-1")
    with pytest.raises(ValueError, match="bound World"):
        owner.project_physical_step(_correlation(world="world-2"))
    with pytest.raises(ValueError, match="active Environment revision"):
        owner.project_physical_step(_correlation(revision="old-revision"))
    with pytest.raises(ValueError, match="next causal tick"):
        owner.project_physical_step(_correlation(1))


def test_projection_is_bound_to_restored_environment_owner_and_exact_geometry():
    owner = StaticEnvironmentOwner(_scene(friction=0.15), "env-owner", world_id="world-1")
    before = owner.project_physical_step(_correlation())
    restored = StaticEnvironmentOwner.from_checkpoint_bytes(owner.checkpoint_bytes())
    after = restored.project_physical_step(_correlation())

    assert after == before
    changed = StaticEnvironmentOwner(_scene(friction=0.3), "env-owner", world_id="world-1")
    assert changed.project_physical_step(_correlation()).geometry_revision != before.geometry_revision


def test_projection_value_rejects_mismatched_geometry_digest_or_units():
    owner = StaticEnvironmentOwner(_scene(), "env-owner", world_id="world-1")
    projection = owner.project_physical_step(_correlation())
    with pytest.raises(ValueError, match="geometry_revision"):
        replace(projection, geometry_revision="0" * 64)
    with pytest.raises(ValueError, match="units"):
        replace(projection, length_unit="cm")
