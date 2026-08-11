"""Tests for historical prediction CLI process behavior and output."""

from pathlib import Path
from unittest.mock import patch

import pytest
from navlens.prediction.historical import (
    format_historical_prediction_run_result,
    serialize_historical_prediction_run_result,
)
from navlens.prediction.historical_cli import main
from navlens.prediction.historical_cli_args import (
    parse_historical_prediction_cli_arguments,
)
from navlens.prediction.historical_cli_output import write_historical_prediction_run_result
from navlens.prediction.historical_csv import evaluate_historical_prediction_from_csv
from tests.historical_prediction_cli_fixtures import (
    write_historical_prediction_cli_files,
)


def test_main_defaults_to_exact_text_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    argv = write_historical_prediction_cli_files(tmp_path)
    arguments = parse_historical_prediction_cli_arguments(argv)
    result = evaluate_historical_prediction_from_csv(arguments)

    assert arguments.output_format == "text"
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert captured.out == format_historical_prediction_run_result(result) + "\n"
    assert captured.err == ""


def test_main_writes_exact_json_bytes(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    argv = write_historical_prediction_cli_files(tmp_path) + ["--output-format", "json"]
    arguments = parse_historical_prediction_cli_arguments(argv)
    result = evaluate_historical_prediction_from_csv(arguments)

    assert main(argv) == 0
    captured = capsysbinary.readouterr()
    assert captured.out == serialize_historical_prediction_run_result(result)
    assert captured.err == b""


def test_main_returns_two_when_a_period_is_skipped(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    argv = write_historical_prediction_cli_files(tmp_path)
    schedule_path = Path(argv[argv.index("--schedule-csv") + 1])
    schedule_path.write_text(
        "prediction_date,pricing_as_of_date,target_date,"
        "prediction_timestamp,evaluation_timestamp\n"
        "2026-01-10,2026-01-10,2026-01-11,"
        "2026-01-10T18:00:00Z,2026-01-11T12:00:00Z\n",
        encoding="utf-8",
    )

    assert main(argv) == 2
    captured = capsys.readouterr()
    assert "Skipped Period Count: 1" in captured.out
    assert "WARNING: Skipped periods exist" in captured.out
    assert captured.err == ""


def test_main_maps_operational_errors_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    argv = write_historical_prediction_cli_files(tmp_path)
    schedule_path = Path(argv[argv.index("--schedule-csv") + 1])
    schedule_path.write_text("invalid_header\nvalue\n", encoding="utf-8")

    assert main(argv) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: historical prediction schedule")
    assert "Traceback" not in captured.err


def test_main_does_not_swallow_programmer_errors(tmp_path: Path) -> None:
    argv = write_historical_prediction_cli_files(tmp_path)

    with patch(
        "navlens.prediction.historical_cli.evaluate_historical_prediction_from_csv",
        side_effect=RuntimeError("unexpected programmer bug"),
    ):
        with pytest.raises(RuntimeError, match="unexpected programmer bug"):
            main(argv)


def test_argparse_rejects_unknown_output_format(tmp_path: Path) -> None:
    argv = write_historical_prediction_cli_files(tmp_path) + ["--output-format", "xml"]

    with pytest.raises(SystemExit) as error:
        main(argv)

    assert error.value.code == 2


def test_output_writer_rejects_unsupported_format(tmp_path: Path) -> None:
    arguments = parse_historical_prediction_cli_arguments(
        write_historical_prediction_cli_files(tmp_path)
    )
    result = evaluate_historical_prediction_from_csv(arguments)

    with pytest.raises(ValueError, match="unsupported output format"):
        write_historical_prediction_run_result(
            result,
            "xml",
            text_stream=None,  # type: ignore[arg-type]
            binary_stream=None,  # type: ignore[arg-type]
        )


def test_main_creates_no_output_files(tmp_path: Path) -> None:
    argv = write_historical_prediction_cli_files(tmp_path)
    before = set(tmp_path.rglob("*"))

    assert main(argv) == 0

    assert set(tmp_path.rglob("*")) == before
