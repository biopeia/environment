"""Bounded, read-only Environment geometry projection for local rendering.

This module projects only owner-authored static planes and spheres. It does not
publish, transport, infer a causal cut, or establish compatibility with another
domain's coordinate frame.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

import rfc8785

from environment.static_scene import StaticPhysicalScene

SCHEMA_VERSION = 1
MAX_ITEMS = 128
MAX_TEXT_BYTES = 128
MAX_DESCRIPTOR_BYTES = 65_536


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise ValueError(f"{field} must be valid Unicode") from error
    if len(encoded) > MAX_TEXT_BYTES:
        raise ValueError(f"{field} exceeds {MAX_TEXT_BYTES} UTF-8 bytes")
    if any(ord(char) <= 0x1F or 0x7F <= ord(char) <= 0x9F for char in value):
        raise ValueError(f"{field} must not contain control characters")
    return value


def _finite(value: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{field} must be a finite number") from error
    if not math.isfinite(result):
        raise ValueError(f"{field} must be a finite number")
    return result


def _vector(value: tuple[float, float, float], field: str) -> list[float]:
    if len(value) != 3:
        raise ValueError(f"{field} must contain exactly three values")
    return [_finite(component, field) for component in value]


def project_spatial_render_scene(scene: StaticPhysicalScene) -> dict[str, Any]:
    """Return the candidate v1 descriptor for the supplied Environment scene.

    The result is detached JSON-compatible data. It includes no dynamic state,
    solver parameters, genesis inputs, or World identity/cut claims.
    """
    if not isinstance(scene, StaticPhysicalScene):
        raise ValueError("scene must be StaticPhysicalScene")

    frame = scene.frame
    frame_payload = {
        "frame_id": _text(frame.frame_id, "frame.frame_id"),
        "parent_frame_id": _text(frame.parent_frame_id, "frame.parent_frame_id"),
        "origin_m": _vector(frame.origin_m, "frame.origin_m"),
        "x_axis_in_parent": _vector(frame.x_axis_in_parent, "frame.x_axis_in_parent"),
        "y_axis_in_parent": _vector(frame.y_axis_in_parent, "frame.y_axis_in_parent"),
        "z_axis_in_parent": _vector(frame.z_axis_in_parent, "frame.z_axis_in_parent"),
        "handedness": frame.handedness,
        "up_axis": frame.up_axis,
    }

    item_rows: list[tuple[bytes, dict[str, Any]]] = []
    for plane in scene.objects:
        object_id = _text(plane.object_id, "object_id")
        item_rows.append((object_id.encode("utf-8"), {
            "object_id": object_id,
            "kind": "ground_plane",
            "frame_id": frame_payload["frame_id"],
            "normal": _vector(plane.normal, "normal"),
            "offset_m": _finite(plane.offset_m, "offset_m"),
        }))
    for sphere in scene.spheres:
        object_id = _text(sphere.object_id, "object_id")
        if sphere.frame_id != frame_payload["frame_id"]:
            raise ValueError("sphere frame_id must match the scene frame")
        radius = _finite(sphere.radius_m, "radius_m")
        if radius <= 0:
            raise ValueError("radius_m must be positive")
        item_rows.append((object_id.encode("utf-8"), {
            "object_id": object_id,
            "kind": "sphere",
            "frame_id": _text(sphere.frame_id, "frame_id"),
            "center_m": _vector(sphere.center_m, "center_m"),
            "radius_m": radius,
        }))
    item_rows.sort(key=lambda row: row[0])
    if len(item_rows) > MAX_ITEMS:
        raise ValueError(f"scene exceeds the {MAX_ITEMS}-item render bound")
    if len({item_id for item_id, _ in item_rows}) != len(item_rows):
        raise ValueError("object_id values must be unique")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "environment_id": _text(scene.environment_id, "environment_id"),
        "environment_revision": _text(scene.environment_revision, "environment_revision"),
        "length_unit": "m",
        "frame": frame_payload,
        "items": [item for _, item in item_rows],
    }
    payload["render_geometry_sha256"] = hashlib.sha256(rfc8785.dumps(payload)).hexdigest()
    if len(rfc8785.dumps(payload)) > MAX_DESCRIPTOR_BYTES:
        raise ValueError(f"descriptor exceeds {MAX_DESCRIPTOR_BYTES} UTF-8 bytes")
    return payload


def canonical_spatial_render_scene_bytes(scene: StaticPhysicalScene) -> bytes:
    """Encode a projected descriptor as RFC 8785 canonical UTF-8 bytes."""
    return rfc8785.dumps(project_spatial_render_scene(scene))
