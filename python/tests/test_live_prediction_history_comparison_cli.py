import json
from pathlib import Path

import pytest
from navlens.prediction.live_history_comparison_cli import main
from prediction_artifact_fixtures import (
    evaluation_artifact_payload,
    write_evaluation_artifact,
    write_evaluation_batch_artifact,
)


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


def test_cli_compares_automatic_evaluation_artifacts_mode(capsys, tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1-batch.json",
        [
            evaluation_artifact_payload(model_name="ridge", predicted_return_decimal=0.01),
            evaluation_artifact_payload(model_name="linear", predicted_return_decimal=0.015),
            evaluation_artifact_payload(model_name="last-return", predicted_return_decimal=0.0),
        ],
    )
    output = tmp_path / "comparison.json"

    exit_code = main(
        [
            "--evaluation-artifacts",
            str(day1),
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
    assert payload["schema_version"] == "navlens-live-prediction-history-comparison-v1"
    assert [item["model_name"] for item in payload["histories"]] == [
        "ridge",
        "linear",
        "last-return",
    ]


def test_cli_rejects_both_history_and_evaluation_artifacts(tmp_path: Path) -> None:
    first = write_evaluation_artifact(tmp_path / "ridge.json", model_name="ridge")
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [evaluation_artifact_payload(model_name="ridge")],
    )

    with pytest.raises(SystemExit):
        main(["--history", str(first), "--evaluation-artifacts", str(day1)])


def test_cli_rejects_neither_history_nor_evaluation_artifacts() -> None:
    with pytest.raises(SystemExit):
        main([])
