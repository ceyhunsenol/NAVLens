import json
from pathlib import Path

import pytest
from navlens.prediction.artifact import (
    load_single_return_prediction_artifact,
)
from navlens.prediction.errors import InvalidPredictionArtifactError
from navlens.prediction.options import PredictionModelKind
from navlens.prediction.prediction_artifact_collection import (
    load_single_return_prediction_artifacts,
)
from navlens.prediction.tefas_suite_batch_output import (
    serialize_tefas_prediction_suite_batch,
)
from navlens.sources.tefas.batch import (
    TefasBatchFailure,
    TefasBatchResult,
    TefasBatchSuccess,
)
from prediction_artifact_fixtures import write_prediction_artifact
from tefas_prediction_fixtures import make_prediction_model_suite


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


def test_loads_and_flattens_tefas_prediction_model_suite_batch(tmp_path: Path) -> None:
    suite_aal = make_prediction_model_suite("AAL")
    suite_phe = make_prediction_model_suite("PHE")
    batch_result = TefasBatchResult(
        successes=(
            TefasBatchSuccess("AAL", suite_aal),
            TefasBatchSuccess("PHE", suite_phe),
        ),
        failures=(TefasBatchFailure("BAD", "ValueError", "bad fund"),),
    )
    path = tmp_path / "suite-batch.json"
    path.write_bytes(serialize_tefas_prediction_suite_batch(batch_result))

    artifacts = load_single_return_prediction_artifacts(path)

    expected_count = len(PredictionModelKind)
    assert len(artifacts) == 2 * expected_count
    assert [a.fund_id for a in artifacts[:expected_count]] == ["AAL"] * expected_count
    assert [a.fund_id for a in artifacts[expected_count:]] == ["PHE"] * expected_count


def test_rejects_suite_batch_with_zero_successes(tmp_path: Path) -> None:
    batch_result = TefasBatchResult(
        successes=(),
        failures=(TefasBatchFailure("BAD", "ValueError", "bad fund"),),
    )
    path = tmp_path / "zero-success-suite-batch.json"
    path.write_bytes(serialize_tefas_prediction_suite_batch(batch_result))

    with pytest.raises(InvalidPredictionArtifactError, match="at least one successful suite"):
        load_single_return_prediction_artifacts(path)


def test_rejects_malformed_suite_batch_envelope(tmp_path: Path) -> None:
    path = tmp_path / "malformed.json"
    payload = {
        "schema_version": "navlens-tefas-prediction-model-suite-batch-v1",
        "total_count": 5,
        "succeeded_count": 1,
        "failed_count": 0,
        "successes": [],
        "failures": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(InvalidPredictionArtifactError, match="counts do not match"):
        load_single_return_prediction_artifacts(path)


@pytest.mark.parametrize("corruption", ["duplicate-model", "mixed-fund"])
def test_suite_batch_delegates_embedded_suite_validation(
    corruption: str,
    tmp_path: Path,
) -> None:
    suite = make_prediction_model_suite("AAL")
    batch = TefasBatchResult(
        successes=(TefasBatchSuccess("AAL", suite),),
        failures=(),
    )
    payload = json.loads(serialize_tefas_prediction_suite_batch(batch))
    predictions = payload["successes"][0]["predictions"]
    if corruption == "duplicate-model":
        predictions[1] = predictions[0]
        expected = "unique model identities"
    else:
        predictions[1]["fund_id"] = "PHE"
        expected = "point-in-time scope"
    path = tmp_path / f"{corruption}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(InvalidPredictionArtifactError, match=expected):
        load_single_return_prediction_artifacts(path)
