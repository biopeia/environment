"""Finite environmental resource state independent of a physics engine.

This model owns the resource's objective quantity and scalar spatial field.
Contact detection and geometry construction belong to a physical substrate;
the consumer reports only the amount it actually accepted.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class FiniteResourceState:
    """A finite, static source with a bounded local scalar field.

    The field communicates magnitude only. This class does not determine
    contact, cause an organism action, or assign meaning to the resource.
    """

    position: tuple[float, float, float] = (3.0, 0.0, 0.18)
    radius: float = 0.18
    field_radius: float = 6.0
    remaining: float = 200.0
    transfer_per_tick: float = 2.0

    CHECKPOINT_TYPE = "biopeia.environment.finite-resource-state"
    CHECKPOINT_VERSION = 1

    def __post_init__(self) -> None:
        self.position = _finite_vector(self.position, "position")
        self.radius = _positive_finite(self.radius, "radius")
        self.field_radius = _positive_finite(self.field_radius, "field_radius")
        self.remaining = _nonnegative_finite(self.remaining, "remaining")
        self.transfer_per_tick = _positive_finite(
            self.transfer_per_tick, "transfer_per_tick"
        )
        if self.field_radius <= self.radius:
            raise ValueError("field_radius must exceed radius")

    def distance_to(self, point: Sequence[float]) -> float:
        point_vector = _finite_vector(point, "point")
        squared_distance = sum(
            (coordinate - origin) ** 2
            for coordinate, origin in zip(point_vector, self.position)
        )
        return math.sqrt(squared_distance)

    def field_at(self, point: Sequence[float]) -> float:
        """Return a local scalar that vanishes when the resource is depleted."""
        if self.remaining <= 0.0:
            return 0.0
        distance = self.distance_to(point)
        if distance >= self.field_radius:
            return 0.0
        normalized = max(0.0, 1.0 - distance / self.field_radius)
        return normalized * normalized

    def offered_material(self) -> float:
        """Return the bounded quantity available for one caller-defined tick."""
        if self.remaining <= 0.0:
            return 0.0
        return min(self.transfer_per_tick, self.remaining)

    def consume_absorbed(self, amount: float) -> float:
        """Debit only accepted material; return the amount actually removed."""
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or not math.isfinite(float(amount))
            or amount < 0.0
        ):
            raise ValueError("absorbed resource amount must be finite and non-negative")
        consumed = min(float(amount), self.remaining, self.transfer_per_tick)
        self.remaining -= consumed
        return consumed

    def checkpoint(self) -> dict[str, object]:
        """Serialize this state using the Biopeia-owned checkpoint contract."""
        return {
            "checkpoint_type": self.CHECKPOINT_TYPE,
            "checkpoint_version": self.CHECKPOINT_VERSION,
            "position": [float(value) for value in self.position],
            "radius": float(self.radius),
            "field_radius": float(self.field_radius),
            "remaining": float(self.remaining),
            "transfer_per_tick": float(self.transfer_per_tick),
        }

    @classmethod
    def from_checkpoint(
        cls, payload: Mapping[str, Any]
    ) -> "FiniteResourceState":
        """Restore only the explicitly versioned Biopeia-owned state shape."""
        expected_keys = {
            "checkpoint_type",
            "checkpoint_version",
            "position",
            "radius",
            "field_radius",
            "remaining",
            "transfer_per_tick",
        }
        if (
            not isinstance(payload, Mapping)
            or set(payload) != expected_keys
            or payload.get("checkpoint_type") != cls.CHECKPOINT_TYPE
            or isinstance(payload.get("checkpoint_version"), bool)
            or payload.get("checkpoint_version") != cls.CHECKPOINT_VERSION
        ):
            raise ValueError("unsupported finite resource checkpoint contract")
        return cls(
            position=_finite_vector(payload["position"], "position"),
            radius=float(payload["radius"]),
            field_radius=float(payload["field_radius"]),
            remaining=float(payload["remaining"]),
            transfer_per_tick=float(payload["transfer_per_tick"]),
        )


def _finite_vector(value: Sequence[float], name: str) -> tuple[float, float, float]:
    if isinstance(value, (str, bytes)) or len(value) != 3:
        raise ValueError(f"{name} must contain exactly three finite coordinates")
    vector = tuple(float(coordinate) for coordinate in value)
    if not all(math.isfinite(coordinate) for coordinate in vector):
        raise ValueError(f"{name} must contain exactly three finite coordinates")
    return vector


def _positive_finite(value: float, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return result


def _nonnegative_finite(value: float, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


__all__ = ["FiniteResourceState"]
