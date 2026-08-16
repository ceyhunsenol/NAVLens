"""Point-in-time holdings and security price alignment functions."""

from collections.abc import Iterable, Sequence
from datetime import date

from navlens._native import (
    HoldingPosition,
    align_holdings_prices,
    is_security_price_alignment_supported,
)
from navlens.datasets import (
    HoldingSnapshot,
    SecurityPriceQuery,
    SecurityPriceSnapshot,
    SecurityPriceSource,
    select_latest_holdings_snapshot,
)

from .candidate_selection import select_price_candidates
from .errors import (
    InvalidPriceHistoryStartError,
    MissingHoldingsSnapshotError,
    SecurityPriceSourceMismatchError,
)
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
    return _align_selected_holdings(request, selected_holdings, price_tuple)


def align_point_in_time_from_source(
    request: PointInTimeAlignmentRequest,
    holdings_snapshots: Iterable[HoldingSnapshot],
    security_price_source: SecurityPriceSource,
    price_history_start_date: date,
) -> PointInTimeAlignmentResult:
    """Perform point-in-time holdings and security price alignment using a SecurityPriceSource.

    Selects eligible point-in-time holdings, acquires candidate price snapshots from
    the source for supported holding asset classes (Equity, ETF), and delegates
    matching and coverage arithmetic to the shared alignment core.
    """
    _validate_source_and_dates(request, security_price_source, price_history_start_date)

    holdings_tuple = tuple(holdings_snapshots)
    selected_holdings = _select_holdings(request, holdings_tuple)

    acquired_snapshots = _acquire_security_prices(
        security_price_source,
        selected_holdings.positions,
        start_date=price_history_start_date,
        end_date=date.fromisoformat(str(request.policy.pricing_as_of_date)),
    )

    return _align_selected_holdings(request, selected_holdings, acquired_snapshots)


def _validate_source_and_dates(
    request: PointInTimeAlignmentRequest,
    security_price_source: SecurityPriceSource,
    price_history_start_date: date,
) -> None:
    if security_price_source.source_id != request.security_price_source_id:
        raise SecurityPriceSourceMismatchError(
            f"security_price_source.source_id ({security_price_source.source_id!r}) "
            f"does not match request.security_price_source_id "
            f"({request.security_price_source_id!r})"
        )
    if type(price_history_start_date) is not date:
        raise InvalidPriceHistoryStartError(
            f"price_history_start_date must be an exact date instance; "
            f"got {type(price_history_start_date).__name__}"
        )
    pricing_as_of_date = date.fromisoformat(str(request.policy.pricing_as_of_date))
    if price_history_start_date > pricing_as_of_date:
        raise InvalidPriceHistoryStartError(
            f"price_history_start_date ({price_history_start_date}) "
            f"cannot be after pricing_as_of_date ({pricing_as_of_date})"
        )


def _acquire_security_prices(
    source: SecurityPriceSource,
    positions: Sequence[HoldingPosition],
    *,
    start_date: date,
    end_date: date,
) -> tuple[SecurityPriceSnapshot, ...]:
    supported_instruments = list(
        dict.fromkeys(
            pos.instrument_id
            for pos in positions
            if is_security_price_alignment_supported(pos.asset_class)
        )
    )
    acquired: list[SecurityPriceSnapshot] = []
    for instrument_id in supported_instruments:
        query = SecurityPriceQuery(
            instrument_id=instrument_id,
            start_date=start_date,
            end_date=end_date,
        )
        snapshots = source.fetch_security_prices(query)
        acquired.extend(snapshots)
    return tuple(acquired)


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


def _align_selected_holdings(
    request: PointInTimeAlignmentRequest,
    selected_holdings: HoldingSnapshot,
    security_price_snapshots: tuple[SecurityPriceSnapshot, ...],
) -> PointInTimeAlignmentResult:
    candidates, selected_price_snapshots = select_price_candidates(
        request,
        selected_holdings.positions,
        security_price_snapshots,
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
