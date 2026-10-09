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


def _dot(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _cross(left: tuple[float, float, float], right: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


@dataclass(frozen=True, slots=True)
class PhysicalStepCorrelation:
    """World-authorized correlation value; Environment does not mint authority."""

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
    """Infinite plane ``normal · position_m = offset_m`` in frame-local metres."""

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
class FrameDescriptor:
    """Explicit right-handed frame, with its basis expressed in a parent frame.

    Origin is metres from the parent origin. The basis vectors are unit axes
    expressed in the parent frame. ``up_axis`` names the positive local axis
    aligned to up. No global frame is implied by this descriptor.
    """

    frame_id: str
    parent_frame_id: str
    origin_m: tuple[float, float, float]
    x_axis_in_parent: tuple[float, float, float]
    y_axis_in_parent: tuple[float, float, float]
    z_axis_in_parent: tuple[float, float, float]
    handedness: str
    up_axis: str

    def __post_init__(self) -> None:
        _identity(self.frame_id, "frame_id")
        _identity(self.parent_frame_id, "parent_frame_id")
        object.__setattr__(self, "origin_m", _vector3(self.origin_m, "origin_m"))
        axes = []
        for field in ("x_axis_in_parent", "y_axis_in_parent", "z_axis_in_parent"):
            axis = _vector3(getattr(self, field), field)
            if not math.isclose(_dot(axis, axis), 1.0, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError(f"{field} must be a unit vector")
            axes.append(axis)
            object.__setattr__(self, field, axis)
        if any(not math.isclose(_dot(axes[i], axes[j]), 0.0, rel_tol=0.0, abs_tol=1e-9)
               for i, j in ((0, 1), (0, 2), (1, 2))):
            raise ValueError("frame axes must be orthogonal")
        if any(not math.isclose(a, b, rel_tol=0.0, abs_tol=1e-9)
               for a, b in zip(_cross(axes[0], axes[1]), axes[2], strict=True)):
            raise ValueError("frame axes must be right-handed")
        if self.handedness != "RIGHT_HANDED":
            raise ValueError("fixture frame handedness must be RIGHT_HANDED")
        if self.up_axis not in {"X", "Y", "Z"}:
            raise ValueError("up_axis must identify X, Y, or Z")


@dataclass(frozen=True, slots=True)
class StaticPhysicalScene:
    """Immutable Environment projection with geometry/gravity in the declared frame.

    Ground-plane normals and ``gravity_m_s2`` use frame-local axes; plane offsets
    and frame origins are metres. ``frame`` defines that frame's pose relative
    to its declared parent.
    """

    environment_id: str
    environment_revision: str
    frame: FrameDescriptor
    gravity_m_s2: tuple[float, float, float]
    objects: tuple[StaticGroundPlane, ...]

    def __post_init__(self) -> None:
        for field in ("environment_id", "environment_revision"):
            _identity(getattr(self, field), field)
        if not isinstance(self.frame, FrameDescriptor):
            raise ValueError("frame must be an explicit FrameDescriptor")
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
        frame=scene.frame,
        gravity_m_s2=scene.gravity_m_s2,
        objects=tuple(sorted(scene.objects, key=lambda item: item.object_id)),
    )


class StaticEnvironmentOwner:
    """Small owner boundary for a static scene and its recoverable step marker."""

    SCHEMA_VERSION = 2
    CHECKPOINT_SCHEMA = "environment-static-scene-v2"

    def __init__(self, scene: StaticPhysicalScene, owner_id: str) -> None:
        self._scene = project_static_scene(scene)
        self._owner_id = _identity(owner_id, "owner_id")
        self._last_accepted_correlation: PhysicalStepCorrelation | None = None

    @property
    def owner_id(self) -> str:
        return self._owner_id

    @property
    def scene(self) -> StaticPhysicalScene:
        return self._scene

    @property
    def last_adopted_tick(self) -> int:
        correlation = self._last_accepted_correlation
        return -1 if correlation is None else correlation.causal_tick

    @property
    def last_accepted_correlation(self) -> PhysicalStepCorrelation | None:
        return self._last_accepted_correlation

    def validate_and_adopt(
        self, candidate: StaticSceneCandidate, *, expected_correlation: PhysicalStepCorrelation
    ) -> None:
        """Adopt a no-op environmental transition, rejecting unsupported changes."""
        if not isinstance(candidate, StaticSceneCandidate):
            raise ValueError("candidate must be StaticSceneCandidate")
        if not isinstance(expected_correlation, PhysicalStepCorrelation):
            raise ValueError("expected_correlation must be World-authorized correlation")
        correlation = candidate.correlation
        if correlation != expected_correlation:
            raise ValueError("candidate correlation does not match World-authorized expected correlation")
        if (expected_correlation.environment_id, expected_correlation.environment_revision) != (
            self._scene.environment_id, self._scene.environment_revision
        ):
            raise ValueError("expected correlation does not match active Environment identity/revision")
        if expected_correlation.causal_tick != self.last_adopted_tick + 1:
            raise ValueError("candidate causal_tick is stale or not the next tick")
        if project_static_scene(candidate.scene) != self._scene:
            raise ValueError("static Environment owner rejects changed scene candidates")
        self._last_accepted_correlation = expected_correlation

    def checkpoint_bytes(self) -> bytes:
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "owner_id": self.owner_id,
            "last_accepted_correlation": (
                None if self._last_accepted_correlation is None else {
                    "world_id": self._last_accepted_correlation.world_id,
                    "causal_tick": self._last_accepted_correlation.causal_tick,
                    "physical_step_id": self._last_accepted_correlation.physical_step_id,
                    "environment_id": self._last_accepted_correlation.environment_id,
                    "environment_revision": self._last_accepted_correlation.environment_revision,
                }
            ),
            "scene": {
                "environment_id": self._scene.environment_id,
                "environment_revision": self._scene.environment_revision,
                "frame": {
                    "frame_id": self._scene.frame.frame_id,
                    "parent_frame_id": self._scene.frame.parent_frame_id,
                    "origin_m": list(self._scene.frame.origin_m),
                    "x_axis_in_parent": list(self._scene.frame.x_axis_in_parent),
                    "y_axis_in_parent": list(self._scene.frame.y_axis_in_parent),
                    "z_axis_in_parent": list(self._scene.frame.z_axis_in_parent),
                    "handedness": self._scene.frame.handedness,
                    "up_axis": self._scene.frame.up_axis,
                },
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
            frame_data = scene_data["frame"]
            frame = FrameDescriptor(
                frame_id=frame_data["frame_id"],
                parent_frame_id=frame_data["parent_frame_id"],
                origin_m=tuple(frame_data["origin_m"]),
                x_axis_in_parent=tuple(frame_data["x_axis_in_parent"]),
                y_axis_in_parent=tuple(frame_data["y_axis_in_parent"]),
                z_axis_in_parent=tuple(frame_data["z_axis_in_parent"]),
                handedness=frame_data["handedness"],
                up_axis=frame_data["up_axis"],
            )
            scene = StaticPhysicalScene(
                environment_id=scene_data["environment_id"],
                environment_revision=scene_data["environment_revision"],
                frame=frame,
                gravity_m_s2=tuple(scene_data["gravity_m_s2"]),
                objects=tuple(StaticGroundPlane(**item) for item in scene_data["objects"]),
            )
            raw_correlation = payload["last_accepted_correlation"]
            owner_id = _identity(payload["owner_id"], "owner_id")
            if payload["schema_version"] != cls.SCHEMA_VERSION or project_static_scene(scene) != scene:
                raise ValueError("invalid static Environment checkpoint fields")
            restored = cls(scene, owner_id)
            if raw_correlation is not None:
                correlation = PhysicalStepCorrelation(**raw_correlation)
                if (correlation.environment_id, correlation.environment_revision) != (
                    scene.environment_id, scene.environment_revision
                ):
                    raise ValueError("checkpoint correlation does not match scene identity/revision")
                restored._last_accepted_correlation = correlation
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
    "FrameDescriptor", "PhysicalStepCorrelation", "StaticEnvironmentOwner", "StaticGroundPlane",
    "StaticPhysicalScene", "StaticSceneCandidate", "project_static_scene",
]
