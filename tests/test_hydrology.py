from __future__ import annotations

import pytest

from environment.hydrology import advance_surface_water
from environment.spatial import HexCoord


def _fields(cells: set[HexCoord], **overrides: float) -> dict[str, dict[HexCoord, float]]:
    defaults = {
        "moisture": 0.5,
        "elevation": 0.5,
        "permeability": 0.8,
        "temperature": 0.5,
    }
    return {
        name: {cell: overrides.get(name, default) for cell in cells}
        for name, default in defaults.items()
    }


def test_relaxes_water_toward_equilibrium_and_keeps_source_rounding() -> None:
    cell = HexCoord(0, 0)
    fields = _fields({cell}, moisture=0.9, elevation=0.2, permeability=0.9, temperature=0.3)

    result = advance_surface_water(
        {}, [cell], {cell}, **fields
    )

    assert result == {cell: 0.0204}


def test_expands_active_set_by_one_neighbor_and_applies_downhill_inflow() -> None:
    low = HexCoord(0, 0)
    high = low.neighbor(0)
    cells = {low, high}
    fields = _fields(cells, moisture=0.58, temperature=0.0)
    fields["elevation"] = {low: 0.0, high: 0.9}
    water = {high: 1.0}

    result = advance_surface_water(water, (), cells, **fields)

    assert result[low] == 0.015
    assert result[high] == 0.92
    assert water == {high: 1.0}  # pure transition; input state is not mutated


def test_preserves_sparse_water_threshold() -> None:
    cell = HexCoord(0, 0)
    fields = _fields({cell}, moisture=0.58, temperature=0.0)

    result = advance_surface_water({}, [cell], {cell}, **fields)

    assert result == {}


def test_requires_candidate_and_state_cells_inside_explicit_grid() -> None:
    cell = HexCoord(0, 0)
    outside = HexCoord(10, 10)
    fields = _fields({cell})

    with pytest.raises(ValueError, match="active_cells"):
        advance_surface_water({}, [outside], {cell}, **fields)
    with pytest.raises(ValueError, match="current_water"):
        advance_surface_water({outside: 0.2}, [], {cell}, **fields)


def test_rejects_non_finite_scalar_inputs() -> None:
    cell = HexCoord(0, 0)
    fields = _fields({cell})
    fields["temperature"][cell] = float("nan")

    with pytest.raises(ValueError, match="finite"):
        advance_surface_water({}, [cell], {cell}, **fields)
