from pathlib import Path

import pytest
from navlens.sources.csv import CsvPriceSourceError, read_price_records


def test_reads_explicit_price_records(shared_price_csv_path: Path) -> None:
    records = read_price_records(shared_price_csv_path)

    assert len(records) == 6
    assert records[0].market_date.isoformat() == "2026-01-02"
    assert records[0].unit_price == 100.0


def test_rejects_missing_columns(tmp_path: Path) -> None:
    source = tmp_path / "missing-price.csv"
    source.write_text("date\n2026-01-02\n", encoding="utf-8")

    with pytest.raises(CsvPriceSourceError, match="unit_price"):
        read_price_records(source)


def test_reports_invalid_rows_with_source_context(tmp_path: Path) -> None:
    source = tmp_path / "invalid-date.csv"
    source.write_text("date,unit_price\nnot-a-date,100.0\n", encoding="utf-8")

    with pytest.raises(CsvPriceSourceError, match=r"invalid-date\.csv:2"):
        read_price_records(source)
