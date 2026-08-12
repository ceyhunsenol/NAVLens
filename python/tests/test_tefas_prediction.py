from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from navlens import MarketDate
from navlens.prediction import (
    FundUnitPriceFreshnessPolicy,
    NoEligibleSnapshotsError,
    PredictionModelOptions,
    StaleFundUnitPriceHistoryError,
    predict_next_published_nav_return_from_tefas_acquisition,
)
from navlens.sources.tefas import TefasAcquisitionResult, TefasPriceRecord


def _acquisition(fund_code: str = "AAL", count: int = 14) -> TefasAcquisitionResult:
    start = date(2026, 7, 20)
    records = tuple(
        TefasPriceRecord(start + timedelta(days=index), fund_code, 1.0 + index * 0.01)
        for index in range(count)
    )
    return TefasAcquisitionResult(records, Path("raw.json"), False)


def test_predicts_from_acquired_tefas_prices_through_canonical_pipeline() -> None:
    acquired_at = datetime(2026, 8, 12, 12, tzinfo=UTC)

    result = predict_next_published_nav_return_from_tefas_acquisition(
        _acquisition(),
        acquired_at=acquired_at,
        prediction_date=MarketDate(2026, 8, 2),
        target_date=MarketDate(2026, 8, 3),
    )

    assert result.fund_id == "AAL"
    assert result.source_id == "tefas"
    assert result.prediction_timestamp == acquired_at
    assert str(result.pricing_as_of_date) == "2026-08-02"
    assert result.selected_snapshot_count == 14
    assert result.model_name == "linear-regression-baseline"


def test_rejects_empty_acquisition() -> None:
    empty = TefasAcquisitionResult((), Path("raw.json"), False)

    with pytest.raises(NoEligibleSnapshotsError, match="no fund unit-price records"):
        predict_next_published_nav_return_from_tefas_acquisition(
            empty,
            acquired_at=datetime(2026, 8, 12, 12, tzinfo=UTC),
            prediction_date=MarketDate(2026, 8, 12),
            target_date=MarketDate(2026, 8, 13),
        )


def test_preserves_user_selected_model_configuration() -> None:
    result = predict_next_published_nav_return_from_tefas_acquisition(
        _acquisition(count=20),
        acquired_at=datetime(2026, 8, 12, 12, tzinfo=UTC),
        prediction_date=MarketDate(2026, 8, 8),
        target_date=MarketDate(2026, 8, 9),
        model=PredictionModelOptions(
            lookback=7,
            minimum_training_returns=12,
            confidence_level=0.95,
            model_version="baseline-v2",
        ),
        freshness=FundUnitPriceFreshnessPolicy(6),
    )

    assert result.lookback == 7
    assert result.confidence_level == 0.95
    assert result.model_version == "baseline-v2"


def test_rejects_stale_latest_tefas_price_by_default() -> None:
    with pytest.raises(StaleFundUnitPriceHistoryError, match="10 calendar days old"):
        predict_next_published_nav_return_from_tefas_acquisition(
            _acquisition(),
            acquired_at=datetime(2026, 8, 12, 12, tzinfo=UTC),
            prediction_date=MarketDate(2026, 8, 12),
            target_date=MarketDate(2026, 8, 13),
        )


def test_rejects_mixed_fund_acquisition() -> None:
    first = _acquisition().records
    mixed = TefasAcquisitionResult(
        first + (TefasPriceRecord(date(2026, 8, 3), "PHE", 2.0),),
        Path("raw.json"),
        False,
    )

    with pytest.raises(ValueError, match="exactly one fund"):
        predict_next_published_nav_return_from_tefas_acquisition(
            mixed,
            acquired_at=datetime(2026, 8, 12, 12, tzinfo=UTC),
            prediction_date=MarketDate(2026, 8, 12),
            target_date=MarketDate(2026, 8, 13),
        )
