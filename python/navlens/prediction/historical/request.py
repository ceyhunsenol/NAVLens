"""Immutable request contract for single point-in-time historical predictions."""

from dataclasses import dataclass
from datetime import datetime

from navlens import MarketDate
from navlens._timestamps import datetime_to_utc_timestamp

from .errors import InvalidHistoricalPredictionRequestError


@dataclass(frozen=True, slots=True)
class HistoricalPredictionRequest:
    """A single point-in-time prediction request boundary for historical evaluation."""

    prediction_date: MarketDate
    pricing_as_of_date: MarketDate
    target_date: MarketDate
    prediction_timestamp: datetime
    evaluation_timestamp: datetime

    def __post_init__(self) -> None:
        """Validate request invariants upon construction."""
        if not isinstance(self.prediction_date, MarketDate):
            raise InvalidHistoricalPredictionRequestError(
                "prediction_date must be a MarketDate instance, "
                f"got {type(self.prediction_date).__name__}"
            )
        if not isinstance(self.pricing_as_of_date, MarketDate):
            raise InvalidHistoricalPredictionRequestError(
                "pricing_as_of_date must be a MarketDate instance, "
                f"got {type(self.pricing_as_of_date).__name__}"
            )
        if not isinstance(self.target_date, MarketDate):
            raise InvalidHistoricalPredictionRequestError(
                f"target_date must be a MarketDate instance, got {type(self.target_date).__name__}"
            )

        pred_ts = datetime_to_utc_timestamp(
            self.prediction_timestamp,
            "prediction_timestamp",
            InvalidHistoricalPredictionRequestError,
        )
        eval_ts = datetime_to_utc_timestamp(
            self.evaluation_timestamp,
            "evaluation_timestamp",
            InvalidHistoricalPredictionRequestError,
        )

        if self.pricing_as_of_date > self.prediction_date:
            raise InvalidHistoricalPredictionRequestError(
                f"pricing_as_of_date ({self.pricing_as_of_date}) cannot be after "
                f"prediction_date ({self.prediction_date})"
            )
        if self.target_date <= self.prediction_date:
            raise InvalidHistoricalPredictionRequestError(
                f"target_date ({self.target_date}) must be strictly after "
                f"prediction_date ({self.prediction_date})"
            )

        if pred_ts.unix_seconds >= eval_ts.unix_seconds:
            raise InvalidHistoricalPredictionRequestError(
                f"prediction_timestamp ({self.prediction_timestamp}) must strictly precede "
                f"evaluation_timestamp ({self.evaluation_timestamp})"
            )
