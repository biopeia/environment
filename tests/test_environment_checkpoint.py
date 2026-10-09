from __future__ import annotations

import json

import pytest

from environment.genesis import EnvironmentState, GroundTruth
from environment.laws import PeriodicFieldLaw, ResourceLaw
from environment.spatial import HexCoord


def _ground_truth() -> GroundTruth:
    return GroundTruth(
        fields={
            "signal": PeriodicFieldLaw(
                amplitude=0.2, bias=0.5, angular_frequency=0.25
            )
        },
        resources={
            "resource": ResourceLaw(
                capacity=10.0,
                renewal_rate=0.1,
                decay_rate=0.0,
                initial_quantity=5.0,
            )
        },
    )


def test_checkpoint_bytes_are_deterministic_and_restore_mutable_state() -> None:
    environment = EnvironmentState(_ground_truth())
    environment.propagate_fields(3)
    environment.acquire(HexCoord(2, -1), "resource", 1.25)
    environment.deposit(HexCoord(0, 0), "resource", 0.5)

    encoded = environment.checkpoint_bytes()
    assert encoded == environment.checkpoint_bytes()

    restored = EnvironmentState.from_checkpoint_bytes(_ground_truth(), encoded)
    assert restored.snapshot() == environment.snapshot()
    assert restored.checkpoint_bytes() == encoded


def test_checkpoint_preserves_unmaterialized_initial_field_state() -> None:
    environment = EnvironmentState(_ground_truth())

    restored = EnvironmentState.from_checkpoint_bytes(
        _ground_truth(), environment.checkpoint_bytes()
    )

    assert restored.snapshot() == environment.snapshot()


def test_restore_rejects_ground_truth_mismatch() -> None:
    environment = EnvironmentState(_ground_truth())
    environment.propagate_fields(4)
    encoded = environment.checkpoint_bytes()
    incompatible = GroundTruth(
        fields={"other": PeriodicFieldLaw(amplitude=0.2, bias=0.5, angular_frequency=0.25)}
    )

    with pytest.raises(ValueError, match="fields do not match"):
        EnvironmentState.from_checkpoint_bytes(incompatible, encoded)


def test_restore_rejects_field_values_not_derived_from_tick() -> None:
    environment = EnvironmentState(_ground_truth())
    environment.propagate_fields(1)
    document = json.loads(environment.checkpoint_bytes())
    document["field_values"]["signal"] = 999.0

    with pytest.raises(ValueError, match="does not match GroundTruth"):
        EnvironmentState.from_checkpoint_bytes(_ground_truth(), json.dumps(document).encode())
