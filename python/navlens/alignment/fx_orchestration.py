"""Point-in-time FX-aware return contribution orchestration."""

from collections.abc import Iterable
from datetime import date, timedelta

from navlens import CurrencyPair, FxRateSeries, calculate_fx_adjusted_return_contribution
from navlens.datasets import (
    FxRateQuery,
    FxRateSnapshot,
    FxRateSource,
    select_fx_rate_snapshots,
)

from .errors import FxRateSourceMismatchError
from .fx_request import PointInTimeFxReturnContributionRequest
from .fx_result import PointInTimeFxAdjustedReturnContributionResult


def calculate_point_in_time_fx_adjusted_return_contribution(
    request: PointInTimeFxReturnContributionRequest,
    fx_rate_snapshots: Iterable[FxRateSnapshot],
) -> PointInTimeFxAdjustedReturnContributionResult:
    """Calculates portfolio return contribution using point-in-time FX rate snapshots.

    Derives required direct currency pairs from price-covered foreign holdings, selects
    publication-time safe FX rate snapshots, constructs homogeneous FxRateSeries, and
    delegates calculation to Rust.
    """
    snapshots_tuple = tuple(fx_rate_snapshots)
    canonical_pairs = _required_fx_pairs(request)
    fx_candidates, selected_snapshots = _select_fx_candidates(
        request,
        snapshots_tuple,
        canonical_pairs,
    )

    native_result = calculate_fx_adjusted_return_contribution(
        request.alignment_result.report,
        request.target_period,
        fx_candidates,
        request.fx_policy,
    )

    return PointInTimeFxAdjustedReturnContributionResult(
        request=request,
        contribution_result=native_result,
        selected_fx_snapshots=_ordered_snapshots(selected_snapshots),
    )


def calculate_point_in_time_fx_adjusted_return_contribution_from_source(
    request: PointInTimeFxReturnContributionRequest,
    fx_rate_source: FxRateSource,
) -> PointInTimeFxAdjustedReturnContributionResult:
    """Acquire required FX candidates through a provider-neutral source and calculate."""
    if fx_rate_source.source_id != request.fx_source_id:
        raise FxRateSourceMismatchError(
            f"fx_rate_source.source_id ({fx_rate_source.source_id!r}) does not match "
            f"request.fx_source_id ({request.fx_source_id!r})"
        )

    snapshots = _acquire_fx_rates(request, fx_rate_source, _required_fx_pairs(request))
    return calculate_point_in_time_fx_adjusted_return_contribution(request, snapshots)


def _required_fx_pairs(
    request: PointInTimeFxReturnContributionRequest,
) -> tuple[CurrencyPair, ...]:
    fund_base = request.alignment_result.request.policy.fund_base_currency
    pairs = {
        CurrencyPair(covered.series.currency, fund_base)
        for covered in request.alignment_result.report.covered
        if covered.series.currency != fund_base
    }
    return tuple(
        sorted(
            pairs,
            key=lambda pair: (pair.base_currency.code, pair.quote_currency.code),
        )
    )


def _acquire_fx_rates(
    request: PointInTimeFxReturnContributionRequest,
    source: FxRateSource,
    pairs: tuple[CurrencyPair, ...],
) -> tuple[FxRateSnapshot, ...]:
    period_start = date.fromisoformat(str(request.target_period.period_start_date))
    period_end = date.fromisoformat(str(request.target_period.period_end_date))
    query_start = period_start - timedelta(days=request.fx_policy.max_fx_staleness_calendar_days)
    acquired: list[FxRateSnapshot] = []
    for pair in pairs:
        query = FxRateQuery(
            pair=pair,
            kind=request.fx_policy.required_fx_rate_kind,
            start_date=query_start,
            end_date=period_end,
        )
        acquired.extend(source.fetch_fx_rates(query))
    return tuple(acquired)


def _select_fx_candidates(
    request: PointInTimeFxReturnContributionRequest,
    snapshots: tuple[FxRateSnapshot, ...],
    pairs: tuple[CurrencyPair, ...],
) -> tuple[list[FxRateSeries], list[FxRateSnapshot]]:
    candidates: list[FxRateSeries] = []
    selected_snapshots: list[FxRateSnapshot] = []
    for pair in pairs:
        selected = select_fx_rate_snapshots(
            snapshots,
            source_id=request.fx_source_id,
            pair=pair,
            kind=request.fx_policy.required_fx_rate_kind,
            at_timestamp=request.alignment_result.request.prediction_timestamp,
            pricing_as_of_date=request.alignment_result.request.policy.pricing_as_of_date,
        )
        if selected:
            candidates.append(FxRateSeries([snap.observation for snap in selected]))
            selected_snapshots.extend(selected)
    return candidates, selected_snapshots


def _ordered_snapshots(
    snapshots: Iterable[FxRateSnapshot],
) -> tuple[FxRateSnapshot, ...]:
    return tuple(
        sorted(
            snapshots,
            key=lambda snap: (
                snap.observation.pair.base_currency.code,
                snap.observation.pair.quote_currency.code,
                snap.observation.kind.name,
                snap.observation.market_date,
                snap.available_at,
                snap.ingested_at,
            ),
        )
    )
