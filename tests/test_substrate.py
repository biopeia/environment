from __future__ import annotations

import math

import pytest

from environment.spatial import HexCoord
from environment.substrate import apply_substrate_impulse


def test_impulse_transfers_existing_water_and_detritus_using_source_coefficients():
    origin = HexCoord(1, 1)
    target = HexCoord(2, 1)
    water = {origin: 0.6, target: 0.2}
    detritus = {origin: 0.5, target: 0.1}
    disturbance = {origin: 0.2, target: 0.3}

    transition = apply_substrate_impulse(
        width=4,
        height=4,
        origin=origin,
        target=target,
        magnitude=1.0,
        elevation={origin: 0.2, target: 0.4},
        permeability={target: 0.7},
        surface_water=water,
        detritus=detritus,
        disturbance=disturbance,
    )

    # factor = 1 * max(.15, 1 - 1.5 * .2) * .7 = .49
    assert transition.result.water_transferred == pytest.approx(0.049)
    assert transition.result.detritus_transferred == pytest.approx(0.0294)
    assert transition.surface_water[origin] == pytest.approx(0.551)
    assert transition.surface_water[target] == pytest.approx(0.249)
    assert transition.detritus[origin] == pytest.approx(0.4706)
    assert transition.detritus[target] == pytest.approx(0.1294)
    assert transition.disturbance[origin] == pytest.approx(0.28)
    assert transition.disturbance[target] == pytest.approx(0.34)
    assert water == {origin: 0.6, target: 0.2}
    assert detritus == {origin: 0.5, target: 0.1}
    with pytest.raises(TypeError):
        transition.surface_water[origin] = 0.0  # type: ignore[index]


def test_impulse_clamps_magnitude_caps_fields_and_uses_source_missing_defaults():
    origin = HexCoord(0, 0)
    target = HexCoord(1, 0)
    transition = apply_substrate_impulse(
        width=2,
        height=1,
        origin=origin,
        target=target,
        magnitude=3.0,
        elevation={},
        permeability={},
        surface_water={origin: 0.4, target: 0.98},
        detritus={origin: 0.4, target: 0.99},
        disturbance={origin: 0.99, target: 0.99},
    )

    assert transition.result.magnitude == 1.0
    assert transition.result.water_transferred == pytest.approx(0.08)
    assert transition.result.detritus_transferred == pytest.approx(0.048)
    assert transition.surface_water[target] == 1.0
    assert transition.detritus[target] == 1.0
    assert transition.disturbance[origin] == 1.0
    assert transition.disturbance[target] == 1.0


@pytest.mark.parametrize("target", [HexCoord(0, 0), HexCoord(3, 0)])
def test_self_or_out_of_grid_target_only_disturbs_origin(target: HexCoord):
    origin = HexCoord(0, 0)
    transition = apply_substrate_impulse(
        width=2,
        height=2,
        origin=origin,
        target=target,
        magnitude=0.8,
        elevation={},
        permeability={},
        surface_water={origin: 0.6},
        detritus={origin: 0.4},
        disturbance={},
    )

    assert transition.result.target == origin
    assert transition.result.water_transferred == 0.0
    assert transition.result.detritus_transferred == 0.0
    assert transition.surface_water == {origin: 0.6}
    assert transition.detritus == {origin: 0.4}
    assert transition.disturbance == {origin: pytest.approx(0.064)}


@pytest.mark.parametrize("magnitude", [math.inf, -math.inf, math.nan])
def test_non_finite_magnitude_is_rejected(magnitude: float):
    with pytest.raises(ValueError, match="finite"):
        apply_substrate_impulse(
            width=1,
            height=1,
            origin=HexCoord(0, 0),
            target=HexCoord(0, 0),
            magnitude=magnitude,
            elevation={},
            permeability={},
            surface_water={},
            detritus={},
            disturbance={},
        )
