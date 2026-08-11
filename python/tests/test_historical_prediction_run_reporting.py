"""Tests for auditable historical prediction run results and reporting."""

import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
from navlens.prediction.historical import (
    HistoricalPredictionRunResult,
    InvalidHistoricalPredictionRunResultError,
    format_historical_prediction_run_result,
    serialize_historical_prediction_run_result,
)
from navlens.prediction.historical_cli_args import (
    parse_historical_prediction_cli_arguments,
)
from navlens.prediction.historical_csv import evaluate_historical_prediction_from_csv
from tests.historical_prediction_cli_fixtures import (
    write_historical_prediction_cli_files,
)


def _run_result(tmp_path: Path) -> HistoricalPredictionRunResult:
    arguments = parse_historical_prediction_cli_arguments(
        write_historical_prediction_cli_files(tmp_path)
    )
    return evaluate_historical_prediction_from_csv(arguments)


def test_run_result_retains_dataset_and_evaluation_identity(tmp_path: Path) -> None:
    result = _run_result(tmp_path)

    assert result.evaluation.total_period_count == len(result.dataset.outcomes)
    assert result.evaluation.scope is result.dataset.scope
    with pytest.raises(FrozenInstanceError):
        result.dataset = result.dataset  # type: ignore[misc]


def test_run_result_rejects_inconsistent_counts(tmp_path: Path) -> None:
    result = _run_result(tmp_path)
    invalid = replace(
        result.evaluation,
        total_period_count=3,
        skipped_period_count=1,
        no_eligible_snapshots_count=1,
    )

    with pytest.raises(InvalidHistoricalPredictionRunResultError, match="total_period_count"):
        HistoricalPredictionRunResult(dataset=result.dataset, evaluation=invalid)


def test_text_report_contains_ordered_period_predictions(tmp_path: Path) -> None:
    result = _run_result(tmp_path)

    report = format_historical_prediction_run_result(result)

    first = report.index("2026-01-10 -> 2026-01-11")
    second = report.index("2026-01-11 -> 2026-01-12")
    assert first < second
    assert report.count("| evaluated | predicted=") == 2
    assert "| realized=" in report


def test_json_report_contains_prediction_and_realized_provenance(tmp_path: Path) -> None:
    result = _run_result(tmp_path)

    encoded = serialize_historical_prediction_run_result(result)
    payload = json.loads(encoded)

    assert encoded.endswith(b"\n") and not encoded.endswith(b"\n\n")
    assert payload["evaluation"]["counts"]["evaluated_period_count"] == 2
    assert [item["status"] for item in payload["outcomes"]] == ["evaluated", "evaluated"]
    first = payload["outcomes"][0]
    assert first["prediction"]["expected_return_decimal"] is not None
    assert first["realized"]["return_decimal"] is not None
    assert first["realized"]["start_snapshot"]["source_id"] == "SOURCE_1"


def test_skip_report_uses_stable_reason_code(tmp_path: Path) -> None:
    argv = write_historical_prediction_cli_files(tmp_path)
    schedule = Path(argv[argv.index("--schedule-csv") + 1])
    schedule.write_text(
        "prediction_date,pricing_as_of_date,target_date,"
        "prediction_timestamp,evaluation_timestamp\n"
        "2026-01-10,2026-01-10,2026-01-11,"
        "2026-01-10T18:00:00Z,2026-01-11T12:00:00Z\n",
        encoding="utf-8",
    )
    arguments = parse_historical_prediction_cli_arguments(argv)
    result = evaluate_historical_prediction_from_csv(arguments)

    text = format_historical_prediction_run_result(result)
    payload = json.loads(serialize_historical_prediction_run_result(result))

    reason = "target_observation_not_yet_available"
    assert f"| skipped | reason={reason}" in text
    assert payload["outcomes"][0]["reason"] == reason
    assert "prediction" not in payload["outcomes"][0]


@pytest.mark.parametrize("value", [None, object()])
def test_run_formatters_reject_wrong_type(value: object) -> None:
    with pytest.raises(TypeError, match="HistoricalPredictionRunResult"):
        format_historical_prediction_run_result(value)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="HistoricalPredictionRunResult"):
        serialize_historical_prediction_run_result(value)  # type: ignore[arg-type]
