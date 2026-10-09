import json

import pytest

from environment.identified_resource import IdentifiedFiniteResource
from environment.resource import FiniteResourceState


def test_identified_resource_checkpoint_preserves_owner_identity_and_state() -> None:
    owner = IdentifiedFiniteResource("resource.alpha", FiniteResourceState(remaining=3.5))

    encoded = owner.checkpoint_bytes()
    restored = IdentifiedFiniteResource.from_checkpoint_bytes(encoded)

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
