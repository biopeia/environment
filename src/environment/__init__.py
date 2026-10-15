"""Environment-owned external state and physical-scene capabilities."""

from environment.dynamic_state import (
    DynamicEnvironmentCandidate,
    DynamicEnvironmentOwner,
    DynamicObjectState,
)
from environment.identified_resource import (
    EnvironmentObservationContext,
    FINITE_SCALAR_FIELD_FAMILY_ID,
    FINITE_SCALAR_FIELD_SEMANTIC_REVISION,
    FiniteScalarFieldObservationProjection,
    FiniteScalarFieldSample,
    IdentifiedFiniteResource,
    IdentifiedFiniteScalarField,
    ResourceStateObservationProjection,
    project_committed_resource_state,
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
from environment.spatial_render import (
    canonical_spatial_render_scene_bytes,
    project_spatial_render_scene,
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
    "FINITE_SCALAR_FIELD_FAMILY_ID",
    "FINITE_SCALAR_FIELD_SEMANTIC_REVISION",
    "EnvironmentPhysicalProjection",
    "FiniteResourceState",
    "FiniteScalarFieldObservationProjection",
    "FiniteScalarFieldSample",
    "ResourceStateObservationProjection",
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
    "project_committed_resource_state",
    "project_spatial_render_scene",
    "canonical_spatial_render_scene_bytes",
    "project_static_scene",
]
