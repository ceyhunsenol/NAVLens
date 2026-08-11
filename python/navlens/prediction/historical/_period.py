"""Private per-period evaluation logic for point-in-time historical prediction dataset."""

from navlens import MarketDate, calculate_price_period_returns
from navlens.datasets import select_fund_unit_price_snapshots
from navlens.datasets.fund_unit_price_snapshots import FundUnitPriceSnapshot
from navlens.prediction.contracts import SingleReturnPredictionResult
from navlens.prediction.errors import (
    InsufficientVisibleHistoryError,
    NoEligibleSnapshotsError,
)
from navlens.prediction.orchestration import (
    predict_next_published_nav_return_from_snapshots,
)

from .errors import (
    MissingHistoricalPredictionStartObservationError,
    UnexpectedHistoricalPredictionReturnCardinalityError,
)
from .outcome import (
    HistoricalPredictionOutcome,
    HistoricalPredictionRecord,
    SkippedPredictionRecord,
)
from .request import HistoricalPredictionRequest
from .scope import HistoricalPredictionEvaluationScope
from .skip_reason import (
    InsufficientVisiblePredictionHistorySkip,
    MissingRealizedObservationSkip,
    NoEligiblePredictionSnapshotsSkip,
    TargetObservationNotYetAvailableSkip,
)


def evaluate_historical_prediction_period(
    request: HistoricalPredictionRequest,
    scope: HistoricalPredictionEvaluationScope,
    materialized_snapshots: tuple[FundUnitPriceSnapshot, ...],
) -> HistoricalPredictionOutcome:
    """Evaluate a single historical prediction request against materialized price snapshots."""
    prediction_or_skip = _predict_or_skip(request, scope, materialized_snapshots)
    if isinstance(prediction_or_skip, SkippedPredictionRecord):
        return prediction_or_skip

    return _evaluate_realized_period(request, scope, prediction_or_skip, materialized_snapshots)


def _predict_or_skip(
    request: HistoricalPredictionRequest,
    scope: HistoricalPredictionEvaluationScope,
    materialized_snapshots: tuple[FundUnitPriceSnapshot, ...],
) -> SingleReturnPredictionResult | SkippedPredictionRecord:
    """Execute prediction phase, catching eligible/history exceptions into typed skips."""
    try:
        return predict_next_published_nav_return_from_snapshots(
            materialized_snapshots,
            fund_id=scope.fund_id,
            source_id=scope.source_id,
            prediction_timestamp=request.prediction_timestamp,
            prediction_date=request.prediction_date,
            pricing_as_of_date=request.pricing_as_of_date,
            target_date=request.target_date,
            lookback=scope.lookback,
            minimum_training_returns=scope.minimum_training_returns,
            confidence_level=scope.confidence_level,
            model_version=scope.model_version,
        )
    except NoEligibleSnapshotsError:
        return SkippedPredictionRecord(request, NoEligiblePredictionSnapshotsSkip())
    except InsufficientVisibleHistoryError:
        return SkippedPredictionRecord(request, InsufficientVisiblePredictionHistorySkip())


def _evaluate_realized_period(
    request: HistoricalPredictionRequest,
    scope: HistoricalPredictionEvaluationScope,
    prediction_result: SingleReturnPredictionResult,
    materialized_snapshots: tuple[FundUnitPriceSnapshot, ...],
) -> HistoricalPredictionOutcome:
    """Evaluate target realized return for a successful prediction result."""
    start_date = prediction_result.last_observation_date
    end_date = request.target_date

    eval_snapshots = select_fund_unit_price_snapshots(
        materialized_snapshots,
        source_id=scope.source_id,
        fund_id=scope.fund_id,
        at_timestamp=request.evaluation_timestamp,
        pricing_as_of_date=end_date,
    )

    realized_start = _find_snapshot_by_date(eval_snapshots, start_date)
    if realized_start is None:
        raise MissingHistoricalPredictionStartObservationError(
            f"Missing evaluation-time start observation for date {start_date} "
            f"at timestamp {request.evaluation_timestamp.isoformat()}"
        )

    realized_end = _find_snapshot_by_date(eval_snapshots, end_date)
    if realized_end is None:
        return _classify_missing_target_skip(request, scope, materialized_snapshots, end_date)

    return _build_realized_record(request, scope, prediction_result, realized_start, realized_end)


def _build_realized_record(
    request: HistoricalPredictionRequest,
    scope: HistoricalPredictionEvaluationScope,
    prediction_result: SingleReturnPredictionResult,
    realized_start: FundUnitPriceSnapshot,
    realized_end: FundUnitPriceSnapshot,
) -> HistoricalPredictionRecord:
    """Calculate realized period return and construct outcome record."""
    period_returns = calculate_price_period_returns(
        scope.fund_id,
        [realized_start.observation, realized_end.observation],
    )
    if len(period_returns) != 1:
        raise UnexpectedHistoricalPredictionReturnCardinalityError(
            f"Expected exactly 1 period return from calculate_price_period_returns, "
            f"got {len(period_returns)}"
        )

    return HistoricalPredictionRecord(
        request=request,
        prediction_result=prediction_result,
        realized_period_return=period_returns[0],
        realized_start_snapshot=realized_start,
        realized_end_snapshot=realized_end,
    )


def _find_snapshot_by_date(
    snapshots: tuple[FundUnitPriceSnapshot, ...],
    target_date: MarketDate,
) -> FundUnitPriceSnapshot | None:
    """Find snapshot matching target observation date."""
    for snapshot in snapshots:
        if snapshot.observation.date == target_date:
            return snapshot
    return None


def _classify_missing_target_skip(
    request: HistoricalPredictionRequest,
    scope: HistoricalPredictionEvaluationScope,
    materialized_snapshots: tuple[FundUnitPriceSnapshot, ...],
    target_date: MarketDate,
) -> SkippedPredictionRecord:
    """Classify missing target snapshot as future-available skip or missing skip."""
    has_future_target = any(
        s.fund_id == scope.fund_id
        and s.source_id == scope.source_id
        and s.observation.date == target_date
        for s in materialized_snapshots
    )
    if has_future_target:
        return SkippedPredictionRecord(request, TargetObservationNotYetAvailableSkip())
    return SkippedPredictionRecord(request, MissingRealizedObservationSkip())
