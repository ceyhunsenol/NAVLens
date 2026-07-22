"""Publication-time-safe security price dataset snapshots and point-in-time selection."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from navlens import CurrencyCode, MarketDate, PriceAdjustment, SecurityPriceObservation

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
    currency: CurrencyCode,
    adjustment: PriceAdjustment,
    at_timestamp: datetime,
) -> tuple[SecurityPriceSnapshot, ...]:
    """Select point-in-time-safe security price snapshots chronologically.

    Rules:
    - Only snapshots matching `source_id`, `instrument_id`, `currency`, `adjustment`,
      and published on or before `at_timestamp` (`available_at <= at_timestamp`) are eligible.
    - For any market date, the snapshot published latest (`(available_at, ingested_at)`)
      supersedes earlier observations once its `available_at` timestamp has passed.
    - Observations from different sources are never mixed.
    - The returned tuple is sorted chronologically by market date.
    """
    validate_utc_timestamp(at_timestamp, "prediction timestamp", SecurityPriceDatasetError)

    eligible = [
        s
        for s in snapshots
        if s.source_id == source_id
        and s.observation.instrument_id == instrument_id
        and s.observation.currency == currency
        and s.observation.adjustment == adjustment
        and s.available_at <= at_timestamp
    ]
    if not eligible:
        return ()

    market_date_map: dict[MarketDate, SecurityPriceSnapshot] = {}
    for s in eligible:
        market_date = s.observation.market_date
        existing = market_date_map.get(market_date)
        if existing is None or (s.available_at, s.ingested_at) > (
            existing.available_at,
            existing.ingested_at,
        ):
            market_date_map[market_date] = s

    sorted_snapshots = sorted(
        market_date_map.values(),
        key=lambda s: s.observation.market_date,
    )
    return tuple(sorted_snapshots)
