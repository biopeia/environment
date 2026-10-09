import pytest

from environment.ecology import (
    effective_fertility,
    effective_permeability,
    resource_renewal_factor,
)


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
