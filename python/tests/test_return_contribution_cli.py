from pathlib import Path

import pytest
from navlens.alignment.return_contribution_cli import main

HOLDINGS_CSV_HEADER = (
    "fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight\n"
)
PRICES_CSV_HEADER = (
    "source_id,instrument_id,market_date,price,currency,adjustment,available_at,ingested_at\n"
)


def create_holdings_csv(path: Path, rows: list[str]) -> Path:
    path.write_text(HOLDINGS_CSV_HEADER + "".join(rows), encoding="utf-8")
    return path


def create_prices_csv(path: Path, rows: list[str]) -> Path:
    path.write_text(PRICES_CSV_HEADER + "".join(rows), encoding="utf-8")
    return path


def build_argv(
    holdings_csv: Path,
    prices_csv: Path,
    return_start: str = "2026-01-30",
    return_end: str = "2026-01-31",
) -> list[str]:
    return [
        "--holdings-csv",
        str(holdings_csv),
        "--security-prices-csv",
        str(prices_csv),
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
        "--return-start-date",
        return_start,
        "--return-end-date",
        return_end,
    ]


def test_cli_end_to_end_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holdings_file = create_holdings_csv(
        tmp_path / "holdings.csv",
        [
            "AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST1,equity,0.4\n",
            "AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST2,equity,0.6\n",
        ],
    )
    prices_file = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,INST1,2026-01-30,100.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST1,2026-01-31,110.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST2,2026-01-30,50.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST2,2026-01-31,55.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    argv = build_argv(holdings_file, prices_file)

    exit_code = main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    out = captured.out

    assert "Point-in-Time Alignment Report" in out
    assert "Return Contribution Report" in out
    assert "Target Period: 2026-01-30 to 2026-01-31" in out
    assert "Price Coverage: 1.000000" in out
    assert "Return Coverage: 1.000000" in out
    assert "Observed Contribution: 0.100000" in out
    assert "Has Full Coverage: True" in out


def test_cli_partial_coverage_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holdings_file = create_holdings_csv(
        tmp_path / "holdings.csv",
        [
            "AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,PRICE_GAP,equity,0.2\n",
            "AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,COVERED,equity,0.4\n",
            "AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,RETURN_GAP,equity,0.4\n",
        ],
    )
    prices_file = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,COVERED,2026-01-30,100.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,COVERED,2026-01-31,110.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,RETURN_GAP,2026-01-29,100.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,RETURN_GAP,2026-01-31,110.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    argv = build_argv(holdings_file, prices_file)

    exit_code = main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    out = captured.out

    comp_idx = out.index("Component Contributions:")
    comp_1_idx = out.index("  - COVERED", comp_idx)
    price_gap_idx = out.index("Price Gaps:", comp_1_idx)
    price_gap_1_idx = out.index("  - PRICE_GAP", price_gap_idx)
    return_gap_idx = out.index("Return Gaps:", price_gap_1_idx)
    return_gap_1_idx = out.index("  - RETURN_GAP", return_gap_idx)

    assert comp_idx < comp_1_idx < price_gap_idx
    assert price_gap_1_idx < return_gap_idx < return_gap_1_idx


def test_cli_negative_return_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holdings_file = create_holdings_csv(
        tmp_path / "holdings.csv",
        ["AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,NEGATIVE,equity,1.0\n"],
    )
    prices_file = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,NEGATIVE,2026-01-30,100.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,NEGATIVE,2026-01-31,50.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    argv = build_argv(holdings_file, prices_file)

    exit_code = main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "market return: -0.500000" in captured.out


def test_cli_invalid_return_period_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    holdings_file = create_holdings_csv(
        tmp_path / "holdings.csv",
        ["AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z,kap_src,INST1,equity,1.0\n"],
    )
    prices_file = create_prices_csv(
        tmp_path / "prices.csv",
        [
            "bloomberg,INST1,2026-01-30,100.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
            "bloomberg,INST1,2026-01-31,110.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:05:00Z\n",
        ],
    )
    argv = build_argv(
        holdings_file,
        prices_file,
        return_start="2026-01-31",
        return_end="2026-01-30",
    )

    exit_code = main(argv)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert captured.err.startswith("error: ")
    assert "return period start must precede end" in captured.err
    assert captured.out == ""


def test_cli_csv_parse_error_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holdings_file = tmp_path / "holdings.csv"
    holdings_file.write_text("invalid,csv\n", encoding="utf-8")
    prices_file = create_prices_csv(tmp_path / "prices.csv", [])
    argv = build_argv(holdings_file, prices_file)

    exit_code = main(argv)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "error: CSV is missing required columns in" in captured.err


def test_cli_argparse_missing_arg_exits_2() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2
