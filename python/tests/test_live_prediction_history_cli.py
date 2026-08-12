import json
from pathlib import Path

from navlens.prediction.live_history_cli import main
from prediction_artifact_fixtures import write_evaluation_artifact


def test_cli_stores_versioned_aggregate_report(capsys, tmp_path: Path) -> None:
    first = write_evaluation_artifact(tmp_path / "first.json")
    second = write_evaluation_artifact(
        tmp_path / "second.json",
        evaluated_at="2026-07-22T12:00:00+00:00",
        last_observation_date="2026-07-21",
        prediction_date="2026-07-21",
        prediction_timestamp="2026-07-21T12:00:00+00:00",
        target_date="2026-07-22",
    )
    output = tmp_path / "history.json"

    exit_code = main(
        [
            str(first),
            str(second),
            "--output-format",
            "json",
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output.read_bytes())
    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""
    assert payload["sample_count"] == 2
    assert payload["schema_version"] == "navlens-live-prediction-history-v1"
