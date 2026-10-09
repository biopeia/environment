"""Pure ecological field rules split from the mixed World geography runtime.

These functions preserve the pinned source equations. They do not own cell
state, topology, persistence, or ecological interpretation beyond the named
source calculations.
"""


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
