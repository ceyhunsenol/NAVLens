"""Publication-time-safe security price dataset snapshots and point-in-time selection."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from navlens import MarketDate, SecurityPriceObservation

from ._correction import latest_corrections_by_date
from ._timestamps import validate_utc_timestamp
from .errors import SecurityPriceDatasetError


@dataclass(frozen=True, slots=True)
class SecurityPriceSnapshot:
    """A publication-time-safe dataset envelope wrapping a security price observation."""

    observation: SecurityPriceObservation
    available_at: datetime
    ingested_at: datetime
    source_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.observation, SecurityPriceObservation):
            obs_type = type(self.observation).__name__
            raise SecurityPriceDatasetError(
                f"observation must be a SecurityPriceObservation instance; got {obs_type}"
            )
        if not isinstance(self.source_id, str) or not self.source_id:
            raise SecurityPriceDatasetError("source_id must be a non-empty string")

        validate_utc_timestamp(self.available_at, "available_at", SecurityPriceDatasetError)
        validate_utc_timestamp(self.ingested_at, "ingested_at", SecurityPriceDatasetError)

        if self.ingested_at < self.available_at:
            raise SecurityPriceDatasetError("ingestion time cannot precede availability time")


def select_security_price_snapshots(
    snapshots: Iterable[SecurityPriceSnapshot],
    *,
    source_id: str,
    instrument_id: str,
    at_timestamp: datetime,
    pricing_as_of_date: MarketDate,
) -> tuple[SecurityPriceSnapshot, ...]:
    """Select point-in-time-safe security price snapshots chronologically up to pricing as-of date.

    Rules:
    - Only snapshots matching `source_id`, `instrument_id`, published on or before `at_timestamp`
      (`available_at <= at_timestamp`), and with `market_date <= pricing_as_of_date` are eligible.
    - For any market date, the snapshot published latest (`(available_at, ingested_at)`)
      supersedes earlier observations once its `available_at` timestamp has passed.
    - Observations from different sources are never mixed.
    - The returned tuple is sorted chronologically by market date.
    """
    validate_utc_timestamp(at_timestamp, "prediction timestamp", SecurityPriceDatasetError)

    eligible = _eligible_snapshots(
        snapshots,
        source_id=source_id,
        instrument_id=instrument_id,
        at_timestamp=at_timestamp,
        pricing_as_of_date=pricing_as_of_date,
    )
    if not eligible:
        return ()

    latest_by_date = latest_corrections_by_date(eligible, lambda s: s.observation.market_date)
    return tuple(sorted(latest_by_date.values(), key=lambda s: s.observation.market_date))


def _eligible_snapshots(
    snapshots: Iterable[SecurityPriceSnapshot],
    *,
    source_id: str,
    instrument_id: str,
    at_timestamp: datetime,
    pricing_as_of_date: MarketDate,
) -> list[SecurityPriceSnapshot]:
    return [
        snapshot
        for snapshot in snapshots
        if snapshot.source_id == source_id
        and snapshot.observation.instrument_id == instrument_id
        and snapshot.available_at <= at_timestamp
        and snapshot.observation.market_date <= pricing_as_of_date
    ]
