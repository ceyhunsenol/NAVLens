import json
from datetime import date
from pathlib import Path

import pytest
from navlens.prediction import tefas_evaluation_cli
from navlens.sources.tefas import TefasAcquisitionResult, TefasPriceRecord
from prediction_artifact_fixtures import write_prediction_artifact


class _FakeAcquisition:
    def acquire(self, request, as_of, acquired_at):
        assert request.start_date == date(2026, 7, 20)
        assert request.end_date == date(2026, 7, 21)
        records = (
            TefasPriceRecord(date(2026, 7, 20), "AAL", 100.0),
            TefasPriceRecord(date(2026, 7, 21), "AAL", 102.0),
        )
        return TefasAcquisitionResult(records, Path("tefas.json"), True)


def test_cli_evaluates_and_stores_json_report(monkeypatch, capsys, tmp_path: Path) -> None:
    artifact_path = write_prediction_artifact(tmp_path / "prediction.json")
    output_path = tmp_path / "evaluation.json"
    monkeypatch.setattr(
        tefas_evaluation_cli,
        "AcquireTefasPrices",
        lambda client, raw_root: _FakeAcquisition(),
    )

    exit_code = tefas_evaluation_cli.main(
        [
            str(artifact_path),
            "--as-of",
            "2026-08-12",
            "--output-format",
            "json",
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output_path.read_bytes())
    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""
    assert payload["schema_version"] == "navlens-live-prediction-evaluation-v1"
    assert payload["predicted_return_decimal"] == 0.01
    assert payload["realized_return_decimal"] == pytest.approx(0.02)


def test_cli_rejects_target_after_evaluation_as_of(monkeypatch, capsys, tmp_path: Path) -> None:
    artifact_path = write_prediction_artifact(tmp_path / "prediction.json")
    monkeypatch.setattr(
        tefas_evaluation_cli,
        "AcquireTefasPrices",
        lambda client, raw_root: _FakeAcquisition(),
    )

    exit_code = tefas_evaluation_cli.main([str(artifact_path), "--as-of", "2026-07-20"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "after evaluation as-of date" in captured.err
