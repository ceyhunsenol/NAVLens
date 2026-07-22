from pathlib import Path

import pytest
from navlens import (
    CsvSecurityPriceSourceError,
    CurrencyCode,
    MarketDate,
    PriceAdjustment,
    read_security_prices_csv,
)

VALID_CSV_HEADER = (
    "source_id,instrument_id,market_date,price,currency,adjustment,available_at,ingested_at\n"
)
ROW_1 = (
    "src1,US67066G1040,2026-01-15,150.25,USD,unadjusted,2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
)
ROW_2 = (
    "src1,US67066G1040,2026-01-16,152.00,USD,unadjusted,2026-01-16T18:00:00Z,2026-01-16T18:05:00Z\n"
)


def test_reads_valid_single_and_multi_row_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "prices.csv"
    csv_file.write_text(VALID_CSV_HEADER + ROW_1 + ROW_2, encoding="utf-8")

    snapshots = read_security_prices_csv(csv_file)

    assert len(snapshots) == 2
    snap1, snap2 = snapshots

    assert snap1.source_id == "src1"
    assert snap1.observation.instrument_id == "US67066G1040"
    assert snap1.observation.market_date == MarketDate(2026, 1, 15)
    assert snap1.observation.price.value == pytest.approx(150.25)
    assert snap1.observation.currency == CurrencyCode("USD")
    assert snap1.observation.adjustment == PriceAdjustment("unadjusted")

    assert snap2.observation.market_date == MarketDate(2026, 1, 16)
    assert snap2.observation.price.value == pytest.approx(152.00)


def test_preserves_row_order(tmp_path: Path) -> None:
    csv_file = tmp_path / "ordered_prices.csv"
    csv_file.write_text(VALID_CSV_HEADER + ROW_2 + ROW_1, encoding="utf-8")

    snapshots = read_security_prices_csv(csv_file)

    assert len(snapshots) == 2
    assert snapshots[0].observation.market_date == MarketDate(2026, 1, 16)
    assert snapshots[1].observation.market_date == MarketDate(2026, 1, 15)


def test_supports_utf8_bom(tmp_path: Path) -> None:
    csv_file = tmp_path / "bom_prices.csv"
    csv_file.write_text(VALID_CSV_HEADER + ROW_1, encoding="utf-8-sig")

    snapshots = read_security_prices_csv(csv_file)

    assert len(snapshots) == 1
    assert snapshots[0].observation.instrument_id == "US67066G1040"


def test_preserves_both_correction_rows(tmp_path: Path) -> None:
    orig_row = (
        "src1,US67066G1040,2026-01-15,150.00,USD,unadjusted,"
        "2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    corr_row = (
        "src1,US67066G1040,2026-01-15,150.25,USD,unadjusted,"
        "2026-01-16T09:00:00Z,2026-01-16T09:05:00Z\n"
    )
    csv_file = tmp_path / "corrections.csv"
    csv_file.write_text(VALID_CSV_HEADER + orig_row + corr_row, encoding="utf-8")

    snapshots = read_security_prices_csv(csv_file)

    assert len(snapshots) == 2
    assert snapshots[0].observation.price.value == pytest.approx(150.00)
    assert snapshots[1].observation.price.value == pytest.approx(150.25)


def test_rejects_unreadable_file_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "non_existent.csv"

    with pytest.raises(CsvSecurityPriceSourceError, match="cannot read CSV file") as exc_info:
        read_security_prices_csv(missing_path)

    assert str(missing_path) in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_rejects_empty_file(tmp_path: Path) -> None:
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("", encoding="utf-8")

    with pytest.raises(CsvSecurityPriceSourceError, match="header is missing"):
        read_security_prices_csv(csv_file)


def test_rejects_header_only_empty_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "no_data.csv"
    csv_file.write_text(VALID_CSV_HEADER, encoding="utf-8")

    with pytest.raises(CsvSecurityPriceSourceError, match="contains no security price rows"):
        read_security_prices_csv(csv_file)


def test_rejects_missing_required_columns(tmp_path: Path) -> None:
    csv_file = tmp_path / "missing_cols.csv"
    csv_file.write_text("source_id,instrument_id\nsrc1,US67066G1040\n", encoding="utf-8")

    with pytest.raises(CsvSecurityPriceSourceError, match="missing required columns"):
        read_security_prices_csv(csv_file)


def test_rejects_blank_required_values(tmp_path: Path) -> None:
    bad_row = "src1,,2026-01-15,150.25,USD,unadjusted,2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    csv_file = tmp_path / "blank_value.csv"
    csv_file.write_text(VALID_CSV_HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvSecurityPriceSourceError, match="instrument_id is required") as exc_info:
        read_security_prices_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)


def test_rejects_invalid_market_date(tmp_path: Path) -> None:
    bad_row = (
        "src1,US67066G1040,2026-02-31,150.25,USD,unadjusted,"
        "2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "bad_date.csv"
    csv_file.write_text(VALID_CSV_HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvSecurityPriceSourceError, match="invalid ISO date") as exc_info:
        read_security_prices_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_rejects_invalid_price(tmp_path: Path) -> None:
    bad_row = (
        "src1,US67066G1040,2026-01-15,abc,USD,unadjusted,"
        "2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "bad_price.csv"
    csv_file.write_text(VALID_CSV_HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvSecurityPriceSourceError, match="invalid price") as exc_info:
        read_security_prices_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_rejects_invalid_instrument_id(tmp_path: Path) -> None:
    bad_row = (
        "src1,INVALID ID,2026-01-15,150.25,USD,unadjusted,"
        "2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "bad_inst.csv"
    csv_file.write_text(VALID_CSV_HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvSecurityPriceSourceError, match="whitespace") as exc_info:
        read_security_prices_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_rejects_invalid_currency(tmp_path: Path) -> None:
    bad_row = (
        "src1,US67066G1040,2026-01-15,150.25,usd,unadjusted,"
        "2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "bad_curr.csv"
    csv_file.write_text(VALID_CSV_HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvSecurityPriceSourceError, match="invalid currency") as exc_info:
        read_security_prices_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_rejects_invalid_adjustment(tmp_path: Path) -> None:
    bad_row = (
        "src1,US67066G1040,2026-01-15,150.25,USD,invalid_adj,"
        "2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "bad_adj.csv"
    csv_file.write_text(VALID_CSV_HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvSecurityPriceSourceError, match="invalid adjustment") as exc_info:
        read_security_prices_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


@pytest.mark.parametrize(
    ("available_at", "error_match"),
    [
        ("not-a-timestamp", "invalid available_at timestamp"),
        ("2026-01-15T18:00:00", "timezone"),
        ("2026-01-15T18:00:00+03:00", "UTC"),
    ],
)
def test_rejects_invalid_naive_or_non_utc_timestamp(
    tmp_path: Path, available_at: str, error_match: str
) -> None:
    bad_row = (
        f"src1,US67066G1040,2026-01-15,150.25,USD,unadjusted,{available_at},2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "naive_ts.csv"
    csv_file.write_text(VALID_CSV_HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvSecurityPriceSourceError, match=error_match) as exc_info:
        read_security_prices_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_rejects_ingestion_before_availability(tmp_path: Path) -> None:
    bad_row = (
        "src1,US67066G1040,2026-01-15,150.25,USD,unadjusted,"
        "2026-01-15T18:00:00Z,2026-01-15T17:59:00Z\n"
    )
    csv_file = tmp_path / "ingest_before_avail.csv"
    csv_file.write_text(VALID_CSV_HEADER + bad_row, encoding="utf-8")

    with pytest.raises(
        CsvSecurityPriceSourceError, match="ingestion time cannot precede"
    ) as exc_info:
        read_security_prices_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None
