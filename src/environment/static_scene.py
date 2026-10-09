"""Environment-owned, explicit static 3D scene for physical-step fixtures.

This is a small target capability, not a universal scene schema. It has no
solver dependency and makes no assumptions about spatial indexing or terrain
generation. All lengths are metres and gravity is metres per second squared.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _vector3(value: tuple[float, float, float], name: str) -> tuple[float, float, float]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain three finite values")
    try:
        result = tuple(float(component) for component in value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must contain three finite values") from error
    if len(result) != 3 or not all(math.isfinite(component) for component in result):
        raise ValueError(f"{name} must contain three finite values")
    return result


@dataclass(frozen=True, slots=True)
class PhysicalStepCorrelation:
    """Local correlation value; this type does not make Environment a coordinator."""

    world_id: str
    causal_tick: int
    physical_step_id: str
    environment_id: str
    environment_revision: str

    def __post_init__(self) -> None:
        for field in ("world_id", "physical_step_id", "environment_id", "environment_revision"):
            _identity(getattr(self, field), field)
        if isinstance(self.causal_tick, bool) or not isinstance(self.causal_tick, int) or self.causal_tick < 0:
            raise ValueError("causal_tick must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class StaticGroundPlane:
    """Infinite plane ``normal · position = offset`` in the declared frame."""

    object_id: str
    normal: tuple[float, float, float]
    offset_m: float = 0.0

    def __post_init__(self) -> None:
        _identity(self.object_id, "object_id")
        normal = _vector3(self.normal, "normal")
        norm = math.sqrt(sum(component * component for component in normal))
        if not math.isfinite(norm) or not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("ground plane normal must be a unit vector")
        object.__setattr__(self, "normal", normal)
        if isinstance(self.offset_m, bool):
            raise ValueError("offset_m must be finite")
        try:
            offset = float(self.offset_m)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("offset_m must be finite") from error
        if not math.isfinite(offset):
            raise ValueError("offset_m must be finite")
        object.__setattr__(self, "offset_m", offset)


@dataclass(frozen=True, slots=True)
class StaticPhysicalScene:
    """Immutable Environment projection; numeric geometry is explicitly SI."""

    environment_id: str
    environment_revision: str
    frame_id: str
    gravity_m_s2: tuple[float, float, float]
    objects: tuple[StaticGroundPlane, ...]

    def __post_init__(self) -> None:
        for field in ("environment_id", "environment_revision", "frame_id"):
            _identity(getattr(self, field), field)
        object.__setattr__(self, "gravity_m_s2", _vector3(self.gravity_m_s2, "gravity_m_s2"))
        objects = tuple(self.objects)
        if not all(isinstance(item, StaticGroundPlane) for item in objects):
            raise ValueError("objects must contain StaticGroundPlane values")
        ids = [item.object_id for item in objects]
        if len(set(ids)) != len(ids):
            raise ValueError("object_id values must be unique within the scene")
        object.__setattr__(self, "objects", objects)


@dataclass(frozen=True, slots=True)
class StaticSceneCandidate:
    """Candidate that an owner may adopt only if static scene truth is unchanged."""

    correlation: PhysicalStepCorrelation
    scene: StaticPhysicalScene


def project_static_scene(scene: StaticPhysicalScene) -> StaticPhysicalScene:
    """Pure identity projection of Environment-owned immutable static state."""
    if not isinstance(scene, StaticPhysicalScene):
        raise ValueError("scene must be StaticPhysicalScene")
    # Canonical ordering ensures equivalent collection order has identical projection.
    return StaticPhysicalScene(
        environment_id=scene.environment_id,
        environment_revision=scene.environment_revision,
        frame_id=scene.frame_id,
        gravity_m_s2=scene.gravity_m_s2,
        objects=tuple(sorted(scene.objects, key=lambda item: item.object_id)),
    )


class StaticEnvironmentOwner:
    """Small owner boundary for a static scene and its recoverable step marker."""

    SCHEMA_VERSION = 1
    CHECKPOINT_SCHEMA = "environment-static-scene-v1"

    def __init__(self, scene: StaticPhysicalScene, owner_id: str) -> None:
        self._scene = project_static_scene(scene)
        self._owner_id = _identity(owner_id, "owner_id")
        self._last_adopted_tick = -1

    @property
    def owner_id(self) -> str:
        return self._owner_id

    @property
    def scene(self) -> StaticPhysicalScene:
        return self._scene

    @property
    def last_adopted_tick(self) -> int:
        return self._last_adopted_tick

    def validate_and_adopt(self, candidate: StaticSceneCandidate) -> None:
        """Adopt a no-op environmental transition, rejecting unsupported changes."""
        if not isinstance(candidate, StaticSceneCandidate):
            raise ValueError("candidate must be StaticSceneCandidate")
        correlation = candidate.correlation
        if (correlation.environment_id, correlation.environment_revision) != (
            self._scene.environment_id, self._scene.environment_revision
        ):
            raise ValueError("candidate correlation does not match active Environment identity/revision")
        if correlation.causal_tick != self._last_adopted_tick + 1:
            raise ValueError("candidate causal_tick is stale or not the next tick")
        if project_static_scene(candidate.scene) != self._scene:
            raise ValueError("static Environment owner rejects changed scene candidates")
        self._last_adopted_tick = correlation.causal_tick

    def checkpoint_bytes(self) -> bytes:
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "owner_id": self.owner_id,
            "last_adopted_tick": self._last_adopted_tick,
            "scene": {
                "environment_id": self._scene.environment_id,
                "environment_revision": self._scene.environment_revision,
                "frame_id": self._scene.frame_id,
                "gravity_m_s2": list(self._scene.gravity_m_s2),
                "objects": [
                    {"object_id": item.object_id, "normal": list(item.normal), "offset_m": item.offset_m}
                    for item in self._scene.objects
                ],
            },
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

    @classmethod
    def from_checkpoint_bytes(cls, encoded: bytes) -> StaticEnvironmentOwner:
        if not isinstance(encoded, bytes):
            raise ValueError("checkpoint must be bytes")
        try:
            payload: Any = json.loads(encoded)
            scene_data = payload["scene"]
            scene = StaticPhysicalScene(
                environment_id=scene_data["environment_id"],
                environment_revision=scene_data["environment_revision"],
                frame_id=scene_data["frame_id"],
                gravity_m_s2=tuple(scene_data["gravity_m_s2"]),
                objects=tuple(StaticGroundPlane(**item) for item in scene_data["objects"]),
            )
            tick = payload["last_adopted_tick"]
            owner_id = _identity(payload["owner_id"], "owner_id")
            if (
                payload["schema_version"] != cls.SCHEMA_VERSION
                or not isinstance(tick, int) or isinstance(tick, bool) or tick < -1
                or project_static_scene(scene) != scene
            ):
                raise ValueError("invalid static Environment checkpoint fields")
            restored = cls(scene, owner_id)
            restored._last_adopted_tick = tick
            return restored
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("invalid static Environment checkpoint") from error

    @classmethod
    def validate_checkpoint(cls, encoded: bytes, owner_identity: str, schema_version: str) -> bool:
        if schema_version != cls.CHECKPOINT_SCHEMA or not isinstance(encoded, bytes):
            return False
        try:
            return cls.from_checkpoint_bytes(encoded).owner_id == owner_identity
        except ValueError:
            return False


__all__ = [
    "PhysicalStepCorrelation", "StaticEnvironmentOwner", "StaticGroundPlane",
    "StaticPhysicalScene", "StaticSceneCandidate", "project_static_scene",
]
