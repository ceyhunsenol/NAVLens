"""Canonical schedule validation for historical prediction requests."""

from navlens.prediction.historical.errors import (
    DecreasingHistoricalPredictionScheduleError,
    DuplicateHistoricalPredictionScheduleError,
    InvalidHistoricalPredictionDatasetError,
)
from navlens.prediction.historical.request import HistoricalPredictionRequest


def validate_historical_prediction_schedule(
    requests: tuple[HistoricalPredictionRequest, ...],
) -> None:
    """Validate a sequence of prediction requests for chronological consistency and uniqueness."""
    if not isinstance(requests, tuple):
        raise InvalidHistoricalPredictionDatasetError(
            f"requests must be a tuple, got {type(requests).__name__}"
        )

    for req in requests:
        if not isinstance(req, HistoricalPredictionRequest):
            raise InvalidHistoricalPredictionDatasetError(
                "requests elements must be HistoricalPredictionRequest instances, "
                f"got {type(req).__name__}"
            )

    if len(requests) <= 1:
        return

    # Pass 1: Duplicate detection
    # (must execute before decreasing-order checks for deterministic error precedence)
    seen_target_dates = set()
    seen_periods = set()
    for req in requests:
        period = (req.prediction_date, req.target_date)
        if period in seen_periods:
            raise DuplicateHistoricalPredictionScheduleError(
                f"duplicate period {req.prediction_date} -> {req.target_date} "
                "found in prediction schedule"
            )
        if req.target_date in seen_target_dates:
            raise DuplicateHistoricalPredictionScheduleError(
                f"duplicate target_date {req.target_date} found in prediction schedule"
            )
        seen_target_dates.add(req.target_date)
        seen_periods.add(period)

    # Pass 2: Chronological order validation across consecutive requests
    for i in range(len(requests) - 1):
        curr = requests[i]
        nxt = requests[i + 1]

        if nxt.prediction_date < curr.prediction_date:
            raise DecreasingHistoricalPredictionScheduleError(
                f"prediction_date moved backwards from {curr.prediction_date} "
                f"to {nxt.prediction_date}"
            )
        if nxt.target_date <= curr.target_date:
            raise DecreasingHistoricalPredictionScheduleError(
                f"target_date did not strictly increase from {curr.target_date} "
                f"to {nxt.target_date}"
            )
        if nxt.prediction_timestamp <= curr.prediction_timestamp:
            raise DecreasingHistoricalPredictionScheduleError(
                "prediction_timestamp did not strictly increase from "
                f"{curr.prediction_timestamp} to {nxt.prediction_timestamp}"
            )
        if nxt.evaluation_timestamp < curr.evaluation_timestamp:
            raise DecreasingHistoricalPredictionScheduleError(
                f"evaluation_timestamp moved backwards from {curr.evaluation_timestamp} "
                f"to {nxt.evaluation_timestamp}"
            )
