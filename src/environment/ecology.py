"""Pure ecological field rules split from the mixed World geography runtime.

These functions preserve the pinned source equations. They do not own cell
state, topology, persistence, or ecological interpretation beyond the named
source calculations.
"""


from collections.abc import Hashable, Mapping
from typing import TypeVar


Cell = TypeVar("Cell", bound=Hashable)


def _decay_sparse_field(
    field: Mapping[Cell, float], *, multiplier: float, threshold: float
) -> dict[Cell, float]:
    """Apply one source sparse-field decay without mutating caller state."""
    result: dict[Cell, float] = {}
    for cell, value in field.items():
        decayed = value * multiplier
        if decayed >= threshold:
            result[cell] = round(decayed, 4)
    return result


def decay_traces(field: Mapping[Cell, float]) -> dict[Cell, float]:
    """Apply the pinned source trace decay (0.94; retain at 0.005)."""
    return _decay_sparse_field(field, multiplier=0.94, threshold=0.005)


def decay_disturbance(field: Mapping[Cell, float]) -> dict[Cell, float]:
    """Apply the pinned source disturbance decay (0.88; retain at 0.005)."""
    return _decay_sparse_field(field, multiplier=0.88, threshold=0.005)


def decay_detritus(field: Mapping[Cell, float]) -> dict[Cell, float]:
    """Apply the pinned source detritus decay (0.985; retain at 0.002)."""
    return _decay_sparse_field(field, multiplier=0.985, threshold=0.002)


def decay_ecological_pressure(field: Mapping[Cell, float]) -> dict[Cell, float]:
    """Apply source ecological-pressure decay (0.92; retain at 0.002)."""
    return _decay_sparse_field(field, multiplier=0.92, threshold=0.002)


def effective_permeability(
    permeability: float,
    disturbance: float,
    detritus: float,
    surface_water: float,
) -> float:
    """Return the source terrain's disturbance-adjusted permeability."""
    value = (
        permeability
        + disturbance * 0.18
        - detritus * 0.25
        - surface_water * 0.08
    )
    return max(0.05, min(1.0, value))


def effective_fertility(
    fertility: float,
    detritus: float,
    surface_water: float,
    ecological_pressure: float,
    disturbance: float,
) -> float:
    """Return the source terrain's ecology-adjusted fertility."""
    value = (
        fertility
        + detritus * 0.24
        + surface_water * 0.10
        - ecological_pressure * 0.22
        - disturbance * 0.12
    )
    return max(0.0, min(1.0, value))


def resource_renewal_factor(effective_fertility_value: float) -> float:
    """Map effective fertility to the source resource renewal multiplier."""
    return 0.20 + 0.80 * effective_fertility_value
