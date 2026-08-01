from pathlib import Path

import pytest
from navlens import (
    CsvFxRateSourceError,
    CurrencyCode,
    CurrencyPair,
    FxRate,
    FxRateKind,
    MarketDate,
    read_fx_rates_csv,
)

HEADER = "source_id,base_currency,quote_currency,market_date,rate,kind,available_at,ingested_at\n"
ROW_1 = "tcmb,USD,TRY,2026-01-15,35.25,non_cash_buying,2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
ROW_2 = "tcmb,USD,TRY,2026-01-16,35.50,non_cash_buying,2026-01-16T18:00:00Z,2026-01-16T18:05:00Z\n"


def test_reads_valid_single_row_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "single_fx_rate.csv"
    csv_file.write_text(HEADER + ROW_1, encoding="utf-8")

    snapshots = read_fx_rates_csv(csv_file)

    assert len(snapshots) == 1
    assert snapshots[0].observation.rate == FxRate(35.25)


def test_reads_valid_multi_row_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "fx_rates.csv"
    csv_file.write_text(HEADER + ROW_1 + ROW_2, encoding="utf-8")

    snapshots = read_fx_rates_csv(csv_file)

    assert len(snapshots) == 2
    snap1, snap2 = snapshots

    assert snap1.source_id == "tcmb"
    assert snap1.observation.pair.base_currency == CurrencyCode("USD")
    assert snap1.observation.pair.quote_currency == CurrencyCode("TRY")
    assert snap1.observation.market_date == MarketDate(2026, 1, 15)
    assert snap1.observation.rate == FxRate(35.25)
    assert snap1.observation.kind == FxRateKind("non_cash_buying")

    assert snap2.observation.market_date == MarketDate(2026, 1, 16)
    assert snap2.observation.rate == FxRate(35.50)


def test_all_four_fx_rate_kind_values(tmp_path: Path) -> None:
    rows = (
        "tcmb,USD,TRY,2026-01-15,35.25,non_cash_buying,2026-01-15T18:00:00Z,"
        "2026-01-15T18:05:00Z\n"
        "tcmb,USD,TRY,2026-01-15,35.30,non_cash_selling,2026-01-15T18:00:00Z,"
        "2026-01-15T18:05:00Z\n"
        "tcmb,USD,TRY,2026-01-15,35.20,cash_buying,2026-01-15T18:00:00Z,"
        "2026-01-15T18:05:00Z\n"
        "tcmb,USD,TRY,2026-01-15,35.35,cash_selling,2026-01-15T18:00:00Z,"
        "2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "kinds.csv"
    csv_file.write_text(HEADER + rows, encoding="utf-8")

    snapshots = read_fx_rates_csv(csv_file)

    assert len(snapshots) == 4
    kinds = [s.observation.kind for s in snapshots]
    assert kinds == [
        FxRateKind("non_cash_buying"),
        FxRateKind("non_cash_selling"),
        FxRateKind("cash_buying"),
        FxRateKind("cash_selling"),
    ]


def test_supports_utf8_bom(tmp_path: Path) -> None:
    csv_file = tmp_path / "bom_rates.csv"
    csv_file.write_text(HEADER + ROW_1, encoding="utf-8-sig")

    snapshots = read_fx_rates_csv(csv_file)

    assert len(snapshots) == 1
    assert snapshots[0].observation.pair == CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))


def test_preserves_row_order(tmp_path: Path) -> None:
    csv_file = tmp_path / "ordered_rates.csv"
    csv_file.write_text(HEADER + ROW_2 + ROW_1, encoding="utf-8")

    snapshots = read_fx_rates_csv(csv_file)

    assert len(snapshots) == 2
    assert snapshots[0].observation.market_date == MarketDate(2026, 1, 16)
    assert snapshots[1].observation.market_date == MarketDate(2026, 1, 15)


def test_preserves_both_correction_rows(tmp_path: Path) -> None:
    orig_row = (
        "tcmb,USD,TRY,2026-01-15,35.00,non_cash_buying,2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    corr_row = (
        "tcmb,USD,TRY,2026-01-15,35.25,non_cash_buying,2026-01-16T09:00:00Z,2026-01-16T09:05:00Z\n"
    )
    csv_file = tmp_path / "corrections.csv"
    csv_file.write_text(HEADER + orig_row + corr_row, encoding="utf-8")

    snapshots = read_fx_rates_csv(csv_file)

    assert len(snapshots) == 2
    assert snapshots[0].observation.rate == FxRate(35.00)
    assert snapshots[1].observation.rate == FxRate(35.25)


def test_preserves_rows_from_different_providers(tmp_path: Path) -> None:
    row_tcmb = (
        "tcmb,USD,TRY,2026-01-15,35.25,non_cash_buying,2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    row_ecb = (
        "ecb,USD,TRY,2026-01-15,35.28,non_cash_buying,2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "providers.csv"
    csv_file.write_text(HEADER + row_tcmb + row_ecb, encoding="utf-8")

    snapshots = read_fx_rates_csv(csv_file)

    assert len(snapshots) == 2
    assert snapshots[0].source_id == "tcmb"
    assert snapshots[1].source_id == "ecb"


def test_directional_pair_preservation(tmp_path: Path) -> None:
    usd_try_row = (
        "tcmb,USD,TRY,2026-01-15,35.25,non_cash_buying,2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    try_usd_row = (
        "tcmb,TRY,USD,2026-01-15,0.028,non_cash_buying,2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "directional.csv"
    csv_file.write_text(HEADER + usd_try_row + try_usd_row, encoding="utf-8")

    snapshots = read_fx_rates_csv(csv_file)

    assert len(snapshots) == 2
    assert snapshots[0].observation.pair == CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    assert snapshots[1].observation.pair == CurrencyPair(CurrencyCode("TRY"), CurrencyCode("USD"))


def test_rejects_unreadable_file_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "non_existent.csv"

    with pytest.raises(CsvFxRateSourceError, match="cannot read CSV file") as exc_info:
        read_fx_rates_csv(missing_path)

    assert str(missing_path) in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_rejects_empty_file(tmp_path: Path) -> None:
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("", encoding="utf-8")

    with pytest.raises(CsvFxRateSourceError, match="header is missing"):
        read_fx_rates_csv(csv_file)


def test_rejects_header_only_file(tmp_path: Path) -> None:
    csv_file = tmp_path / "no_data.csv"
    csv_file.write_text(HEADER, encoding="utf-8")

    with pytest.raises(CsvFxRateSourceError, match="contains no FX rate rows"):
        read_fx_rates_csv(csv_file)


def test_rejects_missing_required_columns(tmp_path: Path) -> None:
    csv_file = tmp_path / "missing_cols.csv"
    csv_file.write_text("source_id,base_currency\ntcmb,USD\n", encoding="utf-8")

    with pytest.raises(CsvFxRateSourceError, match="missing required columns"):
        read_fx_rates_csv(csv_file)


@pytest.mark.parametrize(
    "col",
    [
        "source_id",
        "base_currency",
        "quote_currency",
        "market_date",
        "rate",
        "kind",
        "available_at",
        "ingested_at",
    ],
)
def test_rejects_blank_required_values(tmp_path: Path, col: str) -> None:
    data = {
        "source_id": "tcmb",
        "base_currency": "USD",
        "quote_currency": "TRY",
        "market_date": "2026-01-15",
        "rate": "35.25",
        "kind": "non_cash_buying",
        "available_at": "2026-01-15T18:00:00Z",
        "ingested_at": "2026-01-15T18:05:00Z",
    }
    data[col] = "   "
    row = ",".join(data.values()) + "\n"
    csv_file = tmp_path / f"blank_{col}.csv"
    csv_file.write_text(HEADER + row, encoding="utf-8")

    with pytest.raises(CsvFxRateSourceError, match=f"{col} is required") as exc_info:
        read_fx_rates_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)


def test_rejects_invalid_market_date(tmp_path: Path) -> None:
    bad_row = (
        "tcmb,USD,TRY,2026-02-31,35.25,non_cash_buying,2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "bad_date.csv"
    csv_file.write_text(HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvFxRateSourceError, match="invalid ISO date") as exc_info:
        read_fx_rates_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


@pytest.mark.parametrize(
    ("base_currency", "quote_currency"),
    [("usd", "TRY"), ("USD", "try")],
)
def test_rejects_invalid_base_and_quote_currencies(
    tmp_path: Path, base_currency: str, quote_currency: str
) -> None:
    bad_row = (
        f"tcmb,{base_currency},{quote_currency},2026-01-15,35.25,non_cash_buying,"
        "2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "bad_currency.csv"
    csv_file.write_text(HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvFxRateSourceError, match="invalid currency") as exc_info:
        read_fx_rates_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_rejects_identical_base_and_quote_currency(tmp_path: Path) -> None:
    identical_row = (
        "tcmb,USD,USD,2026-01-15,1.00,non_cash_buying,2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "identical.csv"
    csv_file.write_text(HEADER + identical_row, encoding="utf-8")

    with pytest.raises(CsvFxRateSourceError, match="identical") as exc_info:
        read_fx_rates_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


@pytest.mark.parametrize("bad_rate", ["abc", "0", "-35.25", "nan", "inf", "-inf"])
def test_rejects_invalid_zero_negative_nan_infinite_rate(tmp_path: Path, bad_rate: str) -> None:
    bad_row = (
        f"tcmb,USD,TRY,2026-01-15,{bad_rate},non_cash_buying,"
        "2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "bad_rate.csv"
    csv_file.write_text(HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvFxRateSourceError) as exc_info:
        read_fx_rates_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_rejects_unknown_rate_kind(tmp_path: Path) -> None:
    bad_row = (
        "tcmb,USD,TRY,2026-01-15,35.25,unknown_kind,2026-01-15T18:00:00Z,2026-01-15T18:05:00Z\n"
    )
    csv_file = tmp_path / "bad_kind.csv"
    csv_file.write_text(HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvFxRateSourceError, match="invalid kind") as exc_info:
        read_fx_rates_csv(csv_file)

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
def test_rejects_naive_and_non_utc_timestamps(
    tmp_path: Path, available_at: str, error_match: str
) -> None:
    bad_row = f"tcmb,USD,TRY,2026-01-15,35.25,non_cash_buying,{available_at},2026-01-15T18:05:00Z\n"
    csv_file = tmp_path / "bad_ts.csv"
    csv_file.write_text(HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvFxRateSourceError, match=error_match) as exc_info:
        read_fx_rates_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


@pytest.mark.parametrize(
    ("ingested_at", "error_match"),
    [
        ("2026-01-15T18:05:00", "timezone"),
        ("2026-01-15T21:05:00+03:00", "UTC"),
    ],
)
def test_rejects_naive_and_non_utc_ingestion_timestamps(
    tmp_path: Path, ingested_at: str, error_match: str
) -> None:
    bad_row = f"tcmb,USD,TRY,2026-01-15,35.25,non_cash_buying,2026-01-15T18:00:00Z,{ingested_at}\n"
    csv_file = tmp_path / "bad_ingested_ts.csv"
    csv_file.write_text(HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvFxRateSourceError, match=error_match) as exc_info:
        read_fx_rates_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_rejects_ingestion_before_availability(tmp_path: Path) -> None:
    bad_row = (
        "tcmb,USD,TRY,2026-01-15,35.25,non_cash_buying,2026-01-15T18:00:00Z,2026-01-15T17:59:00Z\n"
    )
    csv_file = tmp_path / "ingest_before_avail.csv"
    csv_file.write_text(HEADER + bad_row, encoding="utf-8")

    with pytest.raises(CsvFxRateSourceError, match="ingestion time cannot precede") as exc_info:
        read_fx_rates_csv(csv_file)

    assert f"{csv_file}:2:" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None
