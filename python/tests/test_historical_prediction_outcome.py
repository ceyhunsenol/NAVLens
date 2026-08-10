"""Tests for HistoricalPredictionRecord and SkippedPredictionRecord."""

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime

import pytest
from navlens import MarketDate, PeriodDecimalReturn, ReturnPeriod
from navlens.prediction import SingleReturnPredictionResult
from navlens.prediction.historical import (
    HistoricalPredictionRecord,
    InsufficientVisiblePredictionHistorySkip,
    InvalidHistoricalPredictionOutcomeError,
    MissingRealizedObservationSkip,
    NoEligiblePredictionSnapshotsSkip,
    SkippedPredictionRecord,
    TargetObservationNotYetAvailableSkip,
)
from tests.historical_prediction_fixtures import (
    make_prediction_result,
    make_request,
    make_snapshot,
)


def _valid_record_components() -> dict[str, object]:
    pred_res = make_prediction_result()
    last_obs_date = pred_res.last_observation_date  # 2026-01-10
    target_date = pred_res.target_date  # 2026-01-11

    req = make_request(
        prediction_date=pred_res.prediction_date,
        pricing_as_of_date=pred_res.pricing_as_of_date,
        target_date=target_date,
        prediction_timestamp=pred_res.prediction_timestamp,
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )

    realized_start = make_snapshot(
        fund_id=pred_res.fund_id,
        source_id=pred_res.source_id,
        market_date=date(2026, 1, 10),
        price=102.0,
        available_at=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
    )
    realized_end = make_snapshot(
        fund_id=pred_res.fund_id,
        source_id=pred_res.source_id,
        market_date=date(2026, 1, 11),
        price=104.0,
        available_at=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )
    ret_period = ReturnPeriod(last_obs_date, target_date)
    realized_return = PeriodDecimalReturn(ret_period, 0.0196)

    return {
        "request": req,
        "prediction_result": pred_res,
        "realized_period_return": realized_return,
        "realized_start_snapshot": realized_start,
        "realized_end_snapshot": realized_end,
    }


def test_valid_historical_prediction_record_construction_and_immutability() -> None:
    kwargs = _valid_record_components()
    record = HistoricalPredictionRecord(**kwargs)  # type: ignore[arg-type]

    assert record.fund_id == record.prediction_result.fund_id
    assert record.source_id == record.prediction_result.source_id
    assert record.predicted_return_decimal == record.prediction_result.expected_return_decimal
    assert record.realized_return_decimal == 0.0196

    with pytest.raises(FrozenInstanceError):
        record.request = None  # type: ignore[misc]


def test_evaluation_time_corrected_start_snapshot_accepted() -> None:
    kwargs = _valid_record_components()
    pred_res: SingleReturnPredictionResult = kwargs["prediction_result"]  # type: ignore[assignment]

    # Create a new start snapshot object with a corrected price (e.g. 102.5 instead of 102.0)
    # published at 2026-01-11 09:00, which is <= evaluation_timestamp (18:00)
    corrected_start = make_snapshot(
        fund_id=pred_res.fund_id,
        source_id=pred_res.source_id,
        market_date=date(2026, 1, 10),
        price=102.5,
        available_at=datetime(2026, 1, 11, 9, 0, tzinfo=UTC),
    )
    kwargs["realized_start_snapshot"] = corrected_start
    record = HistoricalPredictionRecord(**kwargs)  # type: ignore[arg-type]
    assert record.realized_start_snapshot.observation.unit_price.value == 102.5


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("request", "invalid_request"),
        ("prediction_result", "invalid_prediction_result"),
        ("realized_period_return", "invalid_return"),
        ("realized_start_snapshot", "invalid_snapshot"),
        ("realized_end_snapshot", "invalid_snapshot"),
    ],
)
def test_historical_prediction_record_rejects_wrong_field_types(
    field: str, invalid_value: object
) -> None:
    kwargs = _valid_record_components()
    kwargs[field] = invalid_value
    with pytest.raises(InvalidHistoricalPredictionOutcomeError):
        HistoricalPredictionRecord(**kwargs)  # type: ignore[arg-type]


def test_historical_prediction_record_rejects_request_prediction_mismatches() -> None:
    kwargs = _valid_record_components()

    # Mismatched prediction_date in request
    bad_req = make_request(
        prediction_date=MarketDate(2026, 1, 12), target_date=MarketDate(2026, 1, 13)
    )
    kwargs["request"] = bad_req
    with pytest.raises(InvalidHistoricalPredictionOutcomeError):
        HistoricalPredictionRecord(**kwargs)  # type: ignore[arg-type]


def test_historical_prediction_record_rejects_realized_period_boundary_mismatches() -> None:
    kwargs = _valid_record_components()

    # Period start date does not match prediction_result.last_observation_date
    bad_period = ReturnPeriod(MarketDate(2026, 1, 9), MarketDate(2026, 1, 11))
    kwargs["realized_period_return"] = PeriodDecimalReturn(bad_period, 0.02)
    with pytest.raises(InvalidHistoricalPredictionOutcomeError):
        HistoricalPredictionRecord(**kwargs)  # type: ignore[arg-type]


def test_historical_prediction_record_rejects_realized_snapshot_date_mismatches() -> None:
    kwargs = _valid_record_components()
    pred_res: SingleReturnPredictionResult = kwargs["prediction_result"]  # type: ignore[assignment]

    # Start snapshot date does not match last_observation_date
    bad_start = make_snapshot(
        fund_id=pred_res.fund_id,
        source_id=pred_res.source_id,
        market_date=date(2026, 1, 9),
    )
    kwargs["realized_start_snapshot"] = bad_start
    with pytest.raises(InvalidHistoricalPredictionOutcomeError):
        HistoricalPredictionRecord(**kwargs)  # type: ignore[arg-type]


def test_historical_prediction_record_rejects_fund_source_mismatches() -> None:
    kwargs = _valid_record_components()
    pred_res: SingleReturnPredictionResult = kwargs["prediction_result"]  # type: ignore[assignment]

    # End snapshot fund_id mismatch
    bad_end = make_snapshot(
        fund_id="OTHER_FUND",
        source_id=pred_res.source_id,
        market_date=date(2026, 1, 11),
    )
    kwargs["realized_end_snapshot"] = bad_end
    with pytest.raises(InvalidHistoricalPredictionOutcomeError):
        HistoricalPredictionRecord(**kwargs)  # type: ignore[arg-type]


def test_historical_prediction_record_rejects_snapshot_available_after_evaluation_timestamp() -> (
    None
):
    kwargs = _valid_record_components()
    pred_res: SingleReturnPredictionResult = kwargs["prediction_result"]  # type: ignore[assignment]

    # End snapshot available after evaluation_timestamp (18:00 vs 19:00)
    future_end = make_snapshot(
        fund_id=pred_res.fund_id,
        source_id=pred_res.source_id,
        market_date=date(2026, 1, 11),
        price=104.0,
        available_at=datetime(2026, 1, 11, 19, 0, tzinfo=UTC),
    )
    kwargs["realized_end_snapshot"] = future_end
    with pytest.raises(InvalidHistoricalPredictionOutcomeError):
        HistoricalPredictionRecord(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "skip_reason",
    [
        NoEligiblePredictionSnapshotsSkip(),
        InsufficientVisiblePredictionHistorySkip(),
        TargetObservationNotYetAvailableSkip(),
        MissingRealizedObservationSkip(),
    ],
)
def test_skipped_prediction_record_valid_construction_and_immutability(
    skip_reason: object,
) -> None:
    req = make_request()
    record = SkippedPredictionRecord(request=req, reason=skip_reason)  # type: ignore[arg-type]
    assert record.request == req
    assert record.reason == skip_reason

    with pytest.raises(FrozenInstanceError):
        record.request = None  # type: ignore[misc]


@pytest.mark.parametrize(
    ("req", "reason"),
    [
        ("invalid_request", NoEligiblePredictionSnapshotsSkip()),
        (make_request(), "invalid_reason"),
    ],
)
def test_skipped_prediction_record_rejects_invalid_types(req: object, reason: object) -> None:
    with pytest.raises(InvalidHistoricalPredictionOutcomeError):
        SkippedPredictionRecord(request=req, reason=reason)  # type: ignore[arg-type]
