"""Environment-owned external state and physical-scene capabilities."""

from environment.identified_resource import IdentifiedFiniteResource
from environment.procedural_genesis import (
    GENERATOR_ID,
    GENERATOR_REVISION,
    EnvironmentGenesisConfig,
    EnvironmentGenesisSpec,
    GeneratedSphere,
    ProceduralEnvironmentScene,
    generate_procedural_environment,
)
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
    "GENERATOR_ID",
    "GENERATOR_REVISION",
    "EnvironmentGenesisConfig",
    "EnvironmentGenesisSpec",
    "FiniteResourceState",
    "FrameDescriptor",
    "GeneratedSphere",
    "IdentifiedFiniteResource",
    "PhysicalSphere",
    "PhysicalStepCorrelation",
    "ProceduralEnvironmentScene",
    "StaticEnvironmentOwner",
    "StaticGroundPlane",
    "StaticPhysicalScene",
    "StaticSceneCandidate",
    "project_resource_geometry",
    "project_static_scene",
    "generate_procedural_environment",
]
