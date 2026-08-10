"""Dataset container for ordered historical prediction outcomes."""

from dataclasses import dataclass

from ._schedule import validate_historical_prediction_schedule
from .errors import (
    InvalidHistoricalPredictionDatasetError,
    MixedHistoricalPredictionScopeError,
)
from .outcome import (
    HistoricalPredictionOutcome,
    HistoricalPredictionRecord,
    SkippedPredictionRecord,
)
from .scope import HistoricalPredictionEvaluationScope


@dataclass(frozen=True, slots=True)
class HistoricalPredictionDataset:
    """A dataset of ordered point-in-time prediction outcomes and their evaluation scope."""

    scope: HistoricalPredictionEvaluationScope
    outcomes: tuple[HistoricalPredictionOutcome, ...]

    def __post_init__(self) -> None:
        """Validate dataset scope and outcome homogeneity and chronology."""
        if not isinstance(self.scope, HistoricalPredictionEvaluationScope):
            raise InvalidHistoricalPredictionDatasetError(
                "scope must be a HistoricalPredictionEvaluationScope instance, "
                f"got {type(self.scope).__name__}"
            )
        if not isinstance(self.outcomes, tuple):
            raise InvalidHistoricalPredictionDatasetError(
                f"outcomes must be a tuple, got {type(self.outcomes).__name__}"
            )

        requests = []
        for outcome in self.outcomes:
            if not isinstance(outcome, (HistoricalPredictionRecord, SkippedPredictionRecord)):
                raise InvalidHistoricalPredictionDatasetError(
                    "outcomes elements must be HistoricalPredictionRecord or "
                    f"SkippedPredictionRecord, got {type(outcome).__name__}"
                )
            requests.append(outcome.request)

        # Validate schedule chronology across all outcomes
        validate_historical_prediction_schedule(tuple(requests))

        # Scope validation and model metadata homogeneity across successful records
        first_successful: HistoricalPredictionRecord | None = None

        for outcome in self.outcomes:
            if not isinstance(outcome, HistoricalPredictionRecord):
                continue

            rec = outcome
            res = rec.prediction_result

            # Check record alignment with dataset scope
            if res.fund_id != self.scope.fund_id:
                raise MixedHistoricalPredictionScopeError(
                    "fund_id", self.scope.fund_id, res.fund_id, rec.request
                )
            if res.source_id != self.scope.source_id:
                raise MixedHistoricalPredictionScopeError(
                    "source_id", self.scope.source_id, res.source_id, rec.request
                )
            if res.lookback != self.scope.lookback:
                raise MixedHistoricalPredictionScopeError(
                    "lookback", self.scope.lookback, res.lookback, rec.request
                )
            if res.model_version != self.scope.model_version:
                raise MixedHistoricalPredictionScopeError(
                    "model_version", self.scope.model_version, res.model_version, rec.request
                )
            if res.confidence_level != self.scope.confidence_level:
                raise MixedHistoricalPredictionScopeError(
                    "confidence_level",
                    self.scope.confidence_level,
                    res.confidence_level,
                    rec.request,
                )

            if rec.realized_start_snapshot.fund_id != self.scope.fund_id:
                raise MixedHistoricalPredictionScopeError(
                    "realized_start_snapshot.fund_id",
                    self.scope.fund_id,
                    rec.realized_start_snapshot.fund_id,
                    rec.request,
                )
            if rec.realized_start_snapshot.source_id != self.scope.source_id:
                raise MixedHistoricalPredictionScopeError(
                    "realized_start_snapshot.source_id",
                    self.scope.source_id,
                    rec.realized_start_snapshot.source_id,
                    rec.request,
                )
            if rec.realized_end_snapshot.fund_id != self.scope.fund_id:
                raise MixedHistoricalPredictionScopeError(
                    "realized_end_snapshot.fund_id",
                    self.scope.fund_id,
                    rec.realized_end_snapshot.fund_id,
                    rec.request,
                )
            if rec.realized_end_snapshot.source_id != self.scope.source_id:
                raise MixedHistoricalPredictionScopeError(
                    "realized_end_snapshot.source_id",
                    self.scope.source_id,
                    rec.realized_end_snapshot.source_id,
                    rec.request,
                )

            # Homogeneity check across all successful records
            if first_successful is None:
                first_successful = rec
            else:
                first_res = first_successful.prediction_result
                if res.model_name != first_res.model_name:
                    raise MixedHistoricalPredictionScopeError(
                        "model_name", first_res.model_name, res.model_name, rec.request
                    )
                if res.model_version != first_res.model_version:
                    raise MixedHistoricalPredictionScopeError(
                        "model_version", first_res.model_version, res.model_version, rec.request
                    )
                if res.feature_schema_version != first_res.feature_schema_version:
                    raise MixedHistoricalPredictionScopeError(
                        "feature_schema_version",
                        first_res.feature_schema_version,
                        res.feature_schema_version,
                        rec.request,
                    )
                if res.target_definition != first_res.target_definition:
                    raise MixedHistoricalPredictionScopeError(
                        "target_definition",
                        first_res.target_definition,
                        res.target_definition,
                        rec.request,
                    )
                if res.confidence_level != first_res.confidence_level:
                    raise MixedHistoricalPredictionScopeError(
                        "confidence_level",
                        first_res.confidence_level,
                        res.confidence_level,
                        rec.request,
                    )
