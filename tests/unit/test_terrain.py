from __future__ import annotations

import pytest

from environment import HexCoord, TerrainFieldState


def test_terrain_fields_are_deterministic_for_same_dimensions_and_seed() -> None:
    first = TerrainFieldState(4, 3, terrain_seed=42)
    second = TerrainFieldState(4, 3, terrain_seed=42)
    cells = (HexCoord(0, 0), HexCoord(1, 1), HexCoord(3, 2))

    values = lambda state: tuple(
        (
            state.elevation(cell),
            state.permeability(cell),
            state.moisture(cell),
            state.temperature(cell),
            state.fertility(cell),
        )
        for cell in cells
    )
    assert values(first) == values(second)


def test_seed_phase_preserves_source_modulo_behavior() -> None:
    assert TerrainFieldState(4, 3, 42).elevation(HexCoord(1, 1)) == (
        TerrainFieldState(4, 3, 1042).elevation(HexCoord(1, 1))
    )


def test_generated_values_match_pinned_source_initialization_examples() -> None:
    fields = TerrainFieldState(4, 3, terrain_seed=42)

    assert (
        fields.elevation(HexCoord(1, 1)),
        fields.permeability(HexCoord(1, 1)),
        fields.moisture(HexCoord(1, 1)),
        fields.temperature(HexCoord(1, 1)),
        fields.fertility(HexCoord(1, 1)),
    ) == (0.6403, 0.5838, 0.5731, 0.2592, 0.5689)


def test_missing_coordinate_uses_source_field_defaults() -> None:
    fields = TerrainFieldState(2, 2, terrain_seed=42)
    outside = HexCoord(20, 20)

    assert fields.elevation(outside) == 0.5
    assert fields.permeability(outside) == 0.8
    assert fields.moisture(outside) == 0.5
    assert fields.temperature(outside) == 0.5
    assert fields.fertility(outside) == 0.5


def test_explicit_field_overrides_do_not_change_other_generated_fields() -> None:
    cell = HexCoord(0, 0)
    generated = TerrainFieldState(2, 2, terrain_seed=42)
    overridden = TerrainFieldState(2, 2, terrain_seed=42, elevation={cell: 0.25})

    assert overridden.elevation(cell) == 0.25
    assert overridden.moisture(cell) == generated.moisture(cell)
    assert overridden.temperature(cell) == generated.temperature(cell)
    assert overridden.fertility(cell) == generated.fertility(cell)


def test_terrain_state_is_immutable_after_construction() -> None:
    fields = TerrainFieldState(2, 2, terrain_seed=42)

    with pytest.raises(AttributeError, match="TerrainFieldState is immutable"):
        fields.width = 3  # type: ignore[misc]


@pytest.mark.parametrize("width,height", [(0, 1), (1, 0), (-1, 2), (2, -1)])
def test_dimensions_must_be_positive(width: int, height: int) -> None:
    with pytest.raises(ValueError, match="terrain dimensions must be positive"):
        TerrainFieldState(width, height, terrain_seed=1)
