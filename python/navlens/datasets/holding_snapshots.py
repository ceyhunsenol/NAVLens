"""Publication-time-safe holdings dataset snapshots and selection logic."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from navlens import HoldingPosition, MarketDate

from ._timestamps import validate_utc_timestamp
from .errors import HoldingDatasetError


@dataclass(frozen=True, slots=True)
class HoldingSnapshot:
    """A dataset-level holdings snapshot for a fund at a specific effective date."""

    fund_id: str
    effective_date: MarketDate
    published_at: datetime
    ingested_at: datetime
    source_id: str
    positions: tuple[HoldingPosition, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.fund_id, str) or not self.fund_id:
            raise HoldingDatasetError("fund_id must be a non-empty string")
        if not isinstance(self.source_id, str) or not self.source_id:
            raise HoldingDatasetError("source_id must be a non-empty string")
        if not isinstance(self.effective_date, MarketDate):
            raise HoldingDatasetError("effective_date must be a MarketDate instance")

        validate_utc_timestamp(self.published_at, "published_at", HoldingDatasetError)
        validate_utc_timestamp(self.ingested_at, "ingested_at", HoldingDatasetError)

        if self.ingested_at < self.published_at:
            raise HoldingDatasetError("ingestion time cannot precede publication time")

        positions_tuple = tuple(self.positions)
        if not positions_tuple:
            raise HoldingDatasetError("holding snapshot positions cannot be empty")

        for pos in positions_tuple:
            if not isinstance(pos, HoldingPosition):
                raise HoldingDatasetError(
                    f"all positions must be HoldingPosition instances; got {type(pos).__name__}"
                )

        object.__setattr__(self, "positions", positions_tuple)


def select_latest_holdings_snapshot(
    snapshots: Iterable[HoldingSnapshot],
    *,
    fund_id: str,
    source_id: str,
    at_timestamp: datetime,
) -> HoldingSnapshot | None:
    """Select the latest publication-time-safe holdings snapshot for a requested fund and source.

    Enforces publication-time safety:
    - Only snapshots matching `fund_id`, `source_id`, and published on or
      before `at_timestamp` are eligible.
    - For any effective date, a later correction supersedes an earlier snapshot once the
      correction has been published.
    - Among eligible active snapshots across effective dates, the snapshot with the newest
      effective date is selected.
    """
    validate_utc_timestamp(at_timestamp, "prediction timestamp", HoldingDatasetError)

    eligible = [
        s
        for s in snapshots
        if s.fund_id == fund_id and s.source_id == source_id and s.published_at <= at_timestamp
    ]
    if not eligible:
        return None

    # Resolve corrections per effective date by keeping the snapshot published latest
    effective_map: dict[MarketDate, HoldingSnapshot] = {}
    for snapshot in eligible:
        existing = effective_map.get(snapshot.effective_date)
        if existing is None or (
            snapshot.published_at,
            snapshot.ingested_at,
        ) > (existing.published_at, existing.ingested_at):
            effective_map[snapshot.effective_date] = snapshot

    return max(
        effective_map.values(),
        key=lambda s: (s.effective_date, s.published_at, s.ingested_at),
    )
