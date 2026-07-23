"""Shared private deterministic revision-selection algorithm for point-in-time snapshots."""

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Protocol, TypeVar

from navlens import MarketDate


class PointInTimeSnapshot(Protocol):
    @property
    def available_at(self) -> datetime: ...

    @property
    def ingested_at(self) -> datetime: ...


T = TypeVar("T", bound=PointInTimeSnapshot)


def latest_corrections_by_date(
    snapshots: Iterable[T],
    date_extractor: Callable[[T], MarketDate],
) -> dict[MarketDate, T]:
    """Resolve corrections for the same market date deterministically.

    The snapshot published latest `(available_at, ingested_at)` supersedes earlier observations.
    A strictly greater-than comparison is used, ensuring that tied timestamps preserve the
    first observed snapshot encountered in the sequence.
    """
    market_date_map: dict[MarketDate, T] = {}
    for snapshot in snapshots:
        market_date = date_extractor(snapshot)
        existing = market_date_map.get(market_date)
        if existing is None or (snapshot.available_at, snapshot.ingested_at) > (
            existing.available_at,
            existing.ingested_at,
        ):
            market_date_map[market_date] = snapshot
    return market_date_map
