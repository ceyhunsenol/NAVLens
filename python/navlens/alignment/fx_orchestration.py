"""Point-in-time FX-aware return contribution orchestration."""

from collections.abc import Iterable

from navlens import CurrencyPair, FxRateSeries, calculate_fx_adjusted_return_contribution
from navlens.datasets import FxRateSnapshot, select_fx_rate_snapshots

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

    fund_base = request.alignment_result.request.policy.fund_base_currency
    raw_pairs: set[CurrencyPair] = set()

    for covered in request.alignment_result.report.covered:
        sec_currency = covered.series.currency
        if sec_currency != fund_base:
            raw_pairs.add(CurrencyPair(sec_currency, fund_base))

    canonical_pairs = sorted(
        raw_pairs,
        key=lambda pair: (pair.base_currency.code, pair.quote_currency.code),
    )

    fx_candidates: list[FxRateSeries] = []
    selected_snapshots: list[FxRateSnapshot] = []

    for pair in canonical_pairs:
        selected = select_fx_rate_snapshots(
            snapshots_tuple,
            source_id=request.fx_source_id,
            pair=pair,
            kind=request.fx_policy.required_fx_rate_kind,
            at_timestamp=request.alignment_result.request.prediction_timestamp,
            pricing_as_of_date=request.alignment_result.request.policy.pricing_as_of_date,
        )
        if selected:
            series = FxRateSeries([snap.observation for snap in selected])
            fx_candidates.append(series)
            selected_snapshots.extend(selected)

    ordered_snapshots = tuple(
        sorted(
            selected_snapshots,
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

    native_result = calculate_fx_adjusted_return_contribution(
        request.alignment_result.report,
        request.target_period,
        fx_candidates,
        request.fx_policy,
    )

    return PointInTimeFxAdjustedReturnContributionResult(
        request=request,
        contribution_result=native_result,
        selected_fx_snapshots=ordered_snapshots,
    )
