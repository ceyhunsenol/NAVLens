"""Tests for historical reconciliation CLI composition root and behavior."""

from pathlib import Path
from unittest.mock import patch

import pytest
from navlens.reconciliation.historical import (
    format_historical_reconciliation_evaluation,
    serialize_historical_reconciliation_evaluation,
)
from navlens.reconciliation.historical_cli import main
from navlens.reconciliation.historical_cli_args import (
    parse_historical_reconciliation_cli_arguments,
)
from navlens.reconciliation.historical_csv import (
    evaluate_historical_reconciliation_from_csv,
)


def _write_cli_test_files(tmp_path: Path) -> list[str]:
    schedule_file = tmp_path / "schedule.csv"
    schedule_file.write_text(
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "2026-01-01,2026-01-02,2026-01-02,2026-01-02T10:00:00Z\n"
        "2026-01-02,2026-01-03,2026-01-03,2026-01-03T10:00:00Z\n",
        encoding="utf-8",
    )

    holdings_file = tmp_path / "holdings.csv"
    holdings_file.write_text(
        "fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight\n"
        "TEST_FUND,2026-01-01,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_h,INST_A,equity,1.0\n"
        "TEST_FUND,2026-01-02,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z,src_h,INST_A,equity,1.0\n",
        encoding="utf-8",
    )

    prices_file = tmp_path / "prices.csv"
    prices_file.write_text(
        "source_id,instrument_id,market_date,price,currency,adjustment,available_at,ingested_at\n"
        "src_p,INST_A,2026-01-01,100.0,TRY,unadjusted,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z\n"
        "src_p,INST_A,2026-01-02,105.0,TRY,unadjusted,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z\n"
        "src_p,INST_A,2026-01-03,110.0,TRY,unadjusted,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z\n",
        encoding="utf-8",
    )

    fund_prices_file = tmp_path / "fund_prices.csv"
    fund_prices_file.write_text(
        "fund_id,market_date,available_at,ingested_at,source_id,unit_price\n"
        "TEST_FUND,2026-01-01,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_f,10.0\n"
        "TEST_FUND,2026-01-02,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_f,10.5\n"
        "TEST_FUND,2026-01-03,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z,src_f,11.0\n",
        encoding="utf-8",
    )

    return [
        "--schedule-csv",
        str(schedule_file),
        "--holdings-csv",
        str(holdings_file),
        "--security-prices-csv",
        str(prices_file),
        "--fund-unit-prices-csv",
        str(fund_prices_file),
        "--fund-id",
        "TEST_FUND",
        "--holdings-source-id",
        "src_h",
        "--security-price-source-id",
        "src_p",
        "--fund-price-source-id",
        "src_f",
        "--fund-base-currency",
        "TRY",
        "--price-adjustment",
        "unadjusted",
        "--minimum-observations",
        "2",
        "--max-staleness-calendar-days",
        "5",
    ]


def test_main_default_output_format_is_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _write_cli_test_files(tmp_path)

    args = parse_historical_reconciliation_cli_arguments(argv)
    assert args.output_format == "text"

    exit_code = main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    expected_text = format_historical_reconciliation_evaluation(
        evaluate_historical_reconciliation_from_csv(args)
    )
    assert captured.out == expected_text + "\n"
    assert captured.err == ""


def test_main_explicit_text_format_selected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _write_cli_test_files(tmp_path) + ["--output-format", "text"]

    args = parse_historical_reconciliation_cli_arguments(argv)
    expected_eval = evaluate_historical_reconciliation_from_csv(args)
    expected_text = format_historical_reconciliation_evaluation(expected_eval)

    exit_code = main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    assert captured.out == expected_text + "\n"
    assert captured.err == ""


def test_main_returns_0_for_successful_evaluation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _write_cli_test_files(tmp_path)

    exit_code = main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "Historical Reconciliation Evaluation" in captured.out
    assert captured.err == ""


def test_main_returns_2_for_partially_skipped_evaluation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _write_cli_test_files(tmp_path)
    # Remove fund price snapshot for 2026-01-03 to force a skip outcome for period 2
    fund_prices_file = Path(argv[7])
    fund_prices_file.write_text(
        "fund_id,market_date,available_at,ingested_at,source_id,unit_price\n"
        "TEST_FUND,2026-01-01,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_f,10.0\n"
        "TEST_FUND,2026-01-02,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_f,10.5\n",
        encoding="utf-8",
    )

    exit_code = main(argv)
    assert exit_code == 2

    captured = capsys.readouterr()
    assert "WARNING: Skipped periods exist (1 of 2 periods skipped)." in captured.out


def test_main_returns_2_for_all_skipped_evaluation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _write_cli_test_files(tmp_path)
    # Write fund prices for non-matching date to force all periods to skip
    fund_prices_file = Path(argv[7])
    fund_prices_file.write_text(
        "fund_id,market_date,available_at,ingested_at,source_id,unit_price\n"
        "TEST_FUND,2026-01-10,2026-01-10T08:00:00Z,2026-01-10T08:00:00Z,src_f,10.0\n",
        encoding="utf-8",
    )

    exit_code = main(argv)
    assert exit_code == 2

    captured = capsys.readouterr()
    assert "Evaluated Period Count: 0" in captured.out
    assert "Skipped Period Count: 2" in captured.out
    assert "WARNING: Skipped periods exist (2 of 2 periods skipped)." in captured.out


def test_main_outputs_exact_json_bytes_via_capsysbinary(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    argv = _write_cli_test_files(tmp_path) + ["--output-format", "json"]

    args = parse_historical_reconciliation_cli_arguments(argv)
    expected_eval = evaluate_historical_reconciliation_from_csv(args)
    expected_bytes = serialize_historical_reconciliation_evaluation(expected_eval)

    exit_code = main(argv)
    assert exit_code == 0

    captured = capsysbinary.readouterr()
    assert captured.out == expected_bytes
    assert captured.err == b""


def test_main_invalid_minimum_observations_returns_1_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _write_cli_test_files(tmp_path)
    argv[argv.index("--minimum-observations") + 1] = "1"

    exit_code = main(argv)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: minimum_observations must be at least 2")


def test_main_negative_max_staleness_returns_1_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _write_cli_test_files(tmp_path)
    argv[argv.index("--max-staleness-calendar-days") + 1] = "-1"

    exit_code = main(argv)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: max_staleness_calendar_days must be non-negative")


def test_main_blank_source_identifier_returns_1_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _write_cli_test_files(tmp_path)
    argv[argv.index("--holdings-source-id") + 1] = "   "

    exit_code = main(argv)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: holdings_source_id must be a non-empty string")


def test_main_outputs_schedule_error_with_exact_path_and_row_number(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _write_cli_test_files(tmp_path)
    schedule_file = Path(argv[argv.index("--schedule-csv") + 1])
    schedule_file.write_text(
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "20260101,2026-01-02,2026-01-02,2026-01-02T10:00:00Z\n",
        encoding="utf-8",
    )

    exit_code = main(argv)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"error: cannot parse schedule CSV {schedule_file} at row 2:" in captured.err


def test_main_creates_no_files_on_disk(tmp_path: Path) -> None:
    argv = _write_cli_test_files(tmp_path)

    initial_files = set(tmp_path.rglob("*"))
    exit_code = main(argv)
    assert exit_code == 0

    final_files = set(tmp_path.rglob("*"))
    assert final_files == initial_files


def test_main_does_not_catch_unexpected_programmer_errors(tmp_path: Path) -> None:
    argv = _write_cli_test_files(tmp_path)

    with patch(
        "navlens.reconciliation.historical_cli.evaluate_historical_reconciliation_from_csv",
        side_effect=RuntimeError("unexpected programmer bug"),
    ):
        with pytest.raises(RuntimeError, match="unexpected programmer bug"):
            main(argv)


def test_argparse_invalid_choice_exits_with_2_before_main(tmp_path: Path) -> None:
    argv = _write_cli_test_files(tmp_path) + ["--output-format", "xml"]

    with pytest.raises(SystemExit) as exc_info:
        main(argv)

    assert exc_info.value.code == 2
