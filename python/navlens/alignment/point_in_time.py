"""Point-in-time holdings and security price alignment function."""

from collections.abc import Iterable

from navlens import align_holdings_prices
from navlens.datasets import (
    HoldingSnapshot,
    SecurityPriceSnapshot,
    select_latest_holdings_snapshot,
)

from .candidate_selection import select_price_candidates
from .errors import MissingHoldingsSnapshotError
from .request import PointInTimeAlignmentRequest
from .result import PointInTimeAlignmentResult


def align_point_in_time(
    request: PointInTimeAlignmentRequest,
    holdings_snapshots: Iterable[HoldingSnapshot],
    security_price_snapshots: Iterable[SecurityPriceSnapshot],
) -> PointInTimeAlignmentResult:
    """Perform point-in-time alignment of holdings and security price snapshots.

    Selects eligible publication-time-safe holdings and price snapshots for the
    requested fund and sources, delegates matching and financial arithmetic to Rust,
    and returns the result with complete provenance.
    """
    holdings_tuple = tuple(holdings_snapshots)
    price_tuple = tuple(security_price_snapshots)

    selected_holdings = _select_holdings(request, holdings_tuple)
    candidates, selected_price_snapshots = select_price_candidates(
        request,
        selected_holdings.positions,
        price_tuple,
    )

    report = align_holdings_prices(
        selected_holdings.positions,
        candidates,
        request.policy,
    )

    return PointInTimeAlignmentResult(
        request=request,
        holdings_snapshot=selected_holdings,
        report=report,
        selected_price_snapshots=selected_price_snapshots,
    )


def _select_holdings(
    request: PointInTimeAlignmentRequest,
    snapshots: tuple[HoldingSnapshot, ...],
) -> HoldingSnapshot:
    selected = select_latest_holdings_snapshot(
        snapshots,
        fund_id=request.fund_id,
        source_id=request.holdings_source_id,
        at_timestamp=request.prediction_timestamp,
    )
    if selected is None:
        raise MissingHoldingsSnapshotError(
            request.fund_id,
            request.holdings_source_id,
            request.prediction_timestamp,
        )
    return selected
