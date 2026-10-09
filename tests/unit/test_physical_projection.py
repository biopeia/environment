from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from environment import FiniteResourceState, PhysicalSphere, project_resource_geometry


def test_resource_geometry_projection_is_immutable_and_engine_neutral() -> None:
    resource = FiniteResourceState(
        position=(2.0, -1.0, 0.5), radius=0.25, field_radius=4.0, remaining=0.0
    )

    projected = project_resource_geometry(resource)

    assert projected == PhysicalSphere(center=(2.0, -1.0, 0.5), radius=0.25)
    with pytest.raises(FrozenInstanceError):
        projected.radius = 3.0  # type: ignore[misc]
    resource.position = (9.0, 8.0, 7.0)
    assert projected.center == (2.0, -1.0, 0.5)


@pytest.mark.parametrize(
    "center,radius",
    [((1.0, 2.0), 1.0), ((1.0, float("inf"), 2.0), 1.0), ((0.0, 0.0, 0.0), 0.0)],
)
def test_physical_sphere_rejects_invalid_geometry(
    center: tuple[float, ...], radius: float
) -> None:
    with pytest.raises(ValueError):
        PhysicalSphere(center=center, radius=radius)  # type: ignore[arg-type]


def test_physical_sphere_copies_mutable_coordinate_input() -> None:
    center = [1.0, 2.0, 3.0]

    projected = PhysicalSphere(center=center, radius=0.5)  # type: ignore[arg-type]
    center[0] = 9.0

    assert projected.center == (1.0, 2.0, 3.0)
