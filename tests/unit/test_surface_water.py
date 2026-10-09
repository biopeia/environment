import pytest

from environment import HexCoord, initialize_surface_water


def _fields(*, moisture_values, elevation_values=None, permeability_values=None):
    cells = [HexCoord(q, r) for q in range(2) for r in range(1)]
    return (
        {cell: moisture_values[index] for index, cell in enumerate(cells)},
        {
            cell: (elevation_values or [0.2, 0.2])[index]
            for index, cell in enumerate(cells)
        },
        {
            cell: (permeability_values or [0.5, 0.5])[index]
            for index, cell in enumerate(cells)
        },
    )


def test_surface_water_matches_source_formula_and_threshold():
    moisture, elevation, permeability = _fields(
        moisture_values=[0.8, 0.582],
        elevation_values=[0.2, 0.0],
        permeability_values=[0.5, 1.0],
    )

    water = initialize_surface_water(
        2,
        1,
        moisture=moisture,
        elevation=elevation,
        permeability=permeability,
    )

    assert water == {HexCoord(0, 0): 0.0979, HexCoord(1, 0): 0.002}
    with pytest.raises(TypeError):
        water[HexCoord(0, 0)] = 1.0


def test_surface_water_omits_values_below_threshold_and_clamps_upper_bound():
    moisture, elevation, permeability = _fields(
        moisture_values=[0.581, 2.0],
        elevation_values=[0.0, 0.0],
        permeability_values=[0.999, 1.0],
    )

    water = initialize_surface_water(
        2,
        1,
        moisture=moisture,
        elevation=elevation,
        permeability=permeability,
    )

    assert water == {HexCoord(1, 0): 1.0}


def test_surface_water_requires_complete_explicit_field_inputs():
    moisture = {HexCoord(0, 0): 0.9}
    elevation = {HexCoord(0, 0): 0.2}
    permeability = {HexCoord(0, 0): 0.8}

    with pytest.raises(ValueError, match="cover every grid cell"):
        initialize_surface_water(
            2,
            1,
            moisture=moisture,
            elevation=elevation,
            permeability=permeability,
        )


def test_surface_water_rejects_non_positive_dimensions():
    for dimensions in ((0, 1), (1, 0), (True, 1)):
        with pytest.raises(ValueError):
            initialize_surface_water(
                *dimensions,
                moisture={},
                elevation={},
                permeability={},
            )
