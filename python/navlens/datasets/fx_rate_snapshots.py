"""Publication-time-safe FX rate dataset snapshots and point-in-time selection."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from navlens import CurrencyPair, FxRateKind, FxRateObservation, MarketDate
from navlens._timestamps import validate_utc_timestamp

from ._correction import latest_corrections_by_date
from .errors import FxRateDatasetError


@dataclass(frozen=True, slots=True)
class FxRateSnapshot:
    """A publication-time-safe dataset envelope wrapping an FX rate observation."""

    observation: FxRateObservation
    available_at: datetime
    ingested_at: datetime
    source_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.observation, FxRateObservation):
            obs_type = type(self.observation).__name__
            raise FxRateDatasetError(
                f"observation must be an FxRateObservation instance; got {obs_type}"
            )
        if not isinstance(self.source_id, str) or not self.source_id:
            raise FxRateDatasetError("source_id must be a non-empty string")

        validate_utc_timestamp(self.available_at, "available_at", FxRateDatasetError)
        validate_utc_timestamp(self.ingested_at, "ingested_at", FxRateDatasetError)

        if self.ingested_at < self.available_at:
            raise FxRateDatasetError("ingestion time cannot precede availability time")


def select_fx_rate_snapshots(
    snapshots: Iterable[FxRateSnapshot],
    *,
    source_id: str,
    pair: CurrencyPair,
    kind: FxRateKind,
    at_timestamp: datetime,
    pricing_as_of_date: MarketDate,
) -> tuple[FxRateSnapshot, ...]:
    """Select point-in-time-safe FX rate snapshots chronologically up to pricing as-of date.

    Rules:
    - Only snapshots matching `source_id`, directional `pair`, exact `kind`, published on or before
      `at_timestamp` (`available_at <= at_timestamp`), and with
      `market_date <= pricing_as_of_date` are eligible.
    - For any market date, the snapshot published latest (`(available_at, ingested_at)`)
      supersedes earlier observations once its `available_at` timestamp has passed.
    - Observations from different sources, pairs, or kinds are never mixed.
    - The returned tuple is sorted chronologically by market date.
    """
    validate_utc_timestamp(at_timestamp, "prediction timestamp", FxRateDatasetError)

    eligible = _eligible_snapshots(
        snapshots,
        source_id=source_id,
        pair=pair,
        kind=kind,
        at_timestamp=at_timestamp,
        pricing_as_of_date=pricing_as_of_date,
    )
    if not eligible:
        return ()

    latest_by_date = latest_corrections_by_date(eligible, lambda s: s.observation.market_date)
    return tuple(sorted(latest_by_date.values(), key=lambda s: s.observation.market_date))


def _eligible_snapshots(
    snapshots: Iterable[FxRateSnapshot],
    *,
    source_id: str,
    pair: CurrencyPair,
    kind: FxRateKind,
    at_timestamp: datetime,
    pricing_as_of_date: MarketDate,
) -> list[FxRateSnapshot]:
    return [
        snapshot
        for snapshot in snapshots
        if snapshot.source_id == source_id
        and snapshot.observation.pair == pair
        and snapshot.observation.kind == kind
        and snapshot.available_at <= at_timestamp
        and snapshot.observation.market_date <= pricing_as_of_date
    ]
