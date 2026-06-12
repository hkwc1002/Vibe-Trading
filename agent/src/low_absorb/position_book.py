"""In-memory manual position book skeleton."""

from __future__ import annotations

from .models import ManualPosition, PositionStatus


class ManualPositionBook:
    """Small in-memory registry for manual positions."""

    def __init__(self) -> None:
        self._positions: dict[str, ManualPosition] = {}

    def upsert(self, position: ManualPosition) -> ManualPosition:
        self._positions[position.position_id] = position
        return position

    def list_active(self) -> list[ManualPosition]:
        return [
            position
            for position in self._positions.values()
            if position.status
            in {
                PositionStatus.ACTIVE_POSITION,
                PositionStatus.HOLDING_REVIEW,
                PositionStatus.EXIT_SUGGESTED,
            }
        ]

    def list_all(self) -> list[ManualPosition]:
        return list(self._positions.values())
