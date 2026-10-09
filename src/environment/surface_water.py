"""Deterministic initial surface-water values derived from terrain fields.

This module covers initialization only. It does not model water transitions,
hydrology, persistence, or causal coordination.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from environment.spatial import HexCoord


def initialize_surface_water(
    width: int,
    height: int,
    *,
    moisture: Mapping[HexCoord, float],
    elevation: Mapping[HexCoord, float],
    permeability: Mapping[HexCoord, float],
) -> Mapping[HexCoord, float]:
    """Return initial water for a complete rectangular set of terrain fields.

    Every in-bounds cell must be present in each input mapping. This explicit
    requirement avoids inheriting the source runtime's implicit fallback and
    partial-override behavior. Input mappings are read only; the returned
    mapping contains only cells meeting the source threshold.
    """
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("width must be a positive integer")
    if isinstance(height, bool) or not isinstance(height, int) or height < 1:
        raise ValueError("height must be a positive integer")

    water: dict[HexCoord, float] = {}
    for q in range(width):
        for r in range(height):
            cell = HexCoord(q, r)
            if (
                cell not in moisture
                or cell not in elevation
                or cell not in permeability
            ):
                raise ValueError(
                    f"terrain fields must cover every grid cell; missing {cell}"
                )

            value = max(
                0.0,
                (moisture[cell] - 0.58)
                * (1.0 - 0.55 * elevation[cell])
                * permeability[cell],
            )
            if value >= 0.002:
                water[cell] = round(min(1.0, value), 4)

    return MappingProxyType(water)
