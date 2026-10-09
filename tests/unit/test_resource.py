from __future__ import annotations

import math

import pytest

from environment.resource import FiniteResourceState


def test_resource_field_is_local_scalar_and_extinguishes_when_depleted() -> None:
    resource = FiniteResourceState(
        position=(2.0, 0.0, 0.0),
        radius=0.2,
        field_radius=4.0,
        remaining=1.5,
        transfer_per_tick=2.0,
    )

    near = resource.field_at((1.0, 0.0, 0.0))
    far = resource.field_at((0.0, 0.0, 0.0))

    assert 0.0 < far < near < 1.0
    assert resource.field_at((6.0, 0.0, 0.0)) == 0.0
    resource.consume_absorbed(10.0)
    assert resource.field_at((2.0, 0.0, 0.0)) == 0.0


def test_resource_debits_only_accepted_material_with_transfer_bound() -> None:
    resource = FiniteResourceState(remaining=10.0, transfer_per_tick=2.0)

    assert resource.offered_material() == 2.0
    assert resource.consume_absorbed(0.4) == pytest.approx(0.4)
    assert resource.remaining == pytest.approx(9.6)
    assert resource.consume_absorbed(20.0) == pytest.approx(2.0)
    assert resource.remaining == pytest.approx(7.6)


def test_resource_checkpoint_round_trip_preserves_source_v1_shape() -> None:
    resource = FiniteResourceState(
        position=(2.0, -1.0, 0.5),
        radius=0.25,
        field_radius=4.0,
        remaining=7.5,
        transfer_per_tick=1.25,
    )
    expected = {
        "schema_version": 1,
        "position": [2.0, -1.0, 0.5],
        "radius": 0.25,
        "field_radius": 4.0,
        "remaining": 7.5,
        "transfer_per_tick": 1.25,
    }

    assert resource.checkpoint() == expected
    restored = FiniteResourceState.from_checkpoint(expected)
    assert restored.checkpoint() == expected


@pytest.mark.parametrize(
    "kwargs",
    [
        {"position": (0.0, 1.0)},
        {"position": (0.0, math.inf, 1.0)},
        {"radius": 0.0},
        {"field_radius": 0.1, "radius": 0.2},
        {"remaining": -1.0},
        {"transfer_per_tick": math.nan},
    ],
)
def test_resource_rejects_invalid_configuration(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        FiniteResourceState(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize("amount", [True, -0.1, math.inf, math.nan, "1"])
def test_resource_rejects_invalid_consumption(amount: object) -> None:
    with pytest.raises(ValueError):
        FiniteResourceState().consume_absorbed(amount)  # type: ignore[arg-type]
