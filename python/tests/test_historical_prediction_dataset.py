"""Tests for HistoricalPredictionDataset."""

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime

import pytest
from navlens import (
    MarketDate,
    ModelDescriptor,
    PeriodDecimalReturn,
    ReturnPeriod,
    create_return_prediction,
)
from navlens.prediction.historical import (
    DecreasingHistoricalPredictionScheduleError,
    HistoricalPredictionDataset,
    HistoricalPredictionEvaluationScope,
    HistoricalPredictionRecord,
    InvalidHistoricalPredictionDatasetError,
    MixedHistoricalPredictionScopeError,
    NoEligiblePredictionSnapshotsSkip,
    SkippedPredictionRecord,
)
from tests.historical_prediction_fixtures import (
    make_prediction_result,
    make_request,
    make_scope,
    make_snapshot,
    sample_snapshots,
)


def _make_record_for_period(
    fund_id: str = "FUND_A",
    source_id: str = "SOURCE_1",
    pred_date: date = date(2026, 1, 10),
    target_date: date = date(2026, 1, 11),
    pred_time: datetime = datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
    eval_time: datetime = datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    lookback: int = 5,
    confidence_level: float = 0.95,
    model_version: str = "v1.0",
) -> HistoricalPredictionRecord:
    snaps = sample_snapshots(fund_id=fund_id, source_id=source_id, count=15)
    pred_res = make_prediction_result(
        snapshots=snaps,
        fund_id=fund_id,
        source_id=source_id,
        prediction_date=MarketDate(pred_date.year, pred_date.month, pred_date.day),
        pricing_as_of_date=MarketDate(pred_date.year, pred_date.month, pred_date.day),
        target_date=MarketDate(target_date.year, target_date.month, target_date.day),
        prediction_timestamp=pred_time,
        lookback=lookback,
        confidence_level=confidence_level,
        model_version=model_version,
    )
    req = make_request(
        prediction_date=pred_res.prediction_date,
        pricing_as_of_date=pred_res.pricing_as_of_date,
        target_date=pred_res.target_date,
        prediction_timestamp=pred_time,
        evaluation_timestamp=eval_time,
    )
    last_obs = pred_res.last_observation_date
    last_obs_d = date.fromisoformat(str(last_obs))
    ret_period = ReturnPeriod(last_obs, pred_res.target_date)
    period_ret = PeriodDecimalReturn(ret_period, 0.002)

    start_snap = make_snapshot(
        fund_id=fund_id,
        source_id=source_id,
        market_date=last_obs_d,
        price=100.0,
        available_at=pred_time,
    )
    end_snap = make_snapshot(
        fund_id=fund_id,
        source_id=source_id,
        market_date=target_date,
        price=100.2,
        available_at=eval_time,
    )

    return HistoricalPredictionRecord(
        request=req,
        prediction_result=pred_res,
        realized_period_return=period_ret,
        realized_start_snapshot=start_snap,
        realized_end_snapshot=end_snap,
    )


def test_empty_dataset_validity_and_immutability() -> None:
    scope = make_scope()
    dataset = HistoricalPredictionDataset(scope=scope, outcomes=())
    assert dataset.scope == scope
    assert dataset.outcomes == ()

    with pytest.raises(FrozenInstanceError):
        dataset.scope = None  # type: ignore[misc]


def test_all_skipped_dataset_does_not_invent_model_metadata() -> None:
    scope = make_scope()
    req1 = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )
    skip1 = SkippedPredictionRecord(request=req1, reason=NoEligiblePredictionSnapshotsSkip())
    skip2 = SkippedPredictionRecord(request=req2, reason=NoEligiblePredictionSnapshotsSkip())

    dataset = HistoricalPredictionDataset(scope=scope, outcomes=(skip1, skip2))
    assert len(dataset.outcomes) == 2
    assert dataset.outcomes[0] is skip1
    assert dataset.outcomes[1] is skip2


def test_mixed_successful_and_skipped_outcomes_preserves_order_and_identity() -> None:
    scope = make_scope(fund_id="FUND_A", source_id="SOURCE_1")

    rec1 = _make_record_for_period(
        fund_id="FUND_A",
        source_id="SOURCE_1",
        pred_date=date(2026, 1, 10),
        target_date=date(2026, 1, 11),
        pred_time=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        eval_time=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 11),
        pricing_as_of_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )
    skip2 = SkippedPredictionRecord(request=req2, reason=NoEligiblePredictionSnapshotsSkip())

    dataset = HistoricalPredictionDataset(scope=scope, outcomes=(rec1, skip2))
    assert len(dataset.outcomes) == 2
    assert dataset.outcomes[0] is rec1
    assert dataset.outcomes[1] is skip2


@pytest.mark.parametrize(
    ("scope", "outcomes"),
    [
        ("invalid_scope", ()),
        (make_scope(), [make_request()]),  # outcomes not a tuple
        (make_scope(), ("invalid_outcome",)),
    ],
)
def test_rejects_invalid_scope_outcome_and_container_types(scope: object, outcomes: object) -> None:
    with pytest.raises(InvalidHistoricalPredictionDatasetError):
        HistoricalPredictionDataset(scope=scope, outcomes=outcomes)  # type: ignore[arg-type]


def test_skipped_requests_participate_in_chronology_validation() -> None:
    scope = make_scope()
    rec1 = _make_record_for_period(
        pred_date=date(2026, 1, 10),
        target_date=date(2026, 1, 11),
        pred_time=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        eval_time=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )
    # req2 has decreasing prediction_date (Jan 9 < Jan 10)
    req2 = make_request(
        prediction_date=MarketDate(2026, 1, 9),
        pricing_as_of_date=MarketDate(2026, 1, 9),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )
    skip2 = SkippedPredictionRecord(request=req2, reason=NoEligiblePredictionSnapshotsSkip())

    with pytest.raises(DecreasingHistoricalPredictionScheduleError):
        HistoricalPredictionDataset(scope=scope, outcomes=(rec1, skip2))


@pytest.mark.parametrize(
    ("scope_kwargs", "record_kwargs"),
    [
        ({"fund_id": "FUND_A"}, {"fund_id": "FUND_B"}),
        ({"source_id": "SOURCE_1"}, {"source_id": "SOURCE_2"}),
        ({"lookback": 5}, {"lookback": 6}),
        ({"model_version": "v1.0"}, {"model_version": "v2.0"}),
        ({"confidence_level": 0.95}, {"confidence_level": 0.90}),
    ],
)
def test_rejects_record_scope_mismatch(
    scope_kwargs: dict[str, object], record_kwargs: dict[str, object]
) -> None:
    base_scope_args = {
        "fund_id": "FUND_A",
        "source_id": "SOURCE_1",
        "lookback": 5,
        "confidence_level": 0.95,
        "model_version": "v1.0",
    }
    base_record_args = {
        "fund_id": "FUND_A",
        "source_id": "SOURCE_1",
        "pred_date": date(2026, 1, 10),
        "target_date": date(2026, 1, 11),
        "pred_time": datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        "eval_time": datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        "lookback": 5,
        "confidence_level": 0.95,
        "model_version": "v1.0",
    }
    base_scope_args.update(scope_kwargs)
    base_record_args.update(record_kwargs)

    scope = HistoricalPredictionEvaluationScope(**base_scope_args)  # type: ignore[arg-type]
    rec = _make_record_for_period(**base_record_args)  # type: ignore[arg-type]

    with pytest.raises(MixedHistoricalPredictionScopeError):
        HistoricalPredictionDataset(scope=scope, outcomes=(rec,))


def test_rejects_model_metadata_homogeneity_mismatch_across_successful_records() -> None:
    scope = make_scope(fund_id="FUND_A", source_id="SOURCE_1", model_version="v1.0")

    rec1 = _make_record_for_period(
        fund_id="FUND_A",
        source_id="SOURCE_1",
        pred_date=date(2026, 1, 10),
        target_date=date(2026, 1, 11),
        pred_time=datetime(2026, 1, 10, 18, 0, tzinfo=UTC),
        eval_time=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        model_version="v1.0",
    )

    # Build second record with different feature schema version by modifying prediction.model
    snaps2 = sample_snapshots(fund_id="FUND_A", source_id="SOURCE_1", count=15)
    res2 = make_prediction_result(
        snapshots=snaps2,
        fund_id="FUND_A",
        source_id="SOURCE_1",
        prediction_date=MarketDate(2026, 1, 11),
        pricing_as_of_date=MarketDate(2026, 1, 11),
        target_date=MarketDate(2026, 1, 12),
        prediction_timestamp=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
        model_version="v1.0",
    )

    mismatched_model = ModelDescriptor(
        res2.prediction.model.name,
        res2.prediction.model.version,
        "v2_features",
    )
    mismatched_pred = create_return_prediction(
        res2.prediction.expected_return,
        res2.prediction.lower_bound,
        res2.prediction.upper_bound,
        res2.prediction.confidence_level,
        mismatched_model,
    )
    object.__setattr__(res2, "prediction", mismatched_pred)

    req2 = make_request(
        prediction_date=res2.prediction_date,
        pricing_as_of_date=res2.pricing_as_of_date,
        target_date=res2.target_date,
        prediction_timestamp=res2.prediction_timestamp,
        evaluation_timestamp=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )
    last_obs2 = res2.last_observation_date
    last_obs2_d = date.fromisoformat(str(last_obs2))
    ret_period2 = ReturnPeriod(last_obs2, res2.target_date)
    period_ret2 = PeriodDecimalReturn(ret_period2, 0.002)

    start_snap2 = make_snapshot(
        fund_id="FUND_A",
        source_id="SOURCE_1",
        market_date=last_obs2_d,
        price=100.0,
        available_at=datetime(2026, 1, 11, 18, 0, tzinfo=UTC),
    )
    end_snap2 = make_snapshot(
        fund_id="FUND_A",
        source_id="SOURCE_1",
        market_date=date(2026, 1, 12),
        price=100.2,
        available_at=datetime(2026, 1, 12, 18, 0, tzinfo=UTC),
    )

    rec2 = HistoricalPredictionRecord(
        request=req2,
        prediction_result=res2,
        realized_period_return=period_ret2,
        realized_start_snapshot=start_snap2,
        realized_end_snapshot=end_snap2,
    )

    with pytest.raises(MixedHistoricalPredictionScopeError) as exc_info:
        HistoricalPredictionDataset(scope=scope, outcomes=(rec1, rec2))

    assert exc_info.value.field_name == "feature_schema_version"
