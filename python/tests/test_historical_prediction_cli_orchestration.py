"""Tests for historical prediction CSV orchestration."""

from pathlib import Path

from navlens.prediction.historical import (
    HistoricalPredictionRunResult,
    build_historical_prediction_dataset,
    evaluate_historical_prediction_dataset,
    read_historical_prediction_requests_csv,
    serialize_historical_prediction_run_result,
)
from navlens.prediction.historical_cli_args import (
    HistoricalPredictionCliArguments,
    parse_historical_prediction_cli_arguments,
)
from navlens.prediction.historical_csv import evaluate_historical_prediction_from_csv
from navlens.sources import read_fund_unit_prices_csv
from tests.historical_prediction_cli_fixtures import (
    write_historical_prediction_cli_files,
)


def test_csv_orchestration_matches_direct_canonical_pipeline(tmp_path: Path) -> None:
    arguments = parse_historical_prediction_cli_arguments(
        write_historical_prediction_cli_files(tmp_path)
    )

    actual = evaluate_historical_prediction_from_csv(arguments)
    requests = read_historical_prediction_requests_csv(arguments.schedule_csv)
    snapshots = read_fund_unit_prices_csv(arguments.fund_unit_prices_csv)
    dataset = build_historical_prediction_dataset(arguments.scope, requests, snapshots)
    expected = HistoricalPredictionRunResult(
        dataset=dataset,
        evaluation=evaluate_historical_prediction_dataset(dataset),
    )

    assert serialize_historical_prediction_run_result(actual) == (
        serialize_historical_prediction_run_result(expected)
    )
    assert actual.evaluation.total_period_count == 2
    assert actual.evaluation.evaluated_period_count == 2


def test_future_target_snapshot_is_classified_without_leaking(tmp_path: Path) -> None:
    argv = write_historical_prediction_cli_files(tmp_path)
    schedule_path = Path(argv[argv.index("--schedule-csv") + 1])
    schedule_path.write_text(
        "prediction_date,pricing_as_of_date,target_date,"
        "prediction_timestamp,evaluation_timestamp\n"
        "2026-01-10,2026-01-10,2026-01-11,"
        "2026-01-10T18:00:00Z,2026-01-11T12:00:00Z\n",
        encoding="utf-8",
    )

    result = evaluate_historical_prediction_from_csv(
        parse_historical_prediction_cli_arguments(argv)
    )

    assert result.evaluation.evaluated_period_count == 0
    assert result.evaluation.target_not_yet_available_count == 1
    assert result.evaluation.missing_target_observation_count == 0


def test_wrong_source_is_reported_as_typed_skip(tmp_path: Path) -> None:
    argv = write_historical_prediction_cli_files(tmp_path)
    argv[argv.index("--source-id") + 1] = "OTHER_SOURCE"

    result = evaluate_historical_prediction_from_csv(
        parse_historical_prediction_cli_arguments(argv)
    )

    assert result.evaluation.evaluated_period_count == 0
    assert result.evaluation.no_eligible_snapshots_count == 2


def test_orchestrator_rejects_wrong_argument_contract() -> None:
    try:
        evaluate_historical_prediction_from_csv("invalid")  # type: ignore[arg-type]
    except TypeError as error:
        assert "HistoricalPredictionCliArguments" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected TypeError")


def test_parsed_arguments_hold_validated_scope(tmp_path: Path) -> None:
    arguments = parse_historical_prediction_cli_arguments(
        write_historical_prediction_cli_files(tmp_path)
    )

    assert isinstance(arguments, HistoricalPredictionCliArguments)
    assert arguments.scope.fund_id == "FUND_A"
    assert arguments.scope.source_id == "SOURCE_1"
    assert arguments.scope.lookback == 5
    assert arguments.scope.confidence_level == 0.95
    assert arguments.scope.model_version == "v1.0"
