import json
from datetime import date
from pathlib import Path

import pytest
from navlens.prediction import live_history_cli, tefas_evaluation_batch_cli
from navlens.prediction.artifact import load_live_prediction_evaluation_artifacts
from navlens.prediction.errors import InvalidPredictionArtifactError
from navlens.sources.tefas import TefasAcquisitionResult, TefasPriceRecord
from prediction_artifact_fixtures import (
    prediction_artifact_payload,
    write_prediction_artifact,
)


class _FakeAcquisition:
    def acquire(self, request, as_of, acquired_at):
        records = (
            TefasPriceRecord(request.start_date, request.normalized_fund_code, 100.0),
            TefasPriceRecord(request.end_date, request.normalized_fund_code, 102.0),
        )
        return TefasAcquisitionResult(records, Path("tefas.json"), True)


def test_batch_isolates_failure_and_serializes_complete_success(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    prediction = write_prediction_artifact(tmp_path / "prediction.json")
    missing = tmp_path / "missing.json"
    output = tmp_path / "batch.json"
    _replace_acquisition(monkeypatch)

    exit_code = tefas_evaluation_batch_cli.main(_arguments(prediction, missing, output))

    captured = capsys.readouterr()
    payload = json.loads(output.read_bytes())
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == ""
    assert payload["schema_version"] == "navlens-tefas-prediction-evaluation-batch-v1"
    assert payload["succeeded_count"] == 1
    assert payload["failed_count"] == 1
    assert payload["successes"][0]["realized_return_decimal"] == pytest.approx(0.02)
    assert payload["failures"][0]["artifact_path"] == str(missing)


def test_history_cli_consumes_successes_from_batch_artifact(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    prediction = write_prediction_artifact(tmp_path / "prediction.json")
    batch_output = tmp_path / "batch.json"
    history_output = tmp_path / "history.json"
    _replace_acquisition(monkeypatch)
    assert (
        tefas_evaluation_batch_cli.main(
            _arguments(prediction, tmp_path / "missing.json", batch_output)
        )
        == 2
    )

    exit_code = live_history_cli.main(
        [str(batch_output), "--output-format", "json", "--output", str(history_output)]
    )

    captured = capsys.readouterr()
    payload = json.loads(history_output.read_bytes())
    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""
    assert payload["sample_count"] == 1


def test_evaluation_batch_consumes_prediction_batch_artifact(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    prediction_batch = tmp_path / "predictions.json"
    prediction_batch.write_text(
        json.dumps(
            {
                "failed_count": 0,
                "failures": [],
                "schema_version": "navlens-tefas-prediction-batch-v1",
                "succeeded_count": 2,
                "successes": [
                    prediction_artifact_payload(),
                    prediction_artifact_payload(fund_id="PHE"),
                ],
                "total_count": 2,
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "evaluations.json"
    _replace_acquisition(monkeypatch)

    exit_code = tefas_evaluation_batch_cli.main(
        [
            str(prediction_batch),
            "--as-of",
            "2026-08-12",
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
    assert payload["succeeded_count"] == 2
    assert [item["fund_id"] for item in payload["successes"]] == ["AAL", "PHE"]


def test_batch_loader_rejects_inconsistent_outcome_counts(tmp_path: Path) -> None:
    path = tmp_path / "batch.json"
    path.write_text(
        json.dumps(
            {
                "failed_count": 0,
                "failures": [],
                "schema_version": "navlens-tefas-prediction-evaluation-batch-v1",
                "succeeded_count": 1,
                "successes": [],
                "total_count": 1,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(InvalidPredictionArtifactError, match="counts"):
        load_live_prediction_evaluation_artifacts(path)


def _replace_acquisition(monkeypatch) -> None:
    monkeypatch.setattr(
        tefas_evaluation_batch_cli,
        "AcquireTefasPrices",
        lambda client, raw_root: _FakeAcquisition(),
    )


def _arguments(prediction: Path, missing: Path, output: Path) -> list[str]:
    return [
        str(prediction),
        str(missing),
        "--as-of",
        date(2026, 8, 12).isoformat(),
        "--output-format",
        "json",
        "--output",
        str(output),
    ]
