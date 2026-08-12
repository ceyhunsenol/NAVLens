import json
from pathlib import Path

from navlens.prediction.live_history_comparison_cli import main
from prediction_artifact_fixtures import write_evaluation_artifact


def test_cli_compares_explicit_model_history_groups(capsys, tmp_path: Path) -> None:
    first = write_evaluation_artifact(tmp_path / "ridge.json", model_name="ridge")
    second = write_evaluation_artifact(
        tmp_path / "last-return.json",
        model_name="last-return",
        predicted_return_decimal=0.0,
    )
    output = tmp_path / "comparison.json"

    exit_code = main(
        [
            "--history",
            str(first),
            "--history",
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
    assert payload["schema_version"] == ("navlens-live-prediction-history-comparison-v1")
    assert [item["model_name"] for item in payload["histories"]] == [
        "ridge",
        "last-return",
    ]
