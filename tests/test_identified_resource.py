import json

import pytest

from environment.identified_resource import IdentifiedFiniteResource
from environment.resource import FiniteResourceState


def test_identified_resource_checkpoint_preserves_owner_identity_and_state() -> None:
    owner = IdentifiedFiniteResource("resource.alpha", FiniteResourceState(remaining=3.5))

    encoded = owner.checkpoint_bytes()
    restored = IdentifiedFiniteResource.from_checkpoint_bytes(encoded)

    payload = json.loads(encoded)
    assert payload["checkpoint_type"] == "biopeia.environment.identified-finite-resource"
    assert payload["checkpoint_version"] == 1
    assert payload["state"]["checkpoint_type"] == "biopeia.environment.finite-resource-state"
    assert payload["state"]["checkpoint_version"] == 1
    assert encoded == owner.checkpoint_bytes()
    assert restored.resource_id == "resource.alpha"
    assert restored.state.checkpoint() == owner.state.checkpoint()


def test_identified_resource_checkpoint_rejects_invalid_identity_or_shape() -> None:
    with pytest.raises(ValueError, match="resource_id"):
        IdentifiedFiniteResource(" ", FiniteResourceState())

    payload = json.loads(
        IdentifiedFiniteResource("resource.alpha", FiniteResourceState()).checkpoint_bytes()
    )
    payload["resource_id"] = ""
    with pytest.raises(ValueError, match="resource_id"):
        IdentifiedFiniteResource.from_checkpoint_bytes(json.dumps(payload).encode())

    source_v1 = {
        "schema_version": 1,
        "resource_id": "resource.alpha",
        "state": {
            "schema_version": 1,
            "position": [3.0, 0.0, 0.18],
            "radius": 0.18,
            "field_radius": 6.0,
            "remaining": 200.0,
            "transfer_per_tick": 2.0,
        },
    }
    with pytest.raises(ValueError, match="checkpoint fields"):
        IdentifiedFiniteResource.from_checkpoint_bytes(json.dumps(source_v1).encode())


def test_identified_resource_checkpoint_rejects_unknown_fields_at_each_level() -> None:
    owner = IdentifiedFiniteResource("resource.alpha", FiniteResourceState(remaining=3.5))
    payload = json.loads(owner.checkpoint_bytes())

    payload["unexpected"] = "future-looking but unsupported"
    with pytest.raises(ValueError, match="checkpoint fields"):
        IdentifiedFiniteResource.from_checkpoint_bytes(json.dumps(payload).encode())

    payload = json.loads(owner.checkpoint_bytes())
    payload["state"]["unexpected"] = "unsupported nested field"
    with pytest.raises(ValueError, match="finite resource checkpoint contract"):
        IdentifiedFiniteResource.from_checkpoint_bytes(json.dumps(payload).encode())


def test_owner_checkpoint_validation_checks_identity_schema_and_bytes() -> None:
    owner = IdentifiedFiniteResource("resource.alpha", FiniteResourceState(remaining=3.5))
    encoded = owner.checkpoint_bytes()

    assert IdentifiedFiniteResource.validate_checkpoint(
        encoded, "resource.alpha", IdentifiedFiniteResource.OWNER_SCHEMA
    )
    assert not IdentifiedFiniteResource.validate_checkpoint(
        encoded, "resource.other", IdentifiedFiniteResource.OWNER_SCHEMA
    )
    assert not IdentifiedFiniteResource.validate_checkpoint(
        encoded, "resource.alpha", "unsupported-schema"
    )
    assert not IdentifiedFiniteResource.validate_checkpoint(
        b"not a checkpoint", "resource.alpha", IdentifiedFiniteResource.OWNER_SCHEMA
    )
