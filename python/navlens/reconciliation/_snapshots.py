"""Shared point-in-time snapshot selection helpers for fund-return reconciliation."""

from collections.abc import Iterable
from datetime import datetime

from navlens import MarketDate, PeriodDecimalReturn, ReturnPeriod, calculate_price_period_returns
from navlens.datasets import FundUnitPriceSnapshot, select_fund_unit_price_snapshots

from .errors import (
    InvalidFundPriceSourceError,
    MissingExactFundUnitPriceSnapshotError,
    UnexpectedNativeReturnCardinalityError,
)


def select_exact_period_fund_return(
    fund_price_snapshots: Iterable[FundUnitPriceSnapshot],
    *,
    fund_id: str,
    fund_price_source_id: str,
    prediction_timestamp: datetime,
    period: ReturnPeriod,
) -> tuple[FundUnitPriceSnapshot, FundUnitPriceSnapshot, PeriodDecimalReturn]:
    """Select exact snapshots and build their canonical native period return."""
    if not isinstance(fund_price_source_id, str) or not fund_price_source_id.strip():
        raise InvalidFundPriceSourceError(fund_price_source_id)

    selected = select_fund_unit_price_snapshots(
        fund_price_snapshots,
        source_id=fund_price_source_id,
        fund_id=fund_id,
        at_timestamp=prediction_timestamp,
        pricing_as_of_date=period.period_end_date,
    )
    start_snapshot = _require_exact_snapshot(
        selected,
        period.period_start_date,
        fund_id,
        fund_price_source_id,
        prediction_timestamp,
    )
    end_snapshot = _require_exact_snapshot(
        selected,
        period.period_end_date,
        fund_id,
        fund_price_source_id,
        prediction_timestamp,
    )
    period_returns = calculate_price_period_returns(
        fund_id,
        [start_snapshot.observation, end_snapshot.observation],
    )
    if len(period_returns) != 1:
        raise UnexpectedNativeReturnCardinalityError(len(period_returns))

    return start_snapshot, end_snapshot, period_returns[0]


def _require_exact_snapshot(
    snapshots: tuple[FundUnitPriceSnapshot, ...],
    required_date: MarketDate,
    fund_id: str,
    source_id: str,
    prediction_timestamp: datetime,
) -> FundUnitPriceSnapshot:
    for snapshot in snapshots:
        if snapshot.observation.date == required_date:
            return snapshot
    raise MissingExactFundUnitPriceSnapshotError(
        fund_id,
        source_id,
        required_date,
        prediction_timestamp,
    )
