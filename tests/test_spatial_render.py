import hashlib

import pytest
import rfc8785

from environment.spatial_render import (
    MAX_DESCRIPTOR_BYTES,
    MAX_ITEMS,
    canonical_spatial_render_scene_bytes,
    project_spatial_render_scene,
)
from environment.static_scene import (
    FrameDescriptor,
    StaticGroundPlane,
    StaticPhysicalScene,
    StaticSphere,
)


def make_scene(*, objects=(), spheres=(), gravity=(0.0, 0.0, -9.80665)):
    return StaticPhysicalScene(
        environment_id="environment.demo",
        environment_revision="r1",
        frame=FrameDescriptor(
            frame_id="environment.frame",
            parent_frame_id="environment.parent-frame",
            origin_m=(0.0, 0.0, 0.0),
            x_axis_in_parent=(1.0, 0.0, 0.0),
            y_axis_in_parent=(0.0, 1.0, 0.0),
            z_axis_in_parent=(0.0, 0.0, 1.0),
            handedness="RIGHT_HANDED",
            up_axis="Z",
        ),
        gravity_m_s2=gravity,
        objects=tuple(objects),
        spheres=tuple(spheres),
    )


def test_empty_descriptor_matches_approved_jcs_vector():
    result = project_spatial_render_scene(make_scene())
    assert result["render_geometry_sha256"] == (
        "022f7875e378b8d9196f13528af47723ffd352f70e379e404946acb3ddc41a9d"
    )
    without_digest = {key: value for key, value in result.items() if key != "render_geometry_sha256"}
    assert result["render_geometry_sha256"] == hashlib.sha256(rfc8785.dumps(without_digest)).hexdigest()
    assert result["items"] == []


def test_sphere_descriptor_matches_approved_jcs_vector():
    result = project_spatial_render_scene(
        make_scene(spheres=(StaticSphere("sphere-a", (1, 0, 0), 0.25, "environment.frame"),))
    )
    assert result["render_geometry_sha256"] == (
        "d0cf99d58351cd91d5c716c3fb8553e54144cd63b418d16a57fb3eca6a4481d4"
    )
    assert result["items"] == [{
        "object_id": "sphere-a",
        "kind": "sphere",
        "frame_id": "environment.frame",
        "center_m": [1.0, 0.0, 0.0],
        "radius_m": 0.25,
    }]


def test_ground_plane_projection_preserves_exact_owner_parameters():
    result = project_spatial_render_scene(
        make_scene(objects=(StaticGroundPlane("ground-z", (0, 0, 1), 2.5),))
    )
    assert result["items"] == [{
        "object_id": "ground-z",
        "kind": "ground_plane",
        "frame_id": "environment.frame",
        "normal": [0.0, 0.0, 1.0],
        "offset_m": 2.5,
    }]
    assert result["render_geometry_sha256"] == hashlib.sha256(
        rfc8785.dumps({key: value for key, value in result.items() if key != "render_geometry_sha256"})
    ).hexdigest()


def test_projection_orders_items_by_utf8_id_and_ignores_solver_values():
    first = make_scene(
        objects=(StaticGroundPlane("z-ground", (0, 0, 1)), StaticGroundPlane("a-wall", (1, 0, 0), 2))
    )
    second = make_scene(
        objects=(StaticGroundPlane("a-wall", (1, 0, 0), 2), StaticGroundPlane("z-ground", (0, 0, 1))),
        gravity=(0, 0, -3.0),
    )
    left = project_spatial_render_scene(first)
    right = project_spatial_render_scene(second)
    assert [item["object_id"] for item in left["items"]] == ["a-wall", "z-ground"]
    assert left == right


def test_projection_rejects_unrepresentable_identity_or_overlarge_scene():
    with pytest.raises(ValueError, match="UTF-8 bytes"):
        project_spatial_render_scene(make_scene(spheres=(StaticSphere("x" * 129, (0, 0, 0), 1, "environment.frame"),)))
    too_many = tuple(StaticGroundPlane(f"plane-{index:03}", (0, 0, 1)) for index in range(MAX_ITEMS + 1))
    with pytest.raises(ValueError, match="128-item"):
        project_spatial_render_scene(make_scene(objects=too_many))
    assert len(canonical_spatial_render_scene_bytes(make_scene())) <= MAX_DESCRIPTOR_BYTES


def test_projection_is_detached_and_does_not_expose_non_render_state():
    result = project_spatial_render_scene(make_scene(objects=(StaticGroundPlane("ground", (0, 0, 1)),)))
    assert set(result) == {
        "schema_version", "environment_id", "environment_revision", "render_geometry_sha256",
        "length_unit", "frame", "items",
    }
    assert "gravity_m_s2" not in result
    result["items"].clear()
    assert project_spatial_render_scene(make_scene(objects=(StaticGroundPlane("ground", (0, 0, 1)),)))["items"]
