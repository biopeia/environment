"""GroundTruth container and EnvironmentState: real field/resource dynamics
(docs/design/archive/symbiont-world-v1.md §13).

environment never loads TOML or knows about `experiments/`; a caller
(lab, in a later increment) constructs GroundTruth from
world-ground-truth.toml and injects it here. Only opaque FieldId/ResourceId
strings and generic numeric laws ever reach this module -- no domain names.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, Mapping

from environment.laws import HazardLaw, PeriodicFieldLaw, ResourceLaw
from environment.spatial import HexCoord

FieldId = str
ResourceId = str
HazardId = str
RegionId = str


def _freeze_nested(mapping: Mapping) -> Mapping:
    return MappingProxyType({key: MappingProxyType(dict(value)) for key, value in mapping.items()})


@dataclass(frozen=True, slots=True)
class GroundTruth:
    """Fields stay global (uniform temporal signal). Resources/hazards have
    a base law (fallback) plus optional per-region overrides
    (docs/design/archive/symbiont-world-v2.md §3) -- additive: a GroundTruth built
    without region_of/regional_* behaves exactly as it did in v1."""

    fields: Mapping[FieldId, PeriodicFieldLaw] = field(default_factory=dict)
    resources: Mapping[ResourceId, ResourceLaw] = field(default_factory=dict)
    hazards: Mapping[HazardId, HazardLaw] = field(default_factory=dict)
    region_of: Callable[[HexCoord], RegionId] | None = None
    regional_resources: Mapping[RegionId, Mapping[ResourceId, ResourceLaw]] = field(
        default_factory=dict
    )
    regional_hazards: Mapping[RegionId, Mapping[HazardId, HazardLaw]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))
        object.__setattr__(self, "resources", MappingProxyType(dict(self.resources)))
        object.__setattr__(self, "hazards", MappingProxyType(dict(self.hazards)))
        object.__setattr__(self, "regional_resources", _freeze_nested(self.regional_resources))
        object.__setattr__(self, "regional_hazards", _freeze_nested(self.regional_hazards))

    def region_of_cell(self, cell: HexCoord) -> RegionId | None:
        return self.region_of(cell) if self.region_of is not None else None

    def resource_law(self, cell: HexCoord, resource_id: ResourceId) -> ResourceLaw:
        region = self.region_of_cell(cell)
        if region is not None:
            override = self.regional_resources.get(region, {}).get(resource_id)
            if override is not None:
                return override
        return self.resources[resource_id]

    def hazard_law(self, cell: HexCoord, hazard_id: HazardId) -> HazardLaw:
        region = self.region_of_cell(cell)
        if region is not None:
            override = self.regional_hazards.get(region, {}).get(hazard_id)
            if override is not None:
                return override
        return self.hazards[hazard_id]


class EnvironmentState:
    """Mutable runtime state derived from a frozen GroundTruth: current
    field values (spatially uniform in W2) and per-cell resource pools,
    materialized lazily on first access."""

    def __init__(self, ground_truth: GroundTruth) -> None:
        self.ground_truth = ground_truth
        self._field_values: dict[FieldId, float] = {}
        self._resource_pools: dict[HexCoord, dict[ResourceId, float]] = {}
        self._tick: int = 0

    @property
    def current_tick(self) -> int:
        """Current Environment clock without exposing mutable internals."""

        return int(self._tick)

    def field_values_at(self, tick: int) -> Mapping[FieldId, float]:
        """Return an immutable field projection at an explicit causal tick.

        This is a pure query: it does not advance or mutate EnvironmentState.
        World can therefore request the environmental values for a proposed
        causal transition without relying on call order or host wall-clock time.
        """
        if type(tick) is not int or tick < 0:
            raise ValueError("tick must be a non-negative integer causal tick")
        return MappingProxyType(
            {
                field_id: law.value_at(tick)
                for field_id, law in self.ground_truth.fields.items()
            }
        )

    def propagate_fields(self, tick: int) -> None:
        self._tick = int(tick)
        self._field_values = {
            field_id: law.value_at(tick) for field_id, law in self.ground_truth.fields.items()
        }

    def field_values(self) -> Mapping[FieldId, float]:
        return MappingProxyType(dict(self._field_values))

    def is_materialized(self, cell: HexCoord) -> bool:
        return cell in self._resource_pools

    def _pool(self, cell: HexCoord) -> dict[ResourceId, float]:
        if cell not in self._resource_pools:
            self._resource_pools[cell] = {
                resource_id: self.ground_truth.resource_law(cell, resource_id).initial_quantity
                for resource_id in self.ground_truth.resources
            }
        return self._resource_pools[cell]

    def resource_pool(self, cell: HexCoord) -> Mapping[ResourceId, float]:
        return MappingProxyType(dict(self._pool(cell)))

    def renew_resources(self, cell: HexCoord, *, renewal_factor: float = 1.0) -> None:
        if renewal_factor < 0.0:
            raise ValueError("renewal_factor must be non-negative")
        pool = self._pool(cell)
        factor = max(0.0, min(1.5, float(renewal_factor)))
        for resource_id in self.ground_truth.resources:
            law = self.ground_truth.resource_law(cell, resource_id)
            current = pool.get(resource_id, law.initial_quantity)
            baseline_next = law.step(current)
            delta = baseline_next - current
            if delta >= 0.0:
                pool[resource_id] = min(law.capacity, current + delta * factor)
            else:
                # Decay is a property of the resource law, not local fertility.
                pool[resource_id] = baseline_next

    def acquire(self, cell: HexCoord, resource_id: ResourceId, requested: float) -> float:
        if requested < 0:
            raise ValueError("requested quantity must be non-negative")
        pool = self._pool(cell)
        available = pool.get(resource_id, 0.0)
        granted = min(requested, available)
        pool[resource_id] = available - granted
        return granted

    def deposit(self, cell: HexCoord, resource_id: ResourceId, amount: float) -> None:
        if amount < 0:
            raise ValueError("deposit quantity must be non-negative")
        if amount == 0:
            return
        pool = self._pool(cell)
        pool[resource_id] = pool.get(resource_id, 0.0) + amount

    def hazard_exposures(
        self,
        local_density: float,
        *,
        tick: int | None = None,
    ) -> Mapping[HazardId, float]:
        """Base-law exposures, ignoring any regional override."""
        effective_tick = self._tick if tick is None else int(tick)
        return {
            hazard_id: law.exposure(local_density, tick=effective_tick)
            for hazard_id, law in self.ground_truth.hazards.items()
        }

    def hazard_exposures_at(
        self,
        cell: HexCoord,
        local_density: float,
        *,
        tick: int | None = None,
    ) -> Mapping[HazardId, float]:
        """Region-aware exposures using the current World tick by default."""
        effective_tick = self._tick if tick is None else int(tick)
        return {
            hazard_id: self.ground_truth.hazard_law(cell, hazard_id).exposure(
                local_density,
                tick=effective_tick,
            )
            for hazard_id in self.ground_truth.hazards
        }

    def snapshot(self) -> dict[str, Any]:
        """Snapshot internal mutable state for transaction rollback or checkpoint."""
        return {
            "tick": self._tick,
            "field_values": dict(self._field_values),
            "resource_pools": {cell: dict(pool) for cell, pool in self._resource_pools.items()},
        }

    def checkpoint_bytes(self) -> bytes:
        """Return a deterministic checkpoint of mutable Environment-owned state.

        ``GroundTruth`` is configuration supplied by its owner and is not copied
        into this payload. The caller supplies that configuration at restore;
        stored field values are checked against its laws at the saved causal tick.
        This payload does not identify or validate all GroundTruth dependencies.
        """
        snapshot = self.snapshot()
        payload = {
            "schema": "biopeia.environment-state",
            "schema_version": 1,
            "tick": snapshot["tick"],
            "field_values": dict(sorted(snapshot["field_values"].items())),
            "resource_pools": [
                {
                    "q": cell.q,
                    "r": cell.r,
                    "resources": dict(sorted(pool.items())),
                }
                for cell, pool in sorted(
                    snapshot["resource_pools"].items(),
                    key=lambda item: (item[0].q, item[0].r),
                )
            ],
        }
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        return (encoded + "\n").encode("utf-8")

    @classmethod
    def from_checkpoint_bytes(
        cls, ground_truth: GroundTruth, payload: bytes
    ) -> "EnvironmentState":
        """Restore mutable state against caller-supplied Environment configuration.

        The payload validates its field projection against the supplied laws, but
        does not prove full configuration identity (for example, resource,
        hazard, or regional-law equivalence).
        """
        try:
            document = json.loads(payload)
            if not isinstance(document, dict) or set(document) != {
                "schema",
                "schema_version",
                "tick",
                "field_values",
                "resource_pools",
            }:
                raise ValueError("invalid Environment checkpoint shape")
            if (
                document["schema"] != "biopeia.environment-state"
                or document["schema_version"] != 1
            ):
                raise ValueError("unsupported Environment checkpoint schema")
            tick = document["tick"]
            fields = document["field_values"]
            pools = document["resource_pools"]
            if (
                type(tick) is not int
                or tick < 0
                or not isinstance(fields, dict)
                or not isinstance(pools, list)
            ):
                raise ValueError("invalid Environment checkpoint values")
            field_ids = set(fields)
            if field_ids not in (set(), set(ground_truth.fields)):
                raise ValueError(
                    "checkpoint fields do not match supplied GroundTruth"
                )
            normalized_fields: dict[str, float] = {}
            for field_id, value in fields.items():
                if (
                    not isinstance(field_id, str)
                    or isinstance(value, bool)
                    or not isinstance(value, (int, float))
                ):
                    raise ValueError("invalid Environment field checkpoint")
                value = float(value)
                if (
                    not math.isfinite(value)
                    or value != ground_truth.fields[field_id].value_at(tick)
                ):
                    raise ValueError(
                        "checkpoint field projection does not match GroundTruth and tick"
                    )
                normalized_fields[field_id] = value

            resource_pools: dict[HexCoord, dict[str, float]] = {}
            for entry in pools:
                if not isinstance(entry, dict) or set(entry) != {
                    "q",
                    "r",
                    "resources",
                }:
                    raise ValueError("invalid Environment resource pool checkpoint")
                q, r, resources = entry["q"], entry["r"], entry["resources"]
                if (
                    type(q) is not int
                    or type(r) is not int
                    or not isinstance(resources, dict)
                ):
                    raise ValueError("invalid Environment resource pool checkpoint")
                cell = HexCoord(q, r)
                if cell in resource_pools:
                    raise ValueError("duplicate Environment resource pool coordinate")
                normalized_pool: dict[str, float] = {}
                for resource_id, value in resources.items():
                    if (
                        not isinstance(resource_id, str)
                        or isinstance(value, bool)
                        or not isinstance(value, (int, float))
                    ):
                        raise ValueError("invalid Environment resource checkpoint")
                    value = float(value)
                    if not math.isfinite(value) or value < 0:
                        raise ValueError("invalid Environment resource quantity")
                    normalized_pool[resource_id] = value
                resource_pools[cell] = normalized_pool

            state = cls(ground_truth)
            state.restore(
                {
                    "tick": tick,
                    "field_values": normalized_fields,
                    "resource_pools": resource_pools,
                }
            )
            return state
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            OverflowError,
            TypeError,
            KeyError,
        ) as exc:
            raise ValueError("malformed Environment checkpoint") from exc

    def restore(self, snap: Mapping[str, Any]) -> None:
        """Restore internal mutable state from a snapshot."""
        self._tick = int(snap.get("tick", 0))
        self._field_values = dict(snap.get("field_values", {}))
        self._resource_pools = {
            cell: dict(pool) for cell, pool in snap.get("resource_pools", {}).items()
        }
