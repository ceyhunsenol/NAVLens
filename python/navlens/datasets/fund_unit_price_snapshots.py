"""Publication-time-safe fund unit-price dataset snapshots and point-in-time selection."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from navlens import MarketDate, PriceObservation

from ._correction import latest_corrections_by_date
from ._timestamps import validate_utc_timestamp
from .errors import FundUnitPriceDatasetError


@dataclass(frozen=True, slots=True)
class FundUnitPriceSnapshot:
    """A publication-time-safe dataset envelope wrapping a fund price observation."""

    fund_id: str
    observation: PriceObservation
    available_at: datetime
    ingested_at: datetime
    source_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.fund_id, str) or not self.fund_id:
            raise FundUnitPriceDatasetError("fund_id must be a non-empty string")
        if not isinstance(self.observation, PriceObservation):
            obs_type = type(self.observation).__name__
            raise FundUnitPriceDatasetError(
                f"observation must be a PriceObservation instance; got {obs_type}"
            )
        if not isinstance(self.source_id, str) or not self.source_id:
            raise FundUnitPriceDatasetError("source_id must be a non-empty string")

        validate_utc_timestamp(self.available_at, "available_at", FundUnitPriceDatasetError)
        validate_utc_timestamp(self.ingested_at, "ingested_at", FundUnitPriceDatasetError)

        if self.ingested_at < self.available_at:
            raise FundUnitPriceDatasetError("ingestion time cannot precede availability time")


def select_fund_unit_price_snapshots(
    snapshots: Iterable[FundUnitPriceSnapshot],
    *,
    source_id: str,
    fund_id: str,
    at_timestamp: datetime,
    pricing_as_of_date: MarketDate,
) -> tuple[FundUnitPriceSnapshot, ...]:
    """Select point-in-time-safe fund price snapshots chronologically up to pricing as-of date.

    Rules:
    - Only snapshots matching `source_id`, `fund_id`, published on or before `at_timestamp`
      (`available_at <= at_timestamp`), and with `market_date <= pricing_as_of_date` are eligible.
    - For any market date, the snapshot published latest (`(available_at, ingested_at)`)
      supersedes earlier observations once its `available_at` timestamp has passed.
    - Observations from different sources are never mixed.
    - The returned tuple is sorted chronologically by market date.
    """
    validate_utc_timestamp(at_timestamp, "prediction timestamp", FundUnitPriceDatasetError)

    eligible = _eligible_snapshots(
        snapshots,
        source_id=source_id,
        fund_id=fund_id,
        at_timestamp=at_timestamp,
        pricing_as_of_date=pricing_as_of_date,
    )
    if not eligible:
        return ()

    latest_by_date = latest_corrections_by_date(eligible, lambda s: s.observation.date)
    return tuple(sorted(latest_by_date.values(), key=lambda s: s.observation.date))


def _eligible_snapshots(
    snapshots: Iterable[FundUnitPriceSnapshot],
    *,
    source_id: str,
    fund_id: str,
    at_timestamp: datetime,
    pricing_as_of_date: MarketDate,
) -> list[FundUnitPriceSnapshot]:
    return [
        snapshot
        for snapshot in snapshots
        if snapshot.source_id == source_id
        and snapshot.fund_id == fund_id
        and snapshot.available_at <= at_timestamp
        and snapshot.observation.date <= pricing_as_of_date
    ]
