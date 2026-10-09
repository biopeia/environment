"""Pure substrate response to a caller-supplied directional impulse.

This is a bounded extraction of current software behavior, not a physical law
or a definition of how a body/solver produces an impulse.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from environment.spatial import HexCoord


@dataclass(frozen=True, slots=True)
class SubstrateImpulseResult:
    origin: HexCoord
    target: HexCoord
    magnitude: float
    water_transferred: float
    detritus_transferred: float
    origin_disturbance_added: float
    target_disturbance_added: float


@dataclass(frozen=True, slots=True)
class SubstrateImpulseTransition:
    """New sparse field maps and report; input maps are never mutated."""

    result: SubstrateImpulseResult
    surface_water: Mapping[HexCoord, float]
    detritus: Mapping[HexCoord, float]
    disturbance: Mapping[HexCoord, float]


def apply_substrate_impulse(
    *,
    width: int,
    height: int,
    origin: HexCoord,
    target: HexCoord,
    magnitude: float,
    elevation: Mapping[HexCoord, float],
    permeability: Mapping[HexCoord, float],
    surface_water: Mapping[HexCoord, float],
    detritus: Mapping[HexCoord, float],
    disturbance: Mapping[HexCoord, float],
) -> SubstrateImpulseTransition:
    """Compute the source substrate response for an explicit grid transition.

    The source accepts a finite magnitude and clamps it to ``[0, 1]``. A
    self-target or target outside the supplied rectangular grid disturbs only
    the origin. Missing field values retain source accessor defaults. The
    function does not infer origin/target from motion, validate physical units,
    or assert that these coefficients are scientifically calibrated.
    """
    if width < 1 or height < 1:
        raise ValueError("grid dimensions must be positive")
    magnitude = float(magnitude)
    if not math.isfinite(magnitude):
        raise ValueError("magnitude must be finite")
    magnitude = max(0.0, min(1.0, magnitude))

    water_next = dict(surface_water)
    detritus_next = dict(detritus)
    disturbance_next = dict(disturbance)
    origin_disturbance = 0.08 * magnitude
    disturbance_next[origin] = min(
        1.0, disturbance_next.get(origin, 0.0) + origin_disturbance
    )

    target_is_valid = 0 <= target.q < width and 0 <= target.r < height
    if target == origin or not target_is_valid:
        result = SubstrateImpulseResult(
            origin,
            origin,
            magnitude,
            0.0,
            0.0,
            origin_disturbance,
            0.0,
        )
        return SubstrateImpulseTransition(
            result,
            MappingProxyType(water_next),
            MappingProxyType(detritus_next),
            MappingProxyType(disturbance_next),
        )

    uphill = max(
        0.0, elevation.get(target, 0.5) - elevation.get(origin, 0.5)
    )
    resistance = max(0.15, 1.0 - 1.5 * uphill)
    target_permeability = max(0.05, permeability.get(target, 0.8))
    transfer_factor = magnitude * resistance * target_permeability

    origin_water = surface_water.get(origin, 0.0)
    water_transfer = min(origin_water, 0.10 * transfer_factor)
    if water_transfer > 0.0:
        water_next[origin] = max(0.0, origin_water - water_transfer)
        water_next[target] = min(
            1.0, surface_water.get(target, 0.0) + water_transfer
        )

    origin_detritus = detritus.get(origin, 0.0)
    detritus_transfer = min(origin_detritus, 0.06 * transfer_factor)
    if detritus_transfer > 0.0:
        detritus_next[origin] = max(0.0, origin_detritus - detritus_transfer)
        detritus_next[target] = min(
            1.0, detritus.get(target, 0.0) + detritus_transfer
        )

    target_disturbance = 0.04 * magnitude
    disturbance_next[target] = min(
        1.0, disturbance_next.get(target, 0.0) + target_disturbance
    )
    result = SubstrateImpulseResult(
        origin,
        target,
        magnitude,
        water_transfer,
        detritus_transfer,
        origin_disturbance,
        target_disturbance,
    )
    return SubstrateImpulseTransition(
        result,
        MappingProxyType(water_next),
        MappingProxyType(detritus_next),
        MappingProxyType(disturbance_next),
    )
