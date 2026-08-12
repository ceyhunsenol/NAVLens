"""Canonical realized-return evaluation for stored TEFAS predictions."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from navlens import (
    BacktestMetrics,
    BacktestObservation,
    MarketDate,
    PeriodDecimalReturn,
    calculate_price_period_returns,
    evaluate_backtest,
)
from navlens._timestamps import validate_utc_timestamp
from navlens.sources.price_observations import to_price_observations
from navlens.sources.tefas import TEFAS_SOURCE_ID, TefasAcquisitionResult, TefasPriceRecord

from .artifact import SingleReturnPredictionArtifact
from .errors import (
    InvalidPredictionArtifactError,
    MissingRealizedPriceObservationError,
    UnexpectedRealizedReturnCardinalityError,
    UnsupportedPredictionArtifactSourceError,
)


@dataclass(frozen=True, slots=True)
class LivePredictionEvaluationResult:
    """One stored prediction, realized native return, and native metrics."""

    artifact: SingleReturnPredictionArtifact
    realized_return: PeriodDecimalReturn
    metrics: BacktestMetrics
    evaluated_at: datetime
    source_artifact_path: Path
    source_from_cache: bool


def evaluate_tefas_prediction_artifact(
    artifact: SingleReturnPredictionArtifact,
    acquisition: TefasAcquisitionResult,
    *,
    evaluated_at: datetime,
) -> LivePredictionEvaluationResult:
    """Evaluate one artifact against exact TEFAS period-boundary observations."""
    _validate_inputs(artifact, evaluated_at)
    start = _require_record(acquisition.records, artifact, artifact.last_observation_date)
    end = _require_record(acquisition.records, artifact, artifact.target_date)
    period_returns = calculate_price_period_returns(
        artifact.fund_id,
        to_price_observations([start, end]),
    )
    if len(period_returns) != 1:
        raise UnexpectedRealizedReturnCardinalityError(
            f"expected 1 native period return, got {len(period_returns)}"
        )
    realized_return = period_returns[0]
    observation = BacktestObservation(
        artifact.prediction_date,
        artifact.target_date,
        artifact.prediction,
        realized_return.return_decimal,
    )
    metrics = evaluate_backtest(artifact.fund_id, [observation])
    return LivePredictionEvaluationResult(
        artifact,
        realized_return,
        metrics,
        evaluated_at,
        acquisition.payload_path,
        acquisition.from_cache,
    )


def _validate_inputs(
    artifact: SingleReturnPredictionArtifact,
    evaluated_at: datetime,
) -> None:
    if not isinstance(artifact, SingleReturnPredictionArtifact):
        raise InvalidPredictionArtifactError(
            "artifact must be a SingleReturnPredictionArtifact instance"
        )
    if artifact.source_id != TEFAS_SOURCE_ID:
        raise UnsupportedPredictionArtifactSourceError(
            f"TEFAS evaluation does not support source_id={artifact.source_id!r}"
        )
    validate_utc_timestamp(evaluated_at, "evaluated_at", InvalidPredictionArtifactError)
    if evaluated_at <= artifact.prediction_timestamp:
        raise InvalidPredictionArtifactError("evaluated_at must be after prediction_timestamp")


def _require_record(
    records: tuple[TefasPriceRecord, ...],
    artifact: SingleReturnPredictionArtifact,
    required_date: MarketDate,
) -> TefasPriceRecord:
    matches = [
        record
        for record in records
        if record.fund_code == artifact.fund_id and str(record.market_date) == str(required_date)
    ]
    if len(matches) != 1:
        raise MissingRealizedPriceObservationError(
            f"expected exactly one TEFAS observation for fund_id={artifact.fund_id!r}, "
            f"date={required_date}; got {len(matches)}"
        )
    return matches[0]
