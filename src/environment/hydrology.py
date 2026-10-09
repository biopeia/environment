"""Pure one-tick surface-water relaxation for explicit Environment state.

The caller owns candidate-cell selection and supplies the environmental fields
and finite grid. This function has no World presence, death, or topology owner.
"""

from __future__ import annotations

import math
from collections.abc import Collection, Iterable, Mapping

from environment.spatial import HexCoord


def advance_surface_water(
    current_water: Mapping[HexCoord, float],
    active_cells: Iterable[HexCoord],
    valid_cells: Collection[HexCoord],
    *,
    moisture: Mapping[HexCoord, float],
    elevation: Mapping[HexCoord, float],
    permeability: Mapping[HexCoord, float],
    temperature: Mapping[HexCoord, float],
) -> dict[HexCoord, float]:
    """Return the source-compatible next sparse water field.

    ``active_cells`` must include cells whose other dynamic Environment state
    can affect the source active set (for example disturbance/detritus) and
    any explicit presence/death inputs chosen by the World caller. Existing
    water cells are included automatically. The candidate set is expanded by
    one in-bounds hex neighborhood, matching the source relaxation scope.

    Missing static fields use the historical ``DynamicGeography`` defaults:
    moisture/elevation/temperature 0.5 and permeability 0.8. The source update
    formula, thresholds, and 4-decimal rounding are retained. No host time,
    randomness, or causal tick is consulted.
    """
    bounds = set(valid_cells)
    seeds = set(active_cells)
    if not bounds:
        if current_water or seeds:
            raise ValueError("non-empty water state requires non-empty valid_cells")
        return {}

    water = _validated_field(current_water, "current_water", bounds)
    if not seeds.issubset(bounds):
        raise ValueError("active_cells must be within valid_cells")
    seeds.update(water)

    active = set(seeds)
    for cell in tuple(seeds):
        for direction in range(6):
            neighbor = cell.neighbor(direction)
            if neighbor in bounds:
                active.add(neighbor)

    moisture_values = _validated_field(moisture, "moisture", bounds)
    elevation_values = _validated_field(elevation, "elevation", bounds)
    permeability_values = _validated_field(permeability, "permeability", bounds)
    temperature_values = _validated_field(temperature, "temperature", bounds)

    next_water: dict[HexCoord, float] = {}
    for cell in active:
        cell_moisture = moisture_values.get(cell, 0.5)
        cell_elevation = elevation_values.get(cell, 0.5)
        cell_permeability = permeability_values.get(cell, 0.8)
        cell_temperature = temperature_values.get(cell, 0.5)
        equilibrium = max(
            0.0,
            (cell_moisture - 0.58)
            * (1.0 - 0.55 * cell_elevation)
            * cell_permeability,
        )
        value = water.get(cell, 0.0) + (equilibrium - water.get(cell, 0.0)) * 0.08
        value *= 1.0 - 0.025 * cell_temperature

        inflow = 0.0
        for direction in range(6):
            neighbor = cell.neighbor(direction)
            if neighbor not in bounds:
                continue
            neighbor_water = water.get(neighbor, 0.0)
            drop = elevation_values.get(neighbor, 0.5) - cell_elevation
            if drop > 0.0 and neighbor_water > value:
                inflow += min(0.015, drop * neighbor_water * 0.02)

        value = max(0.0, min(1.0, value + inflow))
        if value >= 0.002:
            next_water[cell] = round(value, 4)
    return next_water


def _validated_field(
    values: Mapping[HexCoord, float], name: str, bounds: set[HexCoord]
) -> dict[HexCoord, float]:
    result: dict[HexCoord, float] = {}
    for cell, raw_value in values.items():
        if cell not in bounds:
            raise ValueError(f"{name} contains a cell outside valid_cells")
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            raise ValueError(f"{name} values must be finite numbers")
        value = float(raw_value)
        if not math.isfinite(value):
            raise ValueError(f"{name} values must be finite numbers")
        result[cell] = value
    return result


__all__ = ["advance_surface_water"]
