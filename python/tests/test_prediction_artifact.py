from pathlib import Path

import pytest
from navlens.prediction.artifact import load_single_return_prediction_artifact
from navlens.prediction.errors import InvalidPredictionArtifactError
from prediction_artifact_fixtures import write_prediction_artifact


def test_loads_native_prediction_from_versioned_artifact(tmp_path: Path) -> None:
    path = write_prediction_artifact(tmp_path / "prediction.json")

    artifact = load_single_return_prediction_artifact(path)

    assert artifact.fund_id == "AAL"
    assert str(artifact.last_observation_date) == "2026-07-20"
    assert artifact.prediction.expected_return == pytest.approx(0.01)
    assert artifact.prediction.model.version == "v1"


def test_rejects_unknown_schema(tmp_path: Path) -> None:
    path = write_prediction_artifact(tmp_path / "prediction.json", schema_version="future-v2")

    with pytest.raises(InvalidPredictionArtifactError, match="unsupported"):
        load_single_return_prediction_artifact(path)


def test_rejects_missing_required_field(tmp_path: Path) -> None:
    path = write_prediction_artifact(tmp_path / "prediction.json")
    path.write_text('{"schema_version": "navlens-single-return-prediction-v1"}', encoding="utf-8")

    with pytest.raises(InvalidPredictionArtifactError, match="missing required fields"):
        load_single_return_prediction_artifact(path)


def test_rejects_duplicate_json_fields(tmp_path: Path) -> None:
    path = tmp_path / "prediction.json"
    path.write_text('{"schema_version":"v1","schema_version":"v1"}', encoding="utf-8")

    with pytest.raises(InvalidPredictionArtifactError, match="duplicate"):
        load_single_return_prediction_artifact(path)
