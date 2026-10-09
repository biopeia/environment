from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from environment import (
    FiniteResourceState,
    FrameDescriptor,
    PhysicalSphere,
    project_resource_geometry,
)


def _frame(
    frame_id: str = "environment.resources",
    *,
    origin_m: tuple[float, float, float] = (0.0, 0.0, 0.0),
    x_axis_in_parent: tuple[float, float, float] = (1.0, 0.0, 0.0),
    y_axis_in_parent: tuple[float, float, float] = (0.0, 1.0, 0.0),
    z_axis_in_parent: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> FrameDescriptor:
    return FrameDescriptor(
        frame_id=frame_id,
        parent_frame_id="world.root",
        origin_m=origin_m,
        x_axis_in_parent=x_axis_in_parent,
        y_axis_in_parent=y_axis_in_parent,
        z_axis_in_parent=z_axis_in_parent,
        handedness="RIGHT_HANDED",
        up_axis="Z",
    )


def test_resource_geometry_projection_scales_into_explicit_frame() -> None:
    resource = FiniteResourceState(
        position=(2.0, -1.0, 0.5), radius=0.25, field_radius=4.0, remaining=0.0
    )
    original_position = resource.position
    original_radius = resource.radius
    frame = _frame()

    projected = project_resource_geometry(
        resource, frame=frame, meters_per_resource_unit=0.1
    )

    assert projected == PhysicalSphere(
        center_m=(0.2, -0.1, 0.05),
        radius_m=0.025,
        frame=frame,
        meters_per_resource_unit=0.1,
    )
    assert projected.frame_id == "environment.resources"
    assert projected.frame is frame
    assert projected.meters_per_resource_unit == 0.1
    assert resource.position == original_position
    assert resource.radius == original_radius
    with pytest.raises(FrozenInstanceError):
        projected.radius_m = 3.0  # type: ignore[misc]


def test_projection_requires_caller_declared_frame_and_scale() -> None:
    resource = FiniteResourceState()

    with pytest.raises(TypeError):
        project_resource_geometry(resource)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        project_resource_geometry(resource, frame=_frame())  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        project_resource_geometry(
            resource, meters_per_resource_unit=1.0  # type: ignore[call-arg]
        )


def test_projection_keeps_coordinates_local_to_nontrivial_frame() -> None:
    frame = _frame(
        origin_m=(10.0, 20.0, 30.0),
        x_axis_in_parent=(0.0, 1.0, 0.0),
        y_axis_in_parent=(-1.0, 0.0, 0.0),
    )
    projected = project_resource_geometry(
        FiniteResourceState(position=(2.0, -1.0, 0.5)),
        frame=frame,
        meters_per_resource_unit=0.1,
    )

    assert projected.center_m == (0.2, -0.1, 0.05)
    assert projected.frame is frame


@pytest.mark.parametrize("scale", [0.0, -1.0, float("nan"), float("inf"), True])
def test_projection_rejects_invalid_caller_scale(scale: float) -> None:
    with pytest.raises(ValueError):
        project_resource_geometry(
            FiniteResourceState(), frame=_frame(), meters_per_resource_unit=scale
        )


@pytest.mark.parametrize(
    "center,radius",
    [
        ((1.0, 2.0), 1.0),
        ((1.0, float("inf"), 2.0), 1.0),
        ((0.0, 0.0, 0.0), 0.0),
        ((True, 0.0, 0.0), 1.0),
    ],
)
def test_physical_sphere_rejects_invalid_geometry(
    center: tuple[float, ...], radius: float
) -> None:
    with pytest.raises(ValueError):
        PhysicalSphere(
            center_m=center,  # type: ignore[arg-type]
            radius_m=radius,
            frame=_frame(),
            meters_per_resource_unit=1.0,
        )


def test_projection_does_not_treat_field_radius_as_collider_geometry() -> None:
    resource = FiniteResourceState(
        position=(1.0, 2.0, 3.0), radius=0.25, field_radius=7.0
    )

    projected = project_resource_geometry(
        resource, frame=_frame(), meters_per_resource_unit=2.0
    )

    assert projected.center_m == (2.0, 4.0, 6.0)
    assert projected.radius_m == 0.5
    assert not hasattr(projected, "field_radius_m")
