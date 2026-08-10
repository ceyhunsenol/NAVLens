"""Tests for HistoricalPredictionRequest."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest
from navlens import MarketDate
from navlens.prediction.historical import (
    HistoricalPredictionRequest,
    InvalidHistoricalPredictionRequestError,
)


def test_valid_request_construction_and_immutability() -> None:
    request = HistoricalPredictionRequest(
        prediction_date=MarketDate(2026, 1, 15),
        pricing_as_of_date=MarketDate(2026, 1, 15),
        target_date=MarketDate(2026, 1, 16),
        prediction_timestamp=datetime(2026, 1, 15, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 16, 18, 0, 0, tzinfo=UTC),
    )
    assert request.prediction_date == MarketDate(2026, 1, 15)
    assert request.pricing_as_of_date == MarketDate(2026, 1, 15)
    assert request.target_date == MarketDate(2026, 1, 16)
    assert request.prediction_timestamp == datetime(2026, 1, 15, 18, 0, 0, tzinfo=UTC)
    assert request.evaluation_timestamp == datetime(2026, 1, 16, 18, 0, 0, tzinfo=UTC)

    with pytest.raises(FrozenInstanceError):
        request.prediction_date = MarketDate(2026, 1, 20)  # type: ignore[misc]


def test_prediction_date_may_exceed_pricing_as_of_date() -> None:
    # NAVLens explicitly supports prediction_date > pricing_as_of_date
    request = HistoricalPredictionRequest(
        prediction_date=MarketDate(2026, 1, 20),
        pricing_as_of_date=MarketDate(2026, 1, 15),
        target_date=MarketDate(2026, 1, 21),
        prediction_timestamp=datetime(2026, 1, 20, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 21, 18, 0, 0, tzinfo=UTC),
    )
    assert request.prediction_date == MarketDate(2026, 1, 20)
    assert request.pricing_as_of_date == MarketDate(2026, 1, 15)


def test_prediction_timestamp_date_need_not_match_prediction_date() -> None:
    # No artificial calendar-day equality rule between prediction_timestamp UTC day
    # and prediction_date
    request = HistoricalPredictionRequest(
        prediction_date=MarketDate(2026, 1, 15),
        pricing_as_of_date=MarketDate(2026, 1, 15),
        target_date=MarketDate(2026, 1, 16),
        prediction_timestamp=datetime(2026, 1, 14, 23, 59, 59, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 16, 18, 0, 0, tzinfo=UTC),
    )
    assert request.prediction_date == MarketDate(2026, 1, 15)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("prediction_date", "2026-01-15"),
        ("prediction_date", datetime(2026, 1, 15, tzinfo=UTC)),
        ("pricing_as_of_date", 20260115),
        ("target_date", None),
    ],
)
def test_invalid_market_date_types(field: str, invalid_value: object) -> None:
    kwargs = {
        "prediction_date": MarketDate(2026, 1, 15),
        "pricing_as_of_date": MarketDate(2026, 1, 15),
        "target_date": MarketDate(2026, 1, 16),
        "prediction_timestamp": datetime(2026, 1, 15, 18, 0, 0, tzinfo=UTC),
        "evaluation_timestamp": datetime(2026, 1, 16, 18, 0, 0, tzinfo=UTC),
    }
    kwargs[field] = invalid_value
    with pytest.raises(InvalidHistoricalPredictionRequestError):
        HistoricalPredictionRequest(**kwargs)


@pytest.mark.parametrize(
    ("field", "invalid_dt"),
    [
        ("prediction_timestamp", datetime(2026, 1, 15, 18, 0, 0)),  # naive
        (
            "prediction_timestamp",
            datetime(2026, 1, 15, 18, 0, 0, tzinfo=timezone(timedelta(hours=3))),
        ),
        ("prediction_timestamp", "2026-01-15T18:00:00Z"),  # wrong type
        ("prediction_timestamp", datetime(2026, 1, 15, 18, 0, 0, 500)),  # microseconds
        ("evaluation_timestamp", datetime(2026, 1, 16, 18, 0, 0)),  # naive
        (
            "evaluation_timestamp",
            datetime(2026, 1, 16, 18, 0, 0, tzinfo=timezone(timedelta(hours=3))),
        ),
        ("evaluation_timestamp", datetime(2026, 1, 16, 18, 0, 0, 10000)),  # microseconds
    ],
)
def test_invalid_timestamp_precision_or_timezone(field: str, invalid_dt: object) -> None:
    kwargs = {
        "prediction_date": MarketDate(2026, 1, 15),
        "pricing_as_of_date": MarketDate(2026, 1, 15),
        "target_date": MarketDate(2026, 1, 16),
        "prediction_timestamp": datetime(2026, 1, 15, 18, 0, 0, tzinfo=UTC),
        "evaluation_timestamp": datetime(2026, 1, 16, 18, 0, 0, tzinfo=UTC),
    }
    kwargs[field] = invalid_dt
    with pytest.raises(InvalidHistoricalPredictionRequestError):
        HistoricalPredictionRequest(**kwargs)


def test_pricing_as_of_date_after_prediction_date_rejection() -> None:
    with pytest.raises(InvalidHistoricalPredictionRequestError):
        HistoricalPredictionRequest(
            prediction_date=MarketDate(2026, 1, 15),
            pricing_as_of_date=MarketDate(
                2026, 1, 16
            ),  # invalid: pricing_as_of_date > prediction_date
            target_date=MarketDate(2026, 1, 17),
            prediction_timestamp=datetime(2026, 1, 15, 18, 0, 0, tzinfo=UTC),
            evaluation_timestamp=datetime(2026, 1, 17, 18, 0, 0, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    "target_date",
    [
        MarketDate(2026, 1, 15),  # equal to prediction_date
        MarketDate(2026, 1, 14),  # before prediction_date
    ],
)
def test_target_date_not_after_prediction_date_rejection(target_date: MarketDate) -> None:
    with pytest.raises(InvalidHistoricalPredictionRequestError):
        HistoricalPredictionRequest(
            prediction_date=MarketDate(2026, 1, 15),
            pricing_as_of_date=MarketDate(2026, 1, 15),
            target_date=target_date,
            prediction_timestamp=datetime(2026, 1, 15, 18, 0, 0, tzinfo=UTC),
            evaluation_timestamp=datetime(2026, 1, 16, 18, 0, 0, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    "eval_ts",
    [
        datetime(2026, 1, 15, 18, 0, 0, tzinfo=UTC),  # equal to prediction_timestamp
        datetime(2026, 1, 15, 17, 59, 59, tzinfo=UTC),  # before prediction_timestamp
    ],
)
def test_prediction_timestamp_not_strictly_before_evaluation_timestamp_rejection(
    eval_ts: datetime,
) -> None:
    with pytest.raises(InvalidHistoricalPredictionRequestError):
        HistoricalPredictionRequest(
            prediction_date=MarketDate(2026, 1, 15),
            pricing_as_of_date=MarketDate(2026, 1, 15),
            target_date=MarketDate(2026, 1, 16),
            prediction_timestamp=datetime(2026, 1, 15, 18, 0, 0, tzinfo=UTC),
            evaluation_timestamp=eval_ts,
        )
