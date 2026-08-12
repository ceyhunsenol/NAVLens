"""Executable contract for the repository historical prediction example."""

from pathlib import Path

import pytest
from navlens.prediction.historical_cli import main


def test_repository_example_runs_end_to_end(
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = Path(__file__).parents[2]
    example = root / "examples" / "historical_prediction"
    argv = [
        "--schedule-csv",
        str(example / "prediction_schedule.csv"),
        "--fund-unit-prices-csv",
        str(example / "fund_unit_prices.csv"),
        "--fund-id",
        "DEMO",
        "--source-id",
        "example",
        "--lookback",
        "5",
        "--confidence-level",
        "0.95",
        "--model-version",
        "v1.0",
    ]

    assert main(argv) == 0
    captured = capsys.readouterr()
    assert "Evaluated Period Count: 2" in captured.out
    assert captured.out.count("| evaluated | predicted=") == 2
    assert "Skipped Period Count: 0" in captured.out
    assert captured.err == ""
