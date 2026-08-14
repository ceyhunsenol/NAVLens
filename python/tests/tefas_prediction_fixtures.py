from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from navlens import MarketDate
from navlens.prediction.model_suite import (
    PredictionModelSuiteOptions,
    PredictionModelSuiteResult,
    predict_tefas_model_suite,
)
from navlens.sources.tefas import TefasAcquisitionResult, TefasPriceRecord


def make_tefas_prediction_acquisition(
    fund_code: str = "AAL",
    count: int = 14,
) -> TefasAcquisitionResult:
    start = date(2026, 7, 20)
    records = tuple(
        TefasPriceRecord(start + timedelta(days=index), fund_code, 1.0 + index * 0.01)
        for index in range(count)
    )
    return TefasAcquisitionResult(records, Path("raw.json"), False)


def make_prediction_model_suite(
    fund_code: str = "AAL",
    *,
    options: PredictionModelSuiteOptions | None = None,
) -> PredictionModelSuiteResult:
    return predict_tefas_model_suite(
        make_tefas_prediction_acquisition(fund_code),
        acquired_at=datetime(2026, 8, 12, 12, tzinfo=UTC),
        prediction_date=MarketDate(2026, 8, 2),
        target_date=MarketDate(2026, 8, 3),
        options=options,
    )
