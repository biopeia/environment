"""Engine-neutral projections of Environment-owned physical geometry.

This module carries geometry only. It deliberately does not import a solver or
assign units, a coordinate frame, contact behavior, or material properties.
Those semantics must be bound by an explicit World/solver integration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from environment.resource import FiniteResourceState


@dataclass(frozen=True, slots=True)
class PhysicalSphere:
    """Immutable sphere geometry copied from Environment-owned state.

    ``center`` and ``radius`` retain the source values without a unit or frame
    claim. This value is solver-neutral input, not a complete physical contract.
    """

    center: tuple[float, float, float]
    radius: float

    def __post_init__(self) -> None:
        if isinstance(self.center, (str, bytes)):
            raise ValueError("sphere center must contain three finite coordinates")
        try:
            center = tuple(float(value) for value in self.center)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(
                "sphere center must contain three finite coordinates"
            ) from error
        if len(center) != 3 or not all(math.isfinite(value) for value in center):
            raise ValueError("sphere center must contain three finite coordinates")
        object.__setattr__(self, "center", center)
        if isinstance(self.radius, bool):
            raise ValueError("sphere radius must be finite and positive")
        try:
            radius = float(self.radius)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("sphere radius must be finite and positive") from error
        if not math.isfinite(radius) or radius <= 0.0:
            raise ValueError("sphere radius must be finite and positive")
        object.__setattr__(self, "radius", radius)


def project_resource_geometry(resource: FiniteResourceState) -> PhysicalSphere:
    """Project only the resource collider geometry owned by Environment.

    The scalar influence ``field_radius`` and material amount are not collision
    geometry and are intentionally omitted. Values are copied into an immutable
    record; no state changes or engine calls occur.
    """

    return PhysicalSphere(center=tuple(resource.position), radius=resource.radius)


__all__ = ["PhysicalSphere", "project_resource_geometry"]
