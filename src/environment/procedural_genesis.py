"""Deterministic, narrowly scoped procedural Environment genesis.

This target-authored generator creates a static ground plane plus a bounded
set of spherical physical geometry. It is one genesis capability, not a
universal Environment representation or a solver scene format.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from environment.static_scene import (
    EnvironmentGenesisProvenance,
    FrameDescriptor,
    StaticGroundPlane,
    StaticPhysicalScene,
    StaticSphere,
)


GENERATOR_ID = "biopeia.environment.sha256-sphere-layout"
GENERATOR_REVISION = "1"


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _vector3(value: tuple[float, float, float], name: str) -> tuple[float, float, float]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain three finite values")
    try:
        components = tuple(value)
        if any(isinstance(component, bool) for component in components):
            raise ValueError(f"{name} must contain three finite values")
        result = tuple(float(component) for component in components)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must contain three finite values") from error
    if len(result) != 3 or not all(math.isfinite(component) for component in result):
        raise ValueError(f"{name} must contain three finite values")
    return result


@dataclass(frozen=True, slots=True)
class EnvironmentGenesisConfig:
    """Explicit inputs for the versioned sphere-layout generator.

    Bounds and radii are in metres local to ``frame``. The generator assigns
    coordinates by a stable digest; it makes no guarantee of non-overlap,
    terrain quality, ecological meaning, or scientific suitability.
    """

    environment_id: str
    environment_revision: str
    frame: FrameDescriptor
    gravity_m_s2: tuple[float, float, float]
    ground_plane: StaticGroundPlane
    bounds_min_m: tuple[float, float, float]
    bounds_max_m: tuple[float, float, float]
    sphere_count: int
    minimum_radius_m: float
    maximum_radius_m: float

    def __post_init__(self) -> None:
        _identity(self.environment_id, "environment_id")
        _identity(self.environment_revision, "environment_revision")
        if not isinstance(self.frame, FrameDescriptor):
            raise ValueError("frame must be an explicit FrameDescriptor")
        if not isinstance(self.ground_plane, StaticGroundPlane):
            raise ValueError("ground_plane must be a StaticGroundPlane")
        gravity = _vector3(self.gravity_m_s2, "gravity_m_s2")
        object.__setattr__(self, "gravity_m_s2", gravity)
        lower = _vector3(self.bounds_min_m, "bounds_min_m")
        upper = _vector3(self.bounds_max_m, "bounds_max_m")
        if any(lo >= hi for lo, hi in zip(lower, upper, strict=True)):
            raise ValueError("each bounds_min_m component must be below bounds_max_m")
        object.__setattr__(self, "bounds_min_m", lower)
        object.__setattr__(self, "bounds_max_m", upper)
        if isinstance(self.sphere_count, bool) or not isinstance(self.sphere_count, int) or self.sphere_count < 0:
            raise ValueError("sphere_count must be a non-negative integer")
        for field_name in ("minimum_radius_m", "maximum_radius_m"):
            value = getattr(self, field_name)
            if isinstance(value, bool):
                raise ValueError(f"{field_name} must be finite and positive")
            try:
                value = float(value)
            except (TypeError, ValueError, OverflowError) as error:
                raise ValueError(f"{field_name} must be finite and positive") from error
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{field_name} must be finite and positive")
            object.__setattr__(self, field_name, value)
        if self.minimum_radius_m > self.maximum_radius_m:
            raise ValueError("minimum_radius_m must not exceed maximum_radius_m")


@dataclass(frozen=True, slots=True)
class EnvironmentGenesisSpec:
    """Reproducible invocation of one identified Environment generator."""

    environment_seed: int
    generator_id: str
    generator_revision: str
    configuration: EnvironmentGenesisConfig

    def __post_init__(self) -> None:
        if isinstance(self.environment_seed, bool) or not isinstance(self.environment_seed, int):
            raise ValueError("environment_seed must be an integer")
        _identity(self.generator_id, "generator_id")
        _identity(self.generator_revision, "generator_revision")
        if not isinstance(self.configuration, EnvironmentGenesisConfig):
            raise ValueError("configuration must be EnvironmentGenesisConfig")


@dataclass(frozen=True, slots=True)
class ProceduralEnvironmentScene:
    """Wrapper around generated authoritative Environment scene state."""

    scene: StaticPhysicalScene

    def __post_init__(self) -> None:
        if not isinstance(self.scene, StaticPhysicalScene):
            raise ValueError("scene must be a StaticPhysicalScene")


def _canonical_spec(spec: EnvironmentGenesisSpec) -> bytes:
    config = spec.configuration
    frame = config.frame
    payload = {
        "environment_seed": spec.environment_seed,
        "generator_id": spec.generator_id,
        "generator_revision": spec.generator_revision,
        "configuration": {
            "environment_id": config.environment_id,
            "environment_revision": config.environment_revision,
            "frame": {
                "frame_id": frame.frame_id,
                "parent_frame_id": frame.parent_frame_id,
                "origin_m": frame.origin_m,
                "x_axis_in_parent": frame.x_axis_in_parent,
                "y_axis_in_parent": frame.y_axis_in_parent,
                "z_axis_in_parent": frame.z_axis_in_parent,
                "handedness": frame.handedness,
                "up_axis": frame.up_axis,
            },
            "gravity_m_s2": config.gravity_m_s2,
            "ground_plane": {
                "object_id": config.ground_plane.object_id,
                "normal": config.ground_plane.normal,
                "offset_m": config.ground_plane.offset_m,
            },
            "bounds_min_m": config.bounds_min_m,
            "bounds_max_m": config.bounds_max_m,
            "sphere_count": config.sphere_count,
            "minimum_radius_m": config.minimum_radius_m,
            "maximum_radius_m": config.maximum_radius_m,
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _unit_interval(digest: bytes, axis: int) -> float:
    start = axis * 8
    integer = int.from_bytes(digest[start : start + 8], "big", signed=False)
    return integer / ((1 << 64) - 1)


def generate_procedural_environment(spec: EnvironmentGenesisSpec) -> ProceduralEnvironmentScene:
    """Generate one deterministic bounded 3D sphere layout.

    For this exact generator identity and revision, equal complete specs yield
    equal scenes. The algorithm uses only SHA-256 over explicit inputs and
    object indices; it does not read host time, process state, or global RNG.
    This does not promise cross-revision equivalence or a universal scene model.
    """

    if not isinstance(spec, EnvironmentGenesisSpec):
        raise TypeError("spec must be EnvironmentGenesisSpec")
    if (spec.generator_id, spec.generator_revision) != (GENERATOR_ID, GENERATOR_REVISION):
        raise ValueError("unsupported Environment generator identity/revision")
    config = spec.configuration
    canonical = _canonical_spec(spec)
    lower, upper = config.bounds_min_m, config.bounds_max_m
    spheres: list[StaticSphere] = []
    for index in range(config.sphere_count):
        digest = hashlib.sha256(canonical + b"\x00object\x00" + index.to_bytes(8, "big")).digest()
        unit = tuple(_unit_interval(digest, axis) for axis in range(4))
        center = tuple(lo + (hi - lo) * unit[axis] for axis, (lo, hi) in enumerate(zip(lower, upper, strict=True)))
        radius = config.minimum_radius_m + (config.maximum_radius_m - config.minimum_radius_m) * unit[3]
        spheres.append(StaticSphere(f"sphere-{index:06d}", center, radius, config.frame.frame_id))
    genesis_configuration = json.loads(_canonical_spec(spec))["configuration"]
    scene = StaticPhysicalScene(
        environment_id=config.environment_id,
        environment_revision=config.environment_revision,
        frame=config.frame,
        gravity_m_s2=config.gravity_m_s2,
        objects=(config.ground_plane,),
        spheres=tuple(spheres),
        genesis=EnvironmentGenesisProvenance.from_configuration(
            environment_seed=spec.environment_seed,
            generator_id=spec.generator_id,
            generator_revision=spec.generator_revision,
            configuration=genesis_configuration,
        ),
    )
    return ProceduralEnvironmentScene(scene=scene)


__all__ = [
    "GENERATOR_ID",
    "GENERATOR_REVISION",
    "EnvironmentGenesisConfig",
    "EnvironmentGenesisSpec",
    "ProceduralEnvironmentScene",
    "generate_procedural_environment",
]
