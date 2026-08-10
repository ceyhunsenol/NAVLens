"""Tests for validate_historical_prediction_schedule."""

from datetime import UTC, datetime

import pytest
from navlens import MarketDate
from navlens.prediction.historical import (
    DecreasingHistoricalPredictionScheduleError,
    DuplicateHistoricalPredictionScheduleError,
    InvalidHistoricalPredictionDatasetError,
)
from navlens.prediction.historical._schedule import validate_historical_prediction_schedule
from tests.historical_prediction_fixtures import make_request


def test_empty_and_singleton_schedules_are_valid() -> None:
    validate_historical_prediction_schedule(())

    req = make_request()
    validate_historical_prediction_schedule((req,))


def test_valid_multi_request_schedule_preserves_input() -> None:
    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        pricing_as_of_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        pricing_as_of_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )
    schedule = (req1, req2)
    validate_historical_prediction_schedule(schedule)
    assert schedule[0] is req1
    assert schedule[1] is req2


def test_equal_evaluation_timestamps_are_valid() -> None:
    # Batch evaluations performed at the same evaluation_timestamp are valid
    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        pricing_as_of_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 15, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        pricing_as_of_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 15, 18, 0, tzinfo=UTC),  # equal evaluation_timestamp
    )
    validate_historical_prediction_schedule((req1, req2))


def test_rejects_non_tuple_and_invalid_elements() -> None:
    req = make_request()
    with pytest.raises(InvalidHistoricalPredictionDatasetError):
        validate_historical_prediction_schedule([req])  # type: ignore[arg-type]

    with pytest.raises(InvalidHistoricalPredictionDatasetError):
        validate_historical_prediction_schedule((req, "not_a_request"))  # type: ignore[arg-type]


def test_duplicate_target_date_rejection() -> None:
    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),  # duplicate target date
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )
    with pytest.raises(DuplicateHistoricalPredictionScheduleError, match="duplicate target_date"):
        validate_historical_prediction_schedule((req1, req2))


def test_non_adjacent_duplicate_period_rejection() -> None:
    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 13),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 13, 18, 0, tzinfo=UTC),
    )
    duplicate_req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 14, 18, 0, tzinfo=UTC),
    )

    with pytest.raises(DuplicateHistoricalPredictionScheduleError, match="duplicate period"):
        validate_historical_prediction_schedule((req1, req2, duplicate_req1))


def test_duplicate_precedence_before_decreasing_chronology() -> None:
    # Non-adjacent duplicates where timestamps/dates decrease must still raise Duplicate error first
    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 13),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 13, 18, 0, tzinfo=UTC),
    )
    req3 = make_request(
        prediction_date=MarketDate(2026, 1, 8),  # decreasing date & timestamp
        target_date=MarketDate(2026, 1, 12),  # duplicate target date with req1
        prediction_timestamp=datetime(2026, 1, 8, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
    )
    with pytest.raises(DuplicateHistoricalPredictionScheduleError):
        validate_historical_prediction_schedule((req1, req2, req3))


def test_decreasing_prediction_date_rejection() -> None:
    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 9),  # decreasing prediction_date
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )
    with pytest.raises(DecreasingHistoricalPredictionScheduleError):
        validate_historical_prediction_schedule((req1, req2))


def test_non_increasing_target_date_rejection() -> None:
    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 13),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 13, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),  # target_date decreased from Jan 13 to Jan 12
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 13, 18, 0, tzinfo=UTC),
    )
    with pytest.raises(DecreasingHistoricalPredictionScheduleError):
        validate_historical_prediction_schedule((req1, req2))


def test_non_increasing_prediction_timestamp_rejection() -> None:
    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),  # equal prediction_timestamp
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )
    with pytest.raises(DecreasingHistoricalPredictionScheduleError):
        validate_historical_prediction_schedule((req1, req2))


def test_decreasing_evaluation_timestamp_rejection() -> None:
    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 15, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(
            2026, 1, 14, 18, 0, tzinfo=UTC
        ),  # evaluation_timestamp decreased
    )
    with pytest.raises(DecreasingHistoricalPredictionScheduleError):
        validate_historical_prediction_schedule((req1, req2))
