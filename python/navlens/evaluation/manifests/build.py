"""Explicit TEFAS evaluation-to-manifest mapping."""

from datetime import date, datetime
from uuid import UUID, uuid4

from navlens.sources.artifact_digest import sha256_artifact
from navlens.sources.tefas import TefasPriceRequest

from ..comparison import ModelComparisonEntry
from ..records import WalkForwardRecord
from ..tefas_backtest import TefasBacktestResult
from .records import (
    SCHEMA_VERSION,
    TARGET_DEFINITION,
    BacktestRunManifest,
    MetricsManifest,
    ModelRunManifest,
    PredictionManifest,
    RunConfigurationManifest,
    SourceArtifactManifest,
)


def build_tefas_run_manifest(
    result: TefasBacktestResult,
    request: TefasPriceRequest,
    acquisition_as_of: date,
    generated_at: datetime,
    run_id: UUID | None = None,
) -> BacktestRunManifest:
    """Map one completed TEFAS comparison into a versioned manifest."""
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("manifest generation timestamp must include a timezone")
    return BacktestRunManifest(
        schema_version=SCHEMA_VERSION,
        run_id=str(run_id or uuid4()),
        generated_at=generated_at,
        fund_id=result.dataset.fund_id,
        target_definition=TARGET_DEFINITION,
        configuration=_configuration(result),
        source=_source(result, request, acquisition_as_of),
        models=tuple(_model(entry) for entry in result.comparison.entries),
    )


def _configuration(result: TefasBacktestResult) -> RunConfigurationManifest:
    estimator = result.estimator
    return RunConfigurationManifest(
        initial_training_returns=estimator.initial_training_size,
        confidence_level=estimator.confidence_level,
        linear_lookback=estimator.lookback,
    )


def _source(
    result: TefasBacktestResult,
    request: TefasPriceRequest,
    acquisition_as_of: date,
) -> SourceArtifactManifest:
    return SourceArtifactManifest(
        provider="tefas",
        path=str(result.dataset.source_path),
        sha256=sha256_artifact(result.dataset.source_path),
        from_cache=result.acquisition.from_cache,
        acquisition_as_of=acquisition_as_of,
        requested_start_date=request.start_date,
        requested_end_date=request.end_date,
        source_record_count=result.dataset.source_row_count,
    )


def _model(entry: ModelComparisonEntry) -> ModelRunManifest:
    first_record = entry.result.records[0]
    metrics = entry.result.metrics
    interval = metrics.interval
    return ModelRunManifest(
        model_name=entry.model_name,
        model_version=entry.model_version,
        feature_schema_version=first_record.feature_schema_version,
        metrics=MetricsManifest(
            sample_count=metrics.sample_count,
            mean_absolute_error_decimal=metrics.mean_absolute_error,
            mean_error_decimal=metrics.mean_error,
            root_mean_squared_error_decimal=metrics.root_mean_squared_error,
            direction_accuracy=metrics.direction_accuracy,
            interval_coverage=interval.coverage if interval is not None else None,
            interval_mean_width_decimal=(interval.mean_width if interval is not None else None),
        ),
        predictions=tuple(_prediction(record) for record in entry.result.records),
    )


def _prediction(record: WalkForwardRecord) -> PredictionManifest:
    return PredictionManifest(
        prediction_date=record.prediction_date.date(),
        target_date=record.target_date.date(),
        predicted_return_decimal=record.predicted_return,
        actual_return_decimal=record.actual_return,
        lower_bound_decimal=record.lower_bound,
        upper_bound_decimal=record.upper_bound,
        training_start=record.training_start.date(),
        training_end=record.training_end.date(),
    )
