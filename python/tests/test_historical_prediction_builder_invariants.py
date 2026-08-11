"""Tests for historical prediction dataset builder fatal invariants and schedule precedence."""

from collections.abc import Iterable
from datetime import UTC, date, datetime

import pytest
from navlens import MarketDate
from navlens.datasets import FundUnitPriceSnapshot
from navlens.prediction.historical import (
    DecreasingHistoricalPredictionScheduleError,
    MissingHistoricalPredictionStartObservationError,
    UnexpectedHistoricalPredictionReturnCardinalityError,
    build_historical_prediction_dataset,
)
from tests.historical_prediction_fixtures import (
    make_request,
    make_scope,
    make_snapshot,
    sample_snapshots,
)


def test_missing_evaluation_start_observation_raises_fatal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = make_scope()
    snapshots = sample_snapshots(count=10)
    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )

    def _mock_select(
        snaps: Iterable[FundUnitPriceSnapshot],
        *,
        source_id: str,
        fund_id: str,
        at_timestamp: datetime,
        pricing_as_of_date: MarketDate,
    ) -> tuple[FundUnitPriceSnapshot, ...]:
        if at_timestamp == req.evaluation_timestamp:
            return ()
        from navlens.datasets import select_fund_unit_price_snapshots

        return select_fund_unit_price_snapshots(
            snaps,
            source_id=source_id,
            fund_id=fund_id,
            at_timestamp=at_timestamp,
            pricing_as_of_date=pricing_as_of_date,
        )

    monkeypatch.setattr(
        "navlens.prediction.historical._period.select_fund_unit_price_snapshots",
        _mock_select,
    )

    with pytest.raises(MissingHistoricalPredictionStartObservationError):
        build_historical_prediction_dataset(scope, [req], snapshots)


def test_unexpected_native_return_cardinality_raises_fatal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = make_scope()
    snapshots = sample_snapshots(count=10)
    snapshots.append(
        make_snapshot(
            market_date=date(2026, 1, 11),
            available_at=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        )
    )
    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )

    monkeypatch.setattr(
        "navlens.prediction.historical._period.calculate_price_period_returns",
        lambda fund_id, obs: [],
    )

    with pytest.raises(UnexpectedHistoricalPredictionReturnCardinalityError):
        build_historical_prediction_dataset(scope, [req], snapshots)


def test_schedule_failure_bypasses_prediction_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope = make_scope()
    snapshots = sample_snapshots(count=10)

    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 9),
        target_date=MarketDate(2026, 1, 12),
    )

    prediction_executed = False

    def mock_predict(*args: object, **kwargs: object) -> object:
        nonlocal prediction_executed
        prediction_executed = True
        raise RuntimeError("Predict should not be called!")

    monkeypatch.setattr(
        "navlens.prediction.historical._period.predict_next_published_nav_return_from_snapshots",
        mock_predict,
    )

    with pytest.raises(DecreasingHistoricalPredictionScheduleError):
        build_historical_prediction_dataset(scope, [req1, req2], snapshots)

    assert not prediction_executed
