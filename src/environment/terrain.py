"""Deterministic objective terrain fields for a finite coordinate grid.

This module owns only terrain field values generated from an explicit seed
and dimensions. Spatial topology, movement/traversal, occupancy, ecological
interactions, and time-varying terrain remain outside this contract.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from types import MappingProxyType

from environment.spatial import HexCoord


class TerrainFieldState:
    """Generated environmental elevation, permeability, moisture and fertility.

    The formulas are a bounded extraction of the deterministic initialization
    in the source monolith's DynamicGeography._generate_topography. This object
    is immutable after construction; it does not advance causal time or
    participate in World interaction resolution.
    """

    def __init__(
        self,
        width: int,
        height: int,
        terrain_seed: int,
        *,
        elevation: Mapping[HexCoord, float] | None = None,
        permeability: Mapping[HexCoord, float] | None = None,
        moisture: Mapping[HexCoord, float] | None = None,
        temperature: Mapping[HexCoord, float] | None = None,
        fertility: Mapping[HexCoord, float] | None = None,
    ) -> None:
        if width < 1 or height < 1:
            raise ValueError("terrain dimensions must be positive")
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)
        object.__setattr__(self, "terrain_seed", terrain_seed)

        generated = self._generate(width, height, terrain_seed)
        object.__setattr__(
            self,
            "_elevation",
            MappingProxyType(
                dict(elevation) if elevation is not None else generated[0]
            ),
        )
        object.__setattr__(
            self,
            "_permeability",
            MappingProxyType(
                dict(permeability) if permeability is not None else generated[1]
            ),
        )
        object.__setattr__(
            self,
            "_moisture",
            MappingProxyType(dict(moisture) if moisture is not None else generated[2]),
        )
        object.__setattr__(
            self,
            "_temperature",
            MappingProxyType(
                dict(temperature) if temperature is not None else generated[3]
            ),
        )
        object.__setattr__(
            self,
            "_fertility",
            MappingProxyType(
                dict(fertility) if fertility is not None else generated[4]
            ),
        )

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("TerrainFieldState is immutable")

    @staticmethod
    def _generate(
        width: int, height: int, terrain_seed: int
    ) -> tuple[
        dict[HexCoord, float],
        dict[HexCoord, float],
        dict[HexCoord, float],
        dict[HexCoord, float],
        dict[HexCoord, float],
    ]:
        elevation: dict[HexCoord, float] = {}
        permeability: dict[HexCoord, float] = {}
        moisture: dict[HexCoord, float] = {}
        temperature: dict[HexCoord, float] = {}
        fertility: dict[HexCoord, float] = {}
        seed_phase = float(terrain_seed % 1000)

        for q in range(width):
            for r in range(height):
                coord = HexCoord(q, r)
                nx = (q / width) * math.pi * 2.0
                ny = (r / height) * math.pi * 2.0

                v1 = math.sin(nx * 1.5 + seed_phase * 0.1) * math.cos(
                    ny * 1.5 + seed_phase * 0.2
                )
                v2 = (
                    math.sin(nx * 3.0 + seed_phase * 0.5) * 0.35
                    + math.cos(ny * 3.0 + seed_phase * 0.3) * 0.35
                )
                elev = max(0.0, min(1.0, (v1 * 0.65 + v2 * 0.35 + 1.0) * 0.5))
                elevation[coord] = round(elev, 4)

                lat_temp = (r / height) * 0.7 + 0.15
                temp = max(0.0, min(1.0, lat_temp - (elev * 0.35) + 0.1))
                temperature[coord] = round(temp, 4)

                rain = (math.cos(nx * 2.0 + seed_phase * 0.7) * 0.5 + 0.5) * 0.6
                basin = (1.0 - elev) * 0.4
                moist = max(0.0, min(1.0, rain + basin))
                moisture[coord] = round(moist, 4)

                temp_opt = 1.0 - abs(temp - 0.55) * 1.5
                fert = moist * 0.55 + max(0.0, temp_opt) * 0.45
                fertility[coord] = round(max(0.05, min(1.0, fert)), 4)

                slope_penalty = elev * 0.65
                perm = max(0.12, min(1.0, 1.0 - slope_penalty))
                permeability[coord] = round(perm, 4)

        return elevation, permeability, moisture, temperature, fertility

    def elevation(self, cell: HexCoord) -> float:
        return self._elevation.get(cell, 0.5)

    def permeability(self, cell: HexCoord) -> float:
        return self._permeability.get(cell, 0.8)

    def moisture(self, cell: HexCoord) -> float:
        return self._moisture.get(cell, 0.5)

    def temperature(self, cell: HexCoord) -> float:
        return self._temperature.get(cell, 0.5)

    def fertility(self, cell: HexCoord) -> float:
        return self._fertility.get(cell, 0.5)
