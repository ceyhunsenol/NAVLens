import json
import subprocess
from pathlib import Path


def _command(executable: str) -> list[str]:
    repository_root = Path(__file__).resolve().parents[2]
    example_directory = repository_root / "examples" / "historical_prediction"
    return [
        executable,
        "--schedule-csv",
        str(example_directory / "prediction_schedule.csv"),
        "--fund-unit-prices-csv",
        str(example_directory / "fund_unit_prices.csv"),
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
        "--output-format",
        "json",
    ]


def _expected_summary() -> dict[str, object]:
    return {
        "schema_version": 1,
        "evaluation_schema_version": 1,
        "total_period_count": 2,
        "evaluated_period_count": 2,
        "skipped_period_count": 0,
        "sample_count": 2,
        "outcome_statuses": ["evaluated", "evaluated"],
    }


def verify_historical_prediction_example(executable: str) -> None:
    result = subprocess.run(_command(executable), capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise SystemExit(f"historical prediction example failed:\n{result.stderr}")

    payload = json.loads(result.stdout)
    evaluation = payload.get("evaluation", {})
    counts = evaluation.get("counts", {})
    metrics = evaluation.get("metrics", {})
    outcomes = payload.get("outcomes", [])
    observed = {
        "schema_version": payload.get("schema_version"),
        "evaluation_schema_version": evaluation.get("schema_version"),
        "total_period_count": counts.get("total_period_count"),
        "evaluated_period_count": counts.get("evaluated_period_count"),
        "skipped_period_count": counts.get("skipped_period_count"),
        "sample_count": metrics.get("sample_count"),
        "outcome_statuses": [outcome.get("status") for outcome in outcomes],
    }
    if observed != _expected_summary():
        raise SystemExit(f"historical prediction smoke mismatch: {observed!r}")
