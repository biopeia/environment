"""Environment-owned external state and physical-scene capabilities."""

from environment.identified_resource import IdentifiedFiniteResource
from environment.physical import PhysicalSphere, project_resource_geometry
from environment.resource import FiniteResourceState
from environment.static_scene import (
    FrameDescriptor,
    PhysicalStepCorrelation,
    StaticEnvironmentOwner,
    StaticGroundPlane,
    StaticPhysicalScene,
    StaticSceneCandidate,
    project_static_scene,
)

__all__ = [
    "FiniteResourceState",
    "FrameDescriptor",
    "IdentifiedFiniteResource",
    "PhysicalSphere",
    "PhysicalStepCorrelation",
    "StaticEnvironmentOwner",
    "StaticGroundPlane",
    "StaticPhysicalScene",
    "StaticSceneCandidate",
    "project_resource_geometry",
    "project_static_scene",
]
