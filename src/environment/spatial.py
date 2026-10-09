"""Coordinate value used to index spatial environmental state.

World presence, occupancy, placement, and movement authority are not included.
"""

from __future__ import annotations

from dataclasses import dataclass

_DIRECTIONS: tuple[tuple[int, int], ...] = (
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, 0),
    (-1, 1),
    (0, 1),
)

@dataclass(frozen=True, slots=True)
class HexCoord:
    q: int
    r: int

    def neighbor(self, direction: int) -> "HexCoord":
        if not 0 <= direction < 6:
            raise ValueError("direction must be in 0..5")
        dq, dr = _DIRECTIONS[direction]
        return HexCoord(self.q + dq, self.r + dr)

    def distance(self, other: "HexCoord") -> int:
        dq = self.q - other.q
        dr = self.r - other.r
        return (abs(dq) + abs(dr) + abs(dq + dr)) // 2

