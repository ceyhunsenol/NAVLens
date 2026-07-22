from pathlib import Path

import pytest
from navlens.alignment.cli import main

HOLDINGS_CSV_HEADER = (
    "fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight\n"
)
PRICES_CSV_HEADER = (
    "source_id,instrument_id,market_date,price,currency,adjustment,available_at,ingested_at\n"
)
PRICE_ROW = (
    "bloomberg,INST1,2026-01-30,10.0,TRY,total_return_adjusted,"
    "2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n"
)


def test_cli_end_to_end_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holdings_file = tmp_path / "holdings.csv"
    h_row1 = "AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST1,equity,0.4\n"
    h_row2 = "AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST2,equity,0.6\n"
    holdings_file.write_text(HOLDINGS_CSV_HEADER + h_row1 + h_row2, encoding="utf-8")

    prices_file = tmp_path / "prices.csv"
    p_row1 = (
        "bloomberg,INST1,2026-01-30,10.0,TRY,total_return_adjusted,"
        "2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n"
    )
    p_row2 = (
        "bloomberg,INST1,2026-01-31,11.0,TRY,total_return_adjusted,"
        "2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n"
    )
    prices_file.write_text(PRICES_CSV_HEADER + p_row1 + p_row2, encoding="utf-8")

    argv = [
        "--holdings-csv",
        str(holdings_file),
        "--security-prices-csv",
        str(prices_file),
        "--fund-id",
        "AAL",
        "--holdings-source-id",
        "kap_src",
        "--security-price-source-id",
        "bloomberg",
        "--prediction-timestamp",
        "2026-02-01T12:00:00Z",
        "--pricing-as-of-date",
        "2026-01-31",
        "--fund-base-currency",
        "TRY",
        "--price-adjustment",
        "total_return_adjusted",
        "--minimum-observations",
        "2",
        "--max-staleness-calendar-days",
        "5",
    ]

    exit_code = main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    out = captured.out

    assert "Point-in-Time Alignment Report" in out
    assert "Fund ID: AAL" in out
    assert "Prediction Timestamp: 2026-02-01T12:00:00+00:00" in out
    assert "Effective Date: 2026-01-31" in out
    assert "Source ID: kap_src" in out
    assert "Selected Price Snapshots Count: 2" in out
    assert "Declared Weight: 1.000000" in out
    assert "Covered Weight: 0.400000" in out
    assert "Uncovered Listed Weight: 0.600000" in out
    assert "Total Uncovered Weight: 0.600000" in out
    assert "Coverage Ratio: 0.400000" in out
    assert "- INST1" in out
    assert "- INST2 (weight: 0.600000, reason: missing_price_series)" in out


def test_cli_missing_holdings_snapshot_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holdings_file = tmp_path / "holdings.csv"
    h_row = (
        "OTHER_FUND,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST1,equity,0.4\n"
    )
    holdings_file.write_text(HOLDINGS_CSV_HEADER + h_row, encoding="utf-8")

    prices_file = tmp_path / "prices.csv"
    prices_file.write_text(PRICES_CSV_HEADER + PRICE_ROW, encoding="utf-8")

    argv = [
        "--holdings-csv",
        str(holdings_file),
        "--security-prices-csv",
        str(prices_file),
        "--fund-id",
        "MISSING_FUND",
        "--holdings-source-id",
        "kap_src",
        "--security-price-source-id",
        "bloomberg",
        "--prediction-timestamp",
        "2026-02-01T12:00:00Z",
        "--pricing-as-of-date",
        "2026-01-31",
        "--fund-base-currency",
        "TRY",
        "--price-adjustment",
        "total_return_adjusted",
        "--minimum-observations",
        "2",
        "--max-staleness-calendar-days",
        "5",
    ]

    exit_code = main(argv)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "error: no eligible holdings snapshot found for fund_id='MISSING_FUND'" in captured.err


def test_cli_invalid_naive_timestamp_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holdings_file = tmp_path / "holdings.csv"
    h_row = "AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST1,equity,0.4\n"
    holdings_file.write_text(HOLDINGS_CSV_HEADER + h_row, encoding="utf-8")

    prices_file = tmp_path / "prices.csv"
    prices_file.write_text(PRICES_CSV_HEADER + PRICE_ROW, encoding="utf-8")

    argv = [
        "--holdings-csv",
        str(holdings_file),
        "--security-prices-csv",
        str(prices_file),
        "--fund-id",
        "AAL",
        "--holdings-source-id",
        "kap_src",
        "--security-price-source-id",
        "bloomberg",
        "--prediction-timestamp",
        "2026-02-01T12:00:00",  # Naive timestamp
        "--pricing-as-of-date",
        "2026-01-31",
        "--fund-base-currency",
        "TRY",
        "--price-adjustment",
        "total_return_adjusted",
        "--minimum-observations",
        "2",
        "--max-staleness-calendar-days",
        "5",
    ]

    exit_code = main(argv)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "error: prediction_timestamp must include a timezone" in captured.err


def test_cli_csv_parse_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holdings_file = tmp_path / "bad_holdings.csv"
    holdings_file.write_text("invalid,csv,header\n", encoding="utf-8")
    prices_file = tmp_path / "prices.csv"
    prices_file.write_text(PRICES_CSV_HEADER + PRICE_ROW, encoding="utf-8")

    argv = [
        "--holdings-csv",
        str(holdings_file),
        "--security-prices-csv",
        str(prices_file),
        "--fund-id",
        "AAL",
        "--holdings-source-id",
        "kap_src",
        "--security-price-source-id",
        "bloomberg",
        "--prediction-timestamp",
        "2026-02-01T12:00:00Z",
        "--pricing-as-of-date",
        "2026-01-31",
        "--fund-base-currency",
        "TRY",
        "--price-adjustment",
        "total_return_adjusted",
        "--minimum-observations",
        "2",
        "--max-staleness-calendar-days",
        "5",
    ]

    exit_code = main(argv)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "error:" in captured.err


def test_cli_argparse_missing_arg_exits_2() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2
