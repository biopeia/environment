"""Environment-owned external state and physical-scene capabilities."""

from environment.dynamic_state import (
    DynamicEnvironmentCandidate,
    DynamicEnvironmentOwner,
    DynamicObjectState,
)
from environment.identified_resource import (
    EnvironmentObservationContext,
    FiniteScalarFieldObservationProjection,
    FiniteScalarFieldSample,
    IdentifiedFiniteResource,
    IdentifiedFiniteScalarField,
)
from environment.physical import PhysicalSphere, project_resource_geometry
from environment.procedural_genesis import (
    GENERATOR_ID,
    GENERATOR_REVISION,
    EnvironmentGenesisConfig,
    EnvironmentGenesisSpec,
    ProceduralEnvironmentScene,
    generate_procedural_environment,
)
from environment.resource import FiniteResourceState
from environment.restoration import OwnerRestorationReference
from environment.static_scene import (
    EnvironmentGenesisProvenance,
    EnvironmentPhysicalProjection,
    FrameDescriptor,
    PhysicalStepCorrelation,
    StaticEnvironmentOwner,
    StaticGroundPlane,
    StaticPhysicalScene,
    StaticSceneCandidate,
    StaticSphere,
    project_static_scene,
)

__all__ = [
    "GENERATOR_ID",
    "GENERATOR_REVISION",
    "DynamicEnvironmentCandidate",
    "DynamicEnvironmentOwner",
    "DynamicObjectState",
    "EnvironmentGenesisConfig",
    "EnvironmentGenesisProvenance",
    "EnvironmentGenesisSpec",
    "EnvironmentObservationContext",
    "EnvironmentPhysicalProjection",
    "FiniteResourceState",
    "FiniteScalarFieldObservationProjection",
    "FiniteScalarFieldSample",
    "FrameDescriptor",
    "IdentifiedFiniteResource",
    "IdentifiedFiniteScalarField",
    "OwnerRestorationReference",
    "PhysicalSphere",
    "PhysicalStepCorrelation",
    "ProceduralEnvironmentScene",
    "StaticEnvironmentOwner",
    "StaticGroundPlane",
    "StaticPhysicalScene",
    "StaticSceneCandidate",
    "StaticSphere",
    "generate_procedural_environment",
    "project_resource_geometry",
    "project_static_scene",
]
