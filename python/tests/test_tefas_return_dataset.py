from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from navlens.datasets import (
    FundReturnDatasetError,
    build_tefas_fund_returns,
    load_fund_returns_csv,
)
from navlens.sources.tefas import TefasAcquisitionResult, TefasPriceRecord


def test_tefas_and_csv_share_canonical_return_pipeline(
    shared_price_csv_path: Path, tmp_path: Path
) -> None:
    acquisition = TefasAcquisitionResult(
        records=_price_records("ABC"),
        payload_path=tmp_path / "payload.json",
        from_cache=True,
    )

    tefas_dataset = build_tefas_fund_returns(acquisition)
    csv_dataset = load_fund_returns_csv("ABC", shared_price_csv_path)

    pd.testing.assert_series_equal(tefas_dataset.returns, csv_dataset.returns)
    assert tefas_dataset.fund_id == "ABC"
    assert tefas_dataset.source_path == acquisition.payload_path
    assert tefas_dataset.source_row_count == 6


def test_rejects_empty_tefas_dataset(tmp_path: Path) -> None:
    acquisition = TefasAcquisitionResult((), tmp_path / "payload.json", True)

    with pytest.raises(FundReturnDatasetError, match="at least one"):
        build_tefas_fund_returns(acquisition)


def test_rejects_mixed_fund_tefas_dataset(tmp_path: Path) -> None:
    records = list(_price_records("ABC"))
    records[-1] = TefasPriceRecord(records[-1].market_date, "XYZ", records[-1].unit_price)
    acquisition = TefasAcquisitionResult(tuple(records), tmp_path / "payload.json", False)

    with pytest.raises(FundReturnDatasetError, match="multiple funds"):
        build_tefas_fund_returns(acquisition)


def _price_records(fund_code: str) -> tuple[TefasPriceRecord, ...]:
    dates = [
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
        date(2026, 1, 7),
        date(2026, 1, 8),
        date(2026, 1, 9),
    ]
    prices = [100.0, 101.0, 100.495, 102.002425, 101.79842015, 102.8164043515]
    return tuple(
        TefasPriceRecord(market_date, fund_code, unit_price)
        for market_date, unit_price in zip(dates, prices, strict=True)
    )
