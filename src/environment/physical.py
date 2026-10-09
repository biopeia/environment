"""Explicit, engine-neutral projections of Environment physical geometry.

The resource model stores relative lengths rather than calibrated SI values.
This module only realizes those values in a caller-declared frame and scale;
it does not infer physical calibration or execute a coordinate transform.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from environment.resource import FiniteResourceState
from environment.static_scene import FrameDescriptor


def _finite_vector3(value: tuple[float, float, float]) -> tuple[float, float, float]:
    if isinstance(value, (str, bytes)):
        raise ValueError("sphere center_m must contain three finite coordinates")
    try:
        components = tuple(value)
        if any(isinstance(component, bool) for component in components):
            raise ValueError(
                "sphere center_m must contain three finite coordinates"
            )
        center = tuple(float(component) for component in components)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(
            "sphere center_m must contain three finite coordinates"
        ) from error
    if len(center) != 3 or not all(math.isfinite(component) for component in center):
        raise ValueError("sphere center_m must contain three finite coordinates")
    return center


def _positive_finite(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be finite and positive")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be finite and positive") from error
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return result


@dataclass(frozen=True, slots=True)
class PhysicalSphere:
    """A sphere expressed in metres in a declared, untransformed frame.

    ``meters_per_resource_unit`` records the caller-supplied scale used to
    realize the relative lengths from ``FiniteResourceState``. It is not a
    calibration result. ``center_m`` remains local to ``frame``; this type
    does not transform coordinates to the frame's parent.
    """

    center_m: tuple[float, float, float]
    radius_m: float
    frame: FrameDescriptor
    meters_per_resource_unit: float

    def __post_init__(self) -> None:
        center = _finite_vector3(self.center_m)
        object.__setattr__(self, "center_m", center)
        object.__setattr__(self, "radius_m", _positive_finite(self.radius_m, "radius_m"))
        if not isinstance(self.frame, FrameDescriptor):
            raise ValueError("sphere frame must be an explicit FrameDescriptor")
        object.__setattr__(
            self,
            "meters_per_resource_unit",
            _positive_finite(
                self.meters_per_resource_unit, "meters_per_resource_unit"
            ),
        )

    @property
    def frame_id(self) -> str:
        """Identity of the frame in which ``center_m`` is expressed."""
        return self.frame.frame_id


def project_resource_geometry(
    resource: FiniteResourceState,
    *,
    frame: FrameDescriptor,
    meters_per_resource_unit: float,
) -> PhysicalSphere:
    """Realize relative resource lengths in a caller-declared SI frame.

    The input resource's position and radius use the same relative spatial
    scale as its scalar ``field_radius``. This converts only its center and
    collision radius. It neither mutates the resource nor treats the scalar
    influence field, material quantity, or transfer limit as collider data.
    The caller-supplied scale is explicit configuration, not calibration
    evidence; coordinates remain local to ``frame``.
    """

    if not isinstance(resource, FiniteResourceState):
        raise TypeError("resource must be a FiniteResourceState")
    if not isinstance(frame, FrameDescriptor):
        raise ValueError("frame must be an explicit FrameDescriptor")
    scale = _positive_finite(meters_per_resource_unit, "meters_per_resource_unit")
    center = _finite_vector3(resource.position)
    radius = _positive_finite(resource.radius, "resource radius")
    return PhysicalSphere(
        center_m=tuple(coordinate * scale for coordinate in center),
        radius_m=radius * scale,
        frame=frame,
        meters_per_resource_unit=scale,
    )


__all__ = ["PhysicalSphere", "project_resource_geometry"]
