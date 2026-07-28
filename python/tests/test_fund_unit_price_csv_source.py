"""Tests for parsing fund unit-price CSV sources."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from navlens._native import MarketDate, PriceObservation
from navlens.datasets.fund_unit_price_snapshots import FundUnitPriceSnapshot
from navlens.sources.fund_unit_prices_csv import (
    CsvFundUnitPriceSourceError,
    read_fund_unit_prices_csv,
)


def create_csv(path: Path, content: str, encoding: str = "utf-8") -> Path:
    path.write_text(content.lstrip(), encoding=encoding)
    return path


def test_reads_valid_multi_row_csv(tmp_path: Path) -> None:
    path = create_csv(
        tmp_path / "prices.csv",
        """
fund_id,market_date,unit_price,available_at,ingested_at,source_id
F1,2023-01-01,10.5,2023-01-02T12:00:00+00:00,2023-01-02T12:00:00+00:00,S1
F1,2023-01-02,10.6,2023-01-03T12:00:00Z,2023-01-03T12:00:00+00:00,S1
""",
    )
    snapshots = read_fund_unit_prices_csv(path)
    assert len(snapshots) == 2
    s0 = snapshots[0]
    assert s0.fund_id == "F1"
    assert s0.source_id == "S1"
    assert isinstance(s0.observation, PriceObservation)
    assert s0.observation.date == MarketDate(2023, 1, 1)
    assert s0.observation.unit_price.value == 10.5
    assert s0.available_at == datetime(2023, 1, 2, 12, tzinfo=UTC)
    assert s0.ingested_at == datetime(2023, 1, 2, 12, tzinfo=UTC)
    assert isinstance(s0, FundUnitPriceSnapshot)


def test_supports_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "bom.csv"
    content = (
        "fund_id,market_date,unit_price,available_at,ingested_at,source_id\n"
        "F1,2023-01-01,10.5,2023-01-02T12:00:00+00:00,2023-01-02T12:00:00+00:00,S1"
    )
    path.write_text(content, encoding="utf-8-sig")
    snapshots = read_fund_unit_prices_csv(path)
    assert len(snapshots) == 1


def test_rejects_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("")
    with pytest.raises(CsvFundUnitPriceSourceError) as exc:
        read_fund_unit_prices_csv(path)
    assert "header is missing" in str(exc.value)


def test_rejects_missing_required_column(tmp_path: Path) -> None:
    path = create_csv(
        tmp_path / "missing.csv",
        """
fund_id,market_date,unit_price
F1,2023-01-01,10.5
""",
    )
    with pytest.raises(CsvFundUnitPriceSourceError) as exc:
        read_fund_unit_prices_csv(path)
    assert "missing required columns" in str(exc.value)
    assert "available_at" in str(exc.value)


def test_rejects_blank_required_cell(tmp_path: Path) -> None:
    path = create_csv(
        tmp_path / "blank.csv",
        """
fund_id,market_date,unit_price,available_at,ingested_at,source_id
,2023-01-01,10.5,2023-01-02T12:00:00+00:00,2023-01-02T12:00:00+00:00,S1
""",
    )
    with pytest.raises(CsvFundUnitPriceSourceError) as exc:
        read_fund_unit_prices_csv(path)
    assert "2: fund_id is required" in str(exc.value)


def test_rejects_invalid_market_date(tmp_path: Path) -> None:
    path = create_csv(
        tmp_path / "bad_date.csv",
        """
fund_id,market_date,unit_price,available_at,ingested_at,source_id
F1,not-a-date,10.5,2023-01-02T12:00:00+00:00,2023-01-02T12:00:00+00:00,S1
""",
    )
    with pytest.raises(CsvFundUnitPriceSourceError) as exc:
        read_fund_unit_prices_csv(path)
    assert "2: invalid ISO date" in str(exc.value)
    assert exc.value.__cause__ is not None


@pytest.mark.parametrize("unit_price", ["not-a-price", "0", "-10.5", "nan", "inf", "-inf"])
def test_rejects_invalid_unit_price(tmp_path: Path, unit_price: str) -> None:
    path = create_csv(
        tmp_path / "bad_price.csv",
        f"""
fund_id,market_date,unit_price,available_at,ingested_at,source_id
F1,2023-01-01,{unit_price},2023-01-02T12:00:00+00:00,2023-01-02T12:00:00+00:00,S1
""",
    )
    with pytest.raises(CsvFundUnitPriceSourceError) as exc:
        read_fund_unit_prices_csv(path)
    assert "2:" in str(exc.value)
    assert exc.value.__cause__ is not None


def test_rejects_naive_timestamp(tmp_path: Path) -> None:
    path = create_csv(
        tmp_path / "naive.csv",
        """
fund_id,market_date,unit_price,available_at,ingested_at,source_id
F1,2023-01-01,10.5,2023-01-02T12:00:00,2023-01-02T12:00:00,S1
""",
    )
    with pytest.raises(CsvFundUnitPriceSourceError) as exc:
        read_fund_unit_prices_csv(path)
    assert "must include a timezone" in str(exc.value)
    assert "2:" in str(exc.value)
    assert exc.value.__cause__ is not None


def test_rejects_non_utc_timestamp(tmp_path: Path) -> None:
    path = create_csv(
        tmp_path / "non_utc.csv",
        """
fund_id,market_date,unit_price,available_at,ingested_at,source_id
F1,2023-01-01,10.5,2023-01-02T12:00:00+02:00,2023-01-02T12:00:00+02:00,S1
""",
    )
    with pytest.raises(CsvFundUnitPriceSourceError) as exc:
        read_fund_unit_prices_csv(path)
    assert "must be in UTC" in str(exc.value)
    assert "2:" in str(exc.value)
    assert exc.value.__cause__ is not None


def test_rejects_ingested_before_available(tmp_path: Path) -> None:
    path = create_csv(
        tmp_path / "timing.csv",
        """
fund_id,market_date,unit_price,available_at,ingested_at,source_id
F1,2023-01-01,10.5,2023-01-02T12:00:00+00:00,2023-01-01T12:00:00+00:00,S1
""",
    )
    with pytest.raises(CsvFundUnitPriceSourceError) as exc:
        read_fund_unit_prices_csv(path)
    assert "ingestion time cannot precede" in str(exc.value)
    assert exc.value.__cause__ is not None


def test_preserves_duplicate_rows_and_order(tmp_path: Path) -> None:
    path = create_csv(
        tmp_path / "dup.csv",
        """
fund_id,market_date,unit_price,available_at,ingested_at,source_id
F1,2023-01-01,10.5,2023-01-02T12:00:00+00:00,2023-01-02T12:00:00+00:00,S1
F1,2023-01-01,10.6,2023-01-02T14:00:00+00:00,2023-01-02T14:00:00+00:00,S1
F1,2023-01-01,10.5,2023-01-02T12:00:00+00:00,2023-01-02T12:00:00+00:00,S1
""",
    )
    snapshots = read_fund_unit_prices_csv(path)
    assert len(snapshots) == 3
    assert snapshots[0].observation.unit_price.value == 10.5
    assert snapshots[1].observation.unit_price.value == 10.6
    assert snapshots[2].observation.unit_price.value == 10.5


def test_includes_path_and_row_in_error(tmp_path: Path) -> None:
    path = create_csv(
        tmp_path / "err.csv",
        """
fund_id,market_date,unit_price,available_at,ingested_at,source_id
F1,2023-01-01,10.5,2023-01-02T12:00:00+00:00,2023-01-02T12:00:00+00:00,S1
F1,2023-01-01,not-a-price,2023-01-02T12:00:00+00:00,2023-01-02T12:00:00+00:00,S1
""",
    )
    with pytest.raises(CsvFundUnitPriceSourceError) as exc:
        read_fund_unit_prices_csv(path)
    assert str(path) in str(exc.value)
    assert "3: invalid price" in str(exc.value)
