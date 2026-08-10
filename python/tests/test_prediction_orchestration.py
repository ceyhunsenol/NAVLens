"""Comprehensive tests for provider-neutral point-in-time prediction orchestration."""

from datetime import UTC, date, datetime, timedelta

import pytest
from navlens import MarketDate, PredictionRequest, PriceObservation, UnitPrice, UtcTimestamp
from navlens.datasets import FundUnitPriceSnapshot
from navlens.prediction import (
    InsufficientVisibleHistoryError,
    InvalidPredictionWindowError,
    NoEligibleSnapshotsError,
    PointInTimePredictionError,
    SingleReturnPredictionResult,
    predict_next_published_nav_return_from_snapshots,
)


def _make_snapshot(
    fund_id: str,
    source_id: str,
    market_date: date,
    price: float,
    available_at: datetime,
    ingested_at: datetime | None = None,
) -> FundUnitPriceSnapshot:
    if ingested_at is None:
        ingested_at = available_at
    obs = PriceObservation(
        MarketDate(market_date.year, market_date.month, market_date.day),
        UnitPrice(price),
    )
    return FundUnitPriceSnapshot(
        fund_id=fund_id,
        observation=obs,
        available_at=available_at,
        ingested_at=ingested_at,
        source_id=source_id,
    )


def _sample_snapshots(
    fund_id: str = "AAL",
    source_id: str = "tefas",
    count: int = 15,
    base_date: date = date(2026, 7, 1),
    start_time: datetime = datetime(2026, 7, 1, 18, 0, tzinfo=UTC),
) -> list[FundUnitPriceSnapshot]:
    snapshots = []
    current_price = 100.0
    for i in range(count):
        m_date = base_date + timedelta(days=i)
        avail = start_time + timedelta(days=i)
        current_price *= 1.002
        snapshots.append(
            _make_snapshot(
                fund_id=fund_id,
                source_id=source_id,
                market_date=m_date,
                price=current_price,
                available_at=avail,
            )
        )
    return snapshots


def test_successful_end_to_end_prediction() -> None:
    """Test successful point-in-time prediction orchestration."""
    snapshots = _sample_snapshots(count=15)
    pred_timestamp = datetime(2026, 7, 20, 0, 0, tzinfo=UTC)

    pred_date = MarketDate(2026, 7, 15)
    pricing_date = MarketDate(2026, 7, 15)
    target_date = MarketDate(2026, 7, 16)

    result = predict_next_published_nav_return_from_snapshots(
        snapshots,
        fund_id="AAL",
        source_id="tefas",
        prediction_timestamp=pred_timestamp,
        prediction_date=pred_date,
        pricing_as_of_date=pricing_date,
        target_date=target_date,
        lookback=5,
        confidence_level=0.90,
    )

    assert isinstance(result, SingleReturnPredictionResult)
    assert result.fund_id == "AAL"
    assert result.source_id == "tefas"
    assert result.prediction_date == pred_date
    assert result.target_date == target_date
    assert result.pricing_as_of_date == pricing_date
    assert result.lookback == 5
    assert result.selected_snapshot_count == 15
    assert result.canonical_return_count == 14
    assert result.training_return_count == 14
    assert result.training_target_row_count == 9

    # Verify exact PyO3 property access
    assert result.request.fund_id == "AAL"
    assert result.request.prediction_date == pred_date
    assert result.request.target_date == target_date
    assert result.request.generated_at.unix_seconds == int(pred_timestamp.timestamp())

    expected_data_as_of = max(s.available_at for s in result.selected_snapshots)
    assert result.request.data_as_of.unix_seconds == int(expected_data_as_of.timestamp())

    assert result.prediction.model.name == "linear-regression-baseline"
    assert result.prediction.model.version == "v1"
    assert result.prediction.model.feature_set_version == "lagged-returns-v1"
    assert isinstance(result.expected_return_decimal, float)
    assert result.prediction_interval_lower_decimal <= result.expected_return_decimal
    assert result.expected_return_decimal <= result.prediction_interval_upper_decimal


def test_future_publication_exclusion_and_cutoff_inclusion() -> None:
    """Test cutoff boundary inclusion and future snapshot exclusion."""
    start_time = datetime(2026, 7, 1, 18, 0, tzinfo=UTC)
    base_snaps = _sample_snapshots(count=10, start_time=start_time)

    # Add future snapshot (published after cutoff)
    future_snap = _make_snapshot(
        fund_id="AAL",
        source_id="tefas",
        market_date=date(2026, 7, 11),
        price=120.0,
        available_at=datetime(2026, 7, 20, 18, 0, tzinfo=UTC),
    )
    all_snaps = base_snaps + [future_snap]

    cutoff_ts = datetime(2026, 7, 10, 18, 0, tzinfo=UTC)  # Exact match for 10th snapshot
    pred_date = MarketDate(2026, 7, 10)
    pricing_date = MarketDate(2026, 7, 10)
    target_date = MarketDate(2026, 7, 11)

    result = predict_next_published_nav_return_from_snapshots(
        all_snaps,
        fund_id="AAL",
        source_id="tefas",
        prediction_timestamp=cutoff_ts,
        prediction_date=pred_date,
        pricing_as_of_date=pricing_date,
        target_date=target_date,
        lookback=3,
    )

    # 10th snapshot available_at == cutoff_ts, included
    assert result.selected_snapshot_count == 10
    assert result.last_observation_date == MarketDate(2026, 7, 10)
    assert result.actual_data_as_of == cutoff_ts
    assert future_snap not in result.selected_snapshots


def test_correction_precedence_retained_provenance() -> None:
    """Test deterministic correction selection precedence and stored snapshot provenance."""
    t0 = datetime(2026, 7, 1, 18, 0, tzinfo=UTC)
    snaps = _sample_snapshots(count=10, start_time=t0)

    # Add correction for date 2026-07-05 published later but before cutoff
    correction_snap = _make_snapshot(
        fund_id="AAL",
        source_id="tefas",
        market_date=date(2026, 7, 5),
        price=105.5,
        available_at=datetime(2026, 7, 6, 12, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 7, 6, 12, 5, tzinfo=UTC),
    )
    all_snaps = snaps + [correction_snap]

    cutoff_ts = datetime(2026, 7, 10, 18, 0, tzinfo=UTC)
    pred_date = MarketDate(2026, 7, 10)

    result = predict_next_published_nav_return_from_snapshots(
        all_snaps,
        fund_id="AAL",
        source_id="tefas",
        prediction_timestamp=cutoff_ts,
        prediction_date=pred_date,
        pricing_as_of_date=pred_date,
        target_date=MarketDate(2026, 7, 11),
        lookback=3,
    )

    # Date 2026-07-05 snapshot should be the correction_snap
    snap_on_5th = [
        s for s in result.selected_snapshots if s.observation.date == MarketDate(2026, 7, 5)
    ][0]
    assert snap_on_5th.observation.unit_price.value == 105.5
    assert snap_on_5th.ingested_at == datetime(2026, 7, 6, 12, 5, tzinfo=UTC)


def test_fund_and_source_isolation() -> None:
    """Test isolation of fund_id and source_id."""
    snaps = _sample_snapshots(count=10)
    # Add snapshot for another fund and another source
    other_fund = _make_snapshot(
        "XYZ", "tefas", date(2026, 7, 5), 10.0, datetime(2026, 7, 5, 18, 0, tzinfo=UTC)
    )
    other_source = _make_snapshot(
        "AAL", "reuters", date(2026, 7, 5), 10.0, datetime(2026, 7, 5, 18, 0, tzinfo=UTC)
    )
    all_snaps = snaps + [other_fund, other_source]

    result = predict_next_published_nav_return_from_snapshots(
        all_snaps,
        fund_id="AAL",
        source_id="tefas",
        prediction_timestamp=datetime(2026, 7, 10, 18, 0, tzinfo=UTC),
        prediction_date=MarketDate(2026, 7, 10),
        pricing_as_of_date=MarketDate(2026, 7, 10),
        target_date=MarketDate(2026, 7, 11),
        lookback=3,
    )
    assert result.selected_snapshot_count == 10
    for s in result.selected_snapshots:
        assert s.fund_id == "AAL"
        assert s.source_id == "tefas"


def test_insufficient_visible_history_raised_before_native_calculation() -> None:
    """Test InsufficientVisibleHistoryError is raised before native calculation."""
    # 5 snapshots -> 4 returns. Default lookback=5 requires 8 returns (9 snaps)
    snaps = _sample_snapshots(count=5)

    with pytest.raises(
        InsufficientVisibleHistoryError,
        match="selected snapshot count \\(5\\) is less than required minimum \\(9\\)",
    ):
        predict_next_published_nav_return_from_snapshots(
            snaps,
            fund_id="AAL",
            source_id="tefas",
            prediction_timestamp=datetime(2026, 7, 10, 18, 0, tzinfo=UTC),
            prediction_date=MarketDate(2026, 7, 5),
            pricing_as_of_date=MarketDate(2026, 7, 5),
            target_date=MarketDate(2026, 7, 6),
            lookback=5,
        )


def test_no_eligible_snapshots_error() -> None:
    """Test NoEligibleSnapshotsError raised when no snapshots match filters."""
    snaps = _sample_snapshots(count=10)

    with pytest.raises(NoEligibleSnapshotsError, match="no price snapshots found for fund 'WRONG'"):
        predict_next_published_nav_return_from_snapshots(
            snaps,
            fund_id="WRONG",
            source_id="tefas",
            prediction_timestamp=datetime(2026, 7, 10, 18, 0, tzinfo=UTC),
            prediction_date=MarketDate(2026, 7, 10),
            pricing_as_of_date=MarketDate(2026, 7, 10),
            target_date=MarketDate(2026, 7, 11),
        )


def test_decoupled_prediction_date_and_window_validations() -> None:
    """Test decoupled prediction date and invalid prediction window validations."""
    snaps = _sample_snapshots(count=10)

    # Decoupled prediction date (prediction_date later than last_observation_date)
    result = predict_next_published_nav_return_from_snapshots(
        snaps,
        fund_id="AAL",
        source_id="tefas",
        prediction_timestamp=datetime(2026, 7, 15, 0, 0, tzinfo=UTC),
        prediction_date=MarketDate(2026, 7, 12),  # Last observation is 2026-07-10
        pricing_as_of_date=MarketDate(2026, 7, 10),
        target_date=MarketDate(2026, 7, 13),
        lookback=3,
    )
    assert result.last_observation_date == MarketDate(2026, 7, 10)
    assert result.prediction_date == MarketDate(2026, 7, 12)

    # Invalid: prediction_date >= target_date
    with pytest.raises(
        InvalidPredictionWindowError, match="prediction_date .* must precede target_date"
    ):
        predict_next_published_nav_return_from_snapshots(
            snaps,
            fund_id="AAL",
            source_id="tefas",
            prediction_timestamp=datetime(2026, 7, 15, 0, 0, tzinfo=UTC),
            prediction_date=MarketDate(2026, 7, 12),
            pricing_as_of_date=MarketDate(2026, 7, 10),
            target_date=MarketDate(2026, 7, 12),
            lookback=3,
        )

    # Invalid: pricing_as_of_date > prediction_date
    with pytest.raises(
        InvalidPredictionWindowError,
        match="pricing_as_of_date .* cannot be later than prediction_date",
    ):
        predict_next_published_nav_return_from_snapshots(
            snaps,
            fund_id="AAL",
            source_id="tefas",
            prediction_timestamp=datetime(2026, 7, 15, 0, 0, tzinfo=UTC),
            prediction_date=MarketDate(2026, 7, 10),
            pricing_as_of_date=MarketDate(2026, 7, 12),
            target_date=MarketDate(2026, 7, 13),
            lookback=3,
        )


def test_microsecond_timestamp_rejection() -> None:
    """Test rejection of non-zero microsecond timestamps to preserve second precision provenance."""
    snaps = _sample_snapshots(count=10)
    bad_ts = datetime(2026, 7, 10, 18, 0, 0, 123456, tzinfo=UTC)

    with pytest.raises(
        PointInTimePredictionError,
        match="prediction_timestamp must not contain fractional seconds",
    ):
        predict_next_published_nav_return_from_snapshots(
            snaps,
            fund_id="AAL",
            source_id="tefas",
            prediction_timestamp=bad_ts,
            prediction_date=MarketDate(2026, 7, 10),
            pricing_as_of_date=MarketDate(2026, 7, 10),
            target_date=MarketDate(2026, 7, 11),
            lookback=3,
        )


def test_deterministic_replay_identical_inputs() -> None:
    """Test deterministic replay produces identical result outputs for identical inputs."""
    snaps = _sample_snapshots(count=15)
    params = dict(
        snapshots=snaps,
        fund_id="AAL",
        source_id="tefas",
        prediction_timestamp=datetime(2026, 7, 20, 0, 0, tzinfo=UTC),
        prediction_date=MarketDate(2026, 7, 15),
        pricing_as_of_date=MarketDate(2026, 7, 15),
        target_date=MarketDate(2026, 7, 16),
        lookback=5,
    )
    res1 = predict_next_published_nav_return_from_snapshots(**params)
    res2 = predict_next_published_nav_return_from_snapshots(**params)

    assert res1.expected_return_decimal == res2.expected_return_decimal
    assert res1.prediction_interval_lower_decimal == res2.prediction_interval_lower_decimal
    assert res1.prediction_interval_upper_decimal == res2.prediction_interval_upper_decimal
    assert res1.training_target_start_date == res2.training_target_start_date
    assert res1.training_target_end_date == res2.training_target_end_date


def test_training_target_start_date_mapping_and_counts() -> None:
    """Verify training_target_start_date mapping and canonical vs supervised row counts."""
    snaps = _sample_snapshots(count=15)
    lookback = 5
    result = predict_next_published_nav_return_from_snapshots(
        snaps,
        fund_id="AAL",
        source_id="tefas",
        prediction_timestamp=datetime(2026, 7, 20, 0, 0, tzinfo=UTC),
        prediction_date=MarketDate(2026, 7, 15),
        pricing_as_of_date=MarketDate(2026, 7, 15),
        target_date=MarketDate(2026, 7, 16),
        lookback=lookback,
    )

    # 15 snapshots -> 14 canonical returns
    assert result.selected_snapshot_count == 15
    assert result.canonical_return_count == 14
    assert result.training_return_count == 14
    # Supervised rows = canonical returns - lookback = 14 - 5 = 9
    assert result.training_target_row_count == 9

    # Verify training target start/end dates correspond to lookback + 1 and last snapshot
    expected_start = result.selected_snapshots[lookback + 1].observation.date
    expected_end = result.selected_snapshots[-1].observation.date
    assert result.training_target_start_date == expected_start
    assert result.training_target_end_date == expected_end


def test_result_constructor_invariant_rejections() -> None:
    """Test SingleReturnPredictionResult constructor invariant rejections."""
    snaps = _sample_snapshots(count=15)
    valid_res = predict_next_published_nav_return_from_snapshots(
        snaps,
        fund_id="AAL",
        source_id="tefas",
        prediction_timestamp=datetime(2026, 7, 20, 0, 0, tzinfo=UTC),
        prediction_date=MarketDate(2026, 7, 15),
        pricing_as_of_date=MarketDate(2026, 7, 15),
        target_date=MarketDate(2026, 7, 16),
        lookback=5,
    )

    # 1. Non-increasing / duplicate snapshot market dates
    dup_snap = _make_snapshot(
        "AAL", "tefas", date(2026, 7, 1), 100.0, datetime(2026, 7, 1, 18, 0, tzinfo=UTC)
    )
    bad_snaps = (dup_snap, dup_snap)
    with pytest.raises(
        ValueError, match="selected_snapshots market dates must be strictly increasing"
    ):
        SingleReturnPredictionResult(
            request=valid_res.request,
            prediction=valid_res.prediction,
            source_id="tefas",
            prediction_timestamp=valid_res.prediction_timestamp,
            pricing_as_of_date=valid_res.pricing_as_of_date,
            selected_snapshots=bad_snaps,
            training_return_count=1,
            training_target_start_date=valid_res.training_target_start_date,
            training_target_end_date=valid_res.training_target_end_date,
            lookback=5,
            target_definition="next_published_nav_return_decimal",
        )

    # 2. Snapshot later than pricing_as_of_date
    with pytest.raises(ValueError, match="last observation date cannot exceed pricing_as_of_date"):
        SingleReturnPredictionResult(
            request=valid_res.request,
            prediction=valid_res.prediction,
            source_id="tefas",
            prediction_timestamp=valid_res.prediction_timestamp,
            pricing_as_of_date=MarketDate(2026, 7, 1),  # earlier than last snapshot date 2026-07-15
            selected_snapshots=valid_res.selected_snapshots,
            training_return_count=valid_res.training_return_count,
            training_target_start_date=valid_res.training_target_start_date,
            training_target_end_date=valid_res.training_target_end_date,
            lookback=valid_res.lookback,
            target_definition="next_published_nav_return_decimal",
        )

    # 3. Microsecond timestamp rejection in result constructor
    bad_ts = datetime(2026, 7, 20, 0, 0, 0, 100, tzinfo=UTC)
    with pytest.raises(
        ValueError, match="prediction_timestamp must not contain fractional seconds"
    ):
        SingleReturnPredictionResult(
            request=valid_res.request,
            prediction=valid_res.prediction,
            source_id="tefas",
            prediction_timestamp=bad_ts,
            pricing_as_of_date=valid_res.pricing_as_of_date,
            selected_snapshots=valid_res.selected_snapshots,
            training_return_count=valid_res.training_return_count,
            training_target_start_date=valid_res.training_target_start_date,
            training_target_end_date=valid_res.training_target_end_date,
            lookback=valid_res.lookback,
            target_definition="next_published_nav_return_decimal",
        )

    # 4. Whitespace source_id rejection
    with pytest.raises(ValueError, match="source_id must be a non-empty string"):
        SingleReturnPredictionResult(
            request=valid_res.request,
            prediction=valid_res.prediction,
            source_id="   ",
            prediction_timestamp=valid_res.prediction_timestamp,
            pricing_as_of_date=valid_res.pricing_as_of_date,
            selected_snapshots=valid_res.selected_snapshots,
            training_return_count=valid_res.training_return_count,
            training_target_start_date=valid_res.training_target_start_date,
            training_target_end_date=valid_res.training_target_end_date,
            lookback=valid_res.lookback,
            target_definition="next_published_nav_return_decimal",
        )

    # 5. Training target row count < 3 rejection
    short_res = predict_next_published_nav_return_from_snapshots(
        snaps[:8],  # 8 snapshots -> 7 canonical returns
        fund_id="AAL",
        source_id="tefas",
        prediction_timestamp=datetime(2026, 7, 20, 0, 0, tzinfo=UTC),
        prediction_date=MarketDate(2026, 7, 15),
        pricing_as_of_date=MarketDate(2026, 7, 15),
        target_date=MarketDate(2026, 7, 16),
        lookback=4,  # 7 - 4 = 3 rows >= 3 valid
    )
    with pytest.raises(ValueError, match="training_target_row_count .* must be at least 3"):
        SingleReturnPredictionResult(
            request=short_res.request,
            prediction=short_res.prediction,
            source_id="tefas",
            prediction_timestamp=short_res.prediction_timestamp,
            pricing_as_of_date=short_res.pricing_as_of_date,
            selected_snapshots=short_res.selected_snapshots,
            training_return_count=7,
            training_target_start_date=short_res.selected_snapshots[6].observation.date,
            training_target_end_date=short_res.selected_snapshots[-1].observation.date,
            lookback=5,  # 7 - 5 = 2 < 3
            target_definition="next_published_nav_return_decimal",
        )

    # 6. Selected snapshot available_at with fractional seconds rejection
    bad_snap_ts = datetime(2026, 7, 15, 18, 0, 0, 123456, tzinfo=UTC)
    bad_snap = _make_snapshot("AAL", "tefas", date(2026, 7, 15), 100.0, bad_snap_ts)
    snaps_with_micro = valid_res.selected_snapshots[:-1] + (bad_snap,)
    bad_snap_request = PredictionRequest(
        valid_res.request.fund_id,
        valid_res.request.prediction_date,
        valid_res.request.target_date,
        valid_res.request.generated_at,
        UtcTimestamp(int(bad_snap_ts.timestamp())),
    )
    with pytest.raises(ValueError, match="actual_data_as_of must not contain fractional seconds"):
        SingleReturnPredictionResult(
            request=bad_snap_request,
            prediction=valid_res.prediction,
            source_id="tefas",
            prediction_timestamp=valid_res.prediction_timestamp,
            pricing_as_of_date=valid_res.pricing_as_of_date,
            selected_snapshots=snaps_with_micro,
            training_return_count=valid_res.training_return_count,
            training_target_start_date=valid_res.training_target_start_date,
            training_target_end_date=valid_res.training_target_end_date,
            lookback=valid_res.lookback,
            target_definition="next_published_nav_return_decimal",
        )
