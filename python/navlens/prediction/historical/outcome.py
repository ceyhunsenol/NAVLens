"""Outcome contracts for historical prediction datasets."""

from dataclasses import dataclass

from navlens import PeriodDecimalReturn
from navlens.datasets.fund_unit_price_snapshots import FundUnitPriceSnapshot
from navlens.prediction.contracts import SingleReturnPredictionResult

from .errors import InvalidHistoricalPredictionOutcomeError
from .request import HistoricalPredictionRequest
from .skip_reason import (
    HistoricalPredictionSkipReason,
    InsufficientVisiblePredictionHistorySkip,
    MissingRealizedObservationSkip,
    NoEligiblePredictionSnapshotsSkip,
    TargetObservationNotYetAvailableSkip,
)


@dataclass(frozen=True, slots=True)
class HistoricalPredictionRecord:
    """A successfully evaluated single historical prediction outcome."""

    request: HistoricalPredictionRequest
    prediction_result: SingleReturnPredictionResult
    realized_period_return: PeriodDecimalReturn
    realized_start_snapshot: FundUnitPriceSnapshot
    realized_end_snapshot: FundUnitPriceSnapshot

    def __post_init__(self) -> None:
        """Validate outcome invariants upon construction."""
        if not isinstance(self.request, HistoricalPredictionRequest):
            raise InvalidHistoricalPredictionOutcomeError(
                "request must be a HistoricalPredictionRequest instance, "
                f"got {type(self.request).__name__}"
            )
        if not isinstance(self.prediction_result, SingleReturnPredictionResult):
            raise InvalidHistoricalPredictionOutcomeError(
                "prediction_result must be a SingleReturnPredictionResult instance, "
                f"got {type(self.prediction_result).__name__}"
            )
        if not isinstance(self.realized_period_return, PeriodDecimalReturn):
            raise InvalidHistoricalPredictionOutcomeError(
                "realized_period_return must be a PeriodDecimalReturn instance, "
                f"got {type(self.realized_period_return).__name__}"
            )
        if not isinstance(self.realized_start_snapshot, FundUnitPriceSnapshot):
            raise InvalidHistoricalPredictionOutcomeError(
                "realized_start_snapshot must be a FundUnitPriceSnapshot instance, "
                f"got {type(self.realized_start_snapshot).__name__}"
            )
        if not isinstance(self.realized_end_snapshot, FundUnitPriceSnapshot):
            raise InvalidHistoricalPredictionOutcomeError(
                "realized_end_snapshot must be a FundUnitPriceSnapshot instance, "
                f"got {type(self.realized_end_snapshot).__name__}"
            )

        if self.prediction_result.prediction_date != self.request.prediction_date:
            raise InvalidHistoricalPredictionOutcomeError(
                f"prediction_result.prediction_date ({self.prediction_result.prediction_date}) "
                f"does not match request.prediction_date ({self.request.prediction_date})"
            )
        if self.prediction_result.pricing_as_of_date != self.request.pricing_as_of_date:
            raise InvalidHistoricalPredictionOutcomeError(
                "prediction_result.pricing_as_of_date "
                f"({self.prediction_result.pricing_as_of_date}) "
                f"does not match request.pricing_as_of_date ({self.request.pricing_as_of_date})"
            )
        if self.prediction_result.target_date != self.request.target_date:
            raise InvalidHistoricalPredictionOutcomeError(
                f"prediction_result.target_date ({self.prediction_result.target_date}) "
                f"does not match request.target_date ({self.request.target_date})"
            )
        if self.prediction_result.prediction_timestamp != self.request.prediction_timestamp:
            raise InvalidHistoricalPredictionOutcomeError(
                "prediction_result.prediction_timestamp "
                f"({self.prediction_result.prediction_timestamp}) "
                f"does not match request.prediction_timestamp ({self.request.prediction_timestamp})"
            )

        expected_start_date = self.prediction_result.last_observation_date
        expected_end_date = self.request.target_date

        if self.realized_period_return.period_start_date != expected_start_date:
            raise InvalidHistoricalPredictionOutcomeError(
                "realized_period_return.period_start_date "
                f"({self.realized_period_return.period_start_date}) "
                f"must equal prediction_result.last_observation_date ({expected_start_date})"
            )
        if self.realized_period_return.period_end_date != expected_end_date:
            raise InvalidHistoricalPredictionOutcomeError(
                "realized_period_return.period_end_date "
                f"({self.realized_period_return.period_end_date}) "
                f"must equal request.target_date ({expected_end_date})"
            )

        if self.realized_start_snapshot.observation.date != expected_start_date:
            raise InvalidHistoricalPredictionOutcomeError(
                f"realized_start_snapshot date ({self.realized_start_snapshot.observation.date}) "
                f"must equal prediction_result.last_observation_date ({expected_start_date})"
            )
        if self.realized_end_snapshot.observation.date != expected_end_date:
            raise InvalidHistoricalPredictionOutcomeError(
                f"realized_end_snapshot date ({self.realized_end_snapshot.observation.date}) "
                f"must equal request.target_date ({expected_end_date})"
            )

        if self.realized_start_snapshot.fund_id != self.prediction_result.fund_id:
            raise InvalidHistoricalPredictionOutcomeError(
                f"realized_start_snapshot fund_id '{self.realized_start_snapshot.fund_id}' "
                f"does not match prediction_result fund_id '{self.prediction_result.fund_id}'"
            )
        if self.realized_start_snapshot.source_id != self.prediction_result.source_id:
            raise InvalidHistoricalPredictionOutcomeError(
                f"realized_start_snapshot source_id '{self.realized_start_snapshot.source_id}' "
                f"does not match prediction_result source_id '{self.prediction_result.source_id}'"
            )
        if self.realized_end_snapshot.fund_id != self.prediction_result.fund_id:
            raise InvalidHistoricalPredictionOutcomeError(
                f"realized_end_snapshot fund_id '{self.realized_end_snapshot.fund_id}' "
                f"does not match prediction_result fund_id '{self.prediction_result.fund_id}'"
            )
        if self.realized_end_snapshot.source_id != self.prediction_result.source_id:
            raise InvalidHistoricalPredictionOutcomeError(
                f"realized_end_snapshot source_id '{self.realized_end_snapshot.source_id}' "
                f"does not match prediction_result source_id '{self.prediction_result.source_id}'"
            )

        if self.realized_start_snapshot.available_at > self.request.evaluation_timestamp:
            raise InvalidHistoricalPredictionOutcomeError(
                "realized_start_snapshot available_at "
                f"({self.realized_start_snapshot.available_at}) cannot be after "
                f"request.evaluation_timestamp ({self.request.evaluation_timestamp})"
            )
        if self.realized_end_snapshot.available_at > self.request.evaluation_timestamp:
            raise InvalidHistoricalPredictionOutcomeError(
                "realized_end_snapshot available_at "
                f"({self.realized_end_snapshot.available_at}) cannot be after "
                f"request.evaluation_timestamp ({self.request.evaluation_timestamp})"
            )

        if (
            self.realized_start_snapshot.observation.date
            >= self.realized_end_snapshot.observation.date
        ):
            raise InvalidHistoricalPredictionOutcomeError(
                "realized_start_snapshot date "
                f"({self.realized_start_snapshot.observation.date}) must strictly precede "
                f"realized_end_snapshot date ({self.realized_end_snapshot.observation.date})"
            )

    @property
    def fund_id(self) -> str:
        """The canonical fund_id of the prediction."""
        return self.prediction_result.fund_id

    @property
    def source_id(self) -> str:
        """The canonical source_id of the price snapshots."""
        return self.prediction_result.source_id

    @property
    def predicted_return_decimal(self) -> float:
        """The predicted decimal return."""
        return self.prediction_result.expected_return_decimal

    @property
    def realized_return_decimal(self) -> float:
        """The realized decimal return for the period."""
        return self.realized_period_return.return_decimal


@dataclass(frozen=True, slots=True)
class SkippedPredictionRecord:
    """A period skipped during historical replay due to a typed missing-data scenario."""

    request: HistoricalPredictionRequest
    reason: HistoricalPredictionSkipReason

    def __post_init__(self) -> None:
        """Validate skip outcome invariants upon construction."""
        if not isinstance(self.request, HistoricalPredictionRequest):
            raise InvalidHistoricalPredictionOutcomeError(
                "request must be a HistoricalPredictionRequest instance, "
                f"got {type(self.request).__name__}"
            )
        if not isinstance(
            self.reason,
            (
                NoEligiblePredictionSnapshotsSkip,
                InsufficientVisiblePredictionHistorySkip,
                TargetObservationNotYetAvailableSkip,
                MissingRealizedObservationSkip,
            ),
        ):
            raise InvalidHistoricalPredictionOutcomeError(
                "reason must be a valid HistoricalPredictionSkipReason, "
                f"got {type(self.reason).__name__}"
            )


HistoricalPredictionOutcome = HistoricalPredictionRecord | SkippedPredictionRecord
