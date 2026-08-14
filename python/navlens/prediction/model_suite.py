"""Same-snapshot execution contract for all implemented prediction baselines."""

from dataclasses import dataclass
from datetime import datetime

from navlens import MarketDate
from navlens.sources.tefas import TEFAS_SOURCE_ID, TefasAcquisitionResult

from .contracts import SingleReturnPredictionResult
from .freshness import FundUnitPriceFreshnessPolicy
from .options import PredictionModelKind, PredictionModelOptions
from .orchestration import predict_next_published_nav_return_from_snapshots
from .tefas import prepare_tefas_prediction_snapshots


@dataclass(frozen=True, slots=True)
class PredictionModelSuiteOptions:
    """Configuration shared by every estimator in one model suite."""

    lookback: int = 5
    minimum_training_returns: int | None = None
    confidence_level: float = 0.90
    model_version: str = "v1"


def prediction_model_suite_options_from_model_options(
    options: PredictionModelOptions,
) -> PredictionModelSuiteOptions:
    """Extract model-suite options from prediction model options (omitting model_kind)."""
    return PredictionModelSuiteOptions(
        options.lookback,
        options.minimum_training_returns,
        options.confidence_level,
        options.model_version,
    )


@dataclass(frozen=True, slots=True)
class PredictionModelSuiteResult:
    """Predictions from every baseline over one identical visible snapshot set."""

    predictions: tuple[SingleReturnPredictionResult, ...]

    def __post_init__(self) -> None:
        if len(self.predictions) != len(PredictionModelKind):
            raise ValueError("model suite must contain every implemented prediction model")
        first = self.predictions[0]
        if not all(isinstance(item, SingleReturnPredictionResult) for item in self.predictions):
            raise ValueError("model suite entries must be SingleReturnPredictionResult instances")
        if len({item.model_name for item in self.predictions}) != len(self.predictions):
            raise ValueError("model suite predictions must have unique model identities")
        shared = _shared_provenance(first)
        if not all(_shared_provenance(item) == shared for item in self.predictions):
            raise ValueError("model suite predictions must share point-in-time provenance")


def predict_tefas_model_suite(
    acquisition: TefasAcquisitionResult,
    *,
    acquired_at: datetime,
    prediction_date: MarketDate,
    target_date: MarketDate,
    options: PredictionModelSuiteOptions | None = None,
    freshness: FundUnitPriceFreshnessPolicy | None = None,
) -> PredictionModelSuiteResult:
    """Run every implemented baseline over one acquired TEFAS snapshot set."""
    snapshots = prepare_tefas_prediction_snapshots(
        acquisition,
        acquired_at=acquired_at,
        prediction_date=prediction_date,
        freshness=freshness,
    )
    selected = options or PredictionModelSuiteOptions()
    predictions = tuple(
        predict_next_published_nav_return_from_snapshots(
            snapshots,
            fund_id=snapshots[0].fund_id,
            source_id=TEFAS_SOURCE_ID,
            prediction_timestamp=acquired_at,
            prediction_date=prediction_date,
            pricing_as_of_date=snapshots[-1].observation.date,
            target_date=target_date,
            lookback=selected.lookback,
            minimum_training_returns=selected.minimum_training_returns,
            confidence_level=selected.confidence_level,
            model_version=selected.model_version,
            model_kind=kind,
        )
        for kind in PredictionModelKind
    )
    return PredictionModelSuiteResult(predictions)


def _shared_provenance(result: SingleReturnPredictionResult) -> tuple[object, ...]:
    return (
        result.fund_id,
        result.source_id,
        result.prediction_timestamp,
        result.prediction_date,
        result.pricing_as_of_date,
        result.target_date,
        result.selected_snapshots,
        result.confidence_level,
        result.model_version,
    )
