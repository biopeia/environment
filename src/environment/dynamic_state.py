"""Environment-owned dynamic state fixture with explicit owner adoption.

This module demonstrates a bounded state transition contract. It does not
define environmental laws, solve physics, or claim that a candidate was
physically calibrated. Positions are metres in the object's declared frame.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from environment.static_scene import FrameDescriptor, PhysicalStepCorrelation


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _vector3(value: tuple[float, float, float], name: str) -> tuple[float, float, float]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain three finite values")
    try:
        components = tuple(value)
        if len(components) != 3 or any(isinstance(component, bool) for component in components):
            raise ValueError(f"{name} must contain three finite values")
        result = tuple(float(component) for component in components)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must contain three finite values") from error
    if not all(math.isfinite(component) for component in result):
        raise ValueError(f"{name} must contain three finite values")
    return result


@dataclass(frozen=True, slots=True)
class DynamicObjectState:
    object_id: str
    frame_id: str
    position_m: tuple[float, float, float]

    def __post_init__(self) -> None:
        _identity(self.object_id, "object_id")
        _identity(self.frame_id, "frame_id")
        object.__setattr__(self, "position_m", _vector3(self.position_m, "position_m"))


@dataclass(frozen=True, slots=True)
class DynamicEnvironmentCandidate:
    correlation: PhysicalStepCorrelation
    object_state: DynamicObjectState


class DynamicEnvironmentOwner:
    """Adopts one stable object's candidate state and checkpoints it strictly."""

    SCHEMA_VERSION = 1
    CHECKPOINT_SCHEMA = "environment-dynamic-object-v1"

    def __init__(
        self,
        *,
        owner_id: str,
        environment_id: str,
        environment_revision: str,
        frame: FrameDescriptor,
        object_state: DynamicObjectState,
    ) -> None:
        self._owner_id = _identity(owner_id, "owner_id")
        self._environment_id = _identity(environment_id, "environment_id")
        self._environment_revision = _identity(environment_revision, "environment_revision")
        if not isinstance(frame, FrameDescriptor):
            raise ValueError("frame must be an explicit FrameDescriptor")
        self._frame = frame
        if not isinstance(object_state, DynamicObjectState):
            raise ValueError("object_state must be DynamicObjectState")
        if object_state.frame_id != frame.frame_id:
            raise ValueError("object_state frame_id must match the declared FrameDescriptor")
        self._object_state = object_state
        self._last_accepted_correlation: PhysicalStepCorrelation | None = None

    @property
    def owner_id(self) -> str:
        return self._owner_id

    @property
    def environment_id(self) -> str:
        return self._environment_id

    @property
    def environment_revision(self) -> str:
        return self._environment_revision

    @property
    def object_state(self) -> DynamicObjectState:
        return self._object_state

    @property
    def frame(self) -> FrameDescriptor:
        return self._frame

    @property
    def last_accepted_correlation(self) -> PhysicalStepCorrelation | None:
        return self._last_accepted_correlation

    def validate_and_adopt(
        self,
        candidate: DynamicEnvironmentCandidate,
        *,
        expected_correlation: PhysicalStepCorrelation,
    ) -> None:
        if not isinstance(candidate, DynamicEnvironmentCandidate):
            raise ValueError("candidate must be DynamicEnvironmentCandidate")
        if not isinstance(expected_correlation, PhysicalStepCorrelation):
            raise ValueError("expected_correlation must be World-authorized correlation")
        correlation = candidate.correlation
        if correlation != expected_correlation:
            raise ValueError("candidate correlation does not match World-authorized expected correlation")
        if (correlation.environment_id, correlation.environment_revision) != (
            self.environment_id, self.environment_revision
        ):
            raise ValueError("candidate does not match active Environment identity/revision")
        if correlation.causal_tick != self.last_adopted_tick + 1:
            raise ValueError("candidate causal_tick is stale or not the next tick")
        proposed = candidate.object_state
        if not isinstance(proposed, DynamicObjectState):
            raise ValueError("candidate object_state must be DynamicObjectState")
        if (proposed.object_id, proposed.frame_id) != (
            self.object_state.object_id, self.object_state.frame_id
        ):
            raise ValueError("candidate object identity/frame does not match active Environment state")
        if proposed.frame_id != self.frame.frame_id:
            raise ValueError("candidate frame does not match the declared Environment FrameDescriptor")
        # Candidate value construction already rejects non-finite values; repeat
        # the check at the adoption boundary to fail closed on malformed objects.
        if not all(math.isfinite(value) for value in proposed.position_m):
            raise ValueError("candidate position_m must be finite")
        self._object_state = proposed
        self._last_accepted_correlation = correlation

    @property
    def last_adopted_tick(self) -> int:
        correlation = self._last_accepted_correlation
        return -1 if correlation is None else correlation.causal_tick

    def checkpoint_bytes(self) -> bytes:
        correlation = self.last_accepted_correlation
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "owner_id": self.owner_id,
            "environment_id": self.environment_id,
            "environment_revision": self.environment_revision,
            "frame": {
                "frame_id": self.frame.frame_id,
                "parent_frame_id": self.frame.parent_frame_id,
                "origin_m": list(self.frame.origin_m),
                "x_axis_in_parent": list(self.frame.x_axis_in_parent),
                "y_axis_in_parent": list(self.frame.y_axis_in_parent),
                "z_axis_in_parent": list(self.frame.z_axis_in_parent),
                "handedness": self.frame.handedness,
                "up_axis": self.frame.up_axis,
            },
            "object_state": {
                "object_id": self.object_state.object_id,
                "frame_id": self.object_state.frame_id,
                "position_m": list(self.object_state.position_m),
            },
            "last_accepted_correlation": None if correlation is None else {
                "world_id": correlation.world_id,
                "causal_tick": correlation.causal_tick,
                "physical_step_id": correlation.physical_step_id,
                "environment_id": correlation.environment_id,
                "environment_revision": correlation.environment_revision,
            },
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

    @classmethod
    def from_checkpoint_bytes(cls, encoded: bytes) -> DynamicEnvironmentOwner:
        if not isinstance(encoded, bytes):
            raise ValueError("invalid dynamic Environment checkpoint")
        try:
            payload: Any = json.loads(encoded)
            if not isinstance(payload, dict) or set(payload) != {
                "schema_version", "owner_id", "environment_id", "environment_revision",
                "frame", "object_state", "last_accepted_correlation",
            }:
                raise ValueError("invalid checkpoint fields")
            if type(payload["schema_version"]) is not int or payload["schema_version"] != cls.SCHEMA_VERSION:
                raise ValueError("unsupported checkpoint schema")
            object_data = payload["object_state"]
            if not isinstance(object_data, dict) or set(object_data) != {"object_id", "frame_id", "position_m"}:
                raise ValueError("invalid object checkpoint fields")
            frame_data = payload["frame"]
            if not isinstance(frame_data, dict) or set(frame_data) != {
                "frame_id", "parent_frame_id", "origin_m", "x_axis_in_parent", "y_axis_in_parent",
                "z_axis_in_parent", "handedness", "up_axis",
            }:
                raise ValueError("invalid frame checkpoint fields")
            owner = cls(
                owner_id=payload["owner_id"],
                environment_id=payload["environment_id"],
                environment_revision=payload["environment_revision"],
                frame=FrameDescriptor(
                    frame_id=frame_data["frame_id"],
                    parent_frame_id=frame_data["parent_frame_id"],
                    origin_m=tuple(frame_data["origin_m"]),
                    x_axis_in_parent=tuple(frame_data["x_axis_in_parent"]),
                    y_axis_in_parent=tuple(frame_data["y_axis_in_parent"]),
                    z_axis_in_parent=tuple(frame_data["z_axis_in_parent"]),
                    handedness=frame_data["handedness"],
                    up_axis=frame_data["up_axis"],
                ),
                object_state=DynamicObjectState(**object_data),
            )
            raw_correlation = payload["last_accepted_correlation"]
            if raw_correlation is not None:
                expected_fields = {
                    "world_id", "causal_tick", "physical_step_id", "environment_id", "environment_revision"
                }
                if not isinstance(raw_correlation, dict) or set(raw_correlation) != expected_fields:
                    raise ValueError("invalid correlation checkpoint fields")
                correlation = PhysicalStepCorrelation(**raw_correlation)
                if (correlation.environment_id, correlation.environment_revision) != (
                    owner.environment_id, owner.environment_revision
                ):
                    raise ValueError("checkpoint correlation does not match Environment identity/revision")
                owner._last_accepted_correlation = correlation
            return owner
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("invalid dynamic Environment checkpoint") from error

    @classmethod
    def validate_checkpoint(cls, encoded: bytes, owner_identity: str, schema_version: str) -> bool:
        if schema_version != cls.CHECKPOINT_SCHEMA or not isinstance(encoded, bytes):
            return False
        try:
            return cls.from_checkpoint_bytes(encoded).owner_id == owner_identity
        except ValueError:
            return False


__all__ = ["DynamicEnvironmentCandidate", "DynamicEnvironmentOwner", "DynamicObjectState"]
