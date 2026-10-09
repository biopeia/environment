import math

import pytest

from environment.ecology import (
    decay_detritus,
    decay_disturbance,
    decay_ecological_pressure,
    decay_traces,
    effective_fertility,
    effective_permeability,
    resource_renewal_factor,
)


@pytest.mark.parametrize(
    "decay, multiplier, threshold",
    [
        (decay_traces, 0.94, 0.005),
        (decay_disturbance, 0.88, 0.005),
        (decay_detritus, 0.985, 0.002),
        (decay_ecological_pressure, 0.92, 0.002),
    ],
)
def test_sparse_decay_preserves_threshold_rounding_and_input(decay, multiplier, threshold):
    at_threshold = threshold / multiplier
    below_threshold = math.nextafter(at_threshold, 0.0)
    field = {"kept": 0.123456, "threshold": at_threshold, "dropped": below_threshold}
    original = field.copy()

    result = decay(field)

    assert result == {
        "kept": round(0.123456 * multiplier, 4),
        "threshold": threshold,
    }
    assert field == original
    assert result is not field


def test_effective_fertility_preserves_source_contributions_and_clamp():
    assert effective_fertility(0.5, 0.5, 0.4, 0.2, 0.1) == pytest.approx(0.604)
    assert effective_fertility(1.0, 1.0, 1.0, 0.0, 0.0) == 1.0
    assert effective_fertility(0.0, 0.0, 0.0, 10.0, 0.0) == 0.0


def test_effective_permeability_preserves_source_contributions_and_clamp():
    assert effective_permeability(0.6, 0.5, 0.2, 0.25) == pytest.approx(0.62)
    assert effective_permeability(2.0, 0.0, 0.0, 0.0) == 1.0
    assert effective_permeability(0.0, 0.0, 1.0, 0.0) == 0.05


@pytest.mark.parametrize("fertility, expected", [(0.0, 0.2), (0.5, 0.6), (1.0, 1.0)])
def test_resource_renewal_factor_preserves_source_floor(fertility, expected):
    assert resource_renewal_factor(fertility) == pytest.approx(expected)
