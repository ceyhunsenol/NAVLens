import json

from navlens.prediction.model_suite_output import serialize_prediction_model_suite
from navlens.prediction.options import PredictionModelKind
from navlens.prediction.tefas_suite_batch_output import (
    format_tefas_prediction_suite_batch,
    serialize_tefas_prediction_suite_batch,
)
from navlens.sources.tefas.batch import (
    TefasBatchFailure,
    TefasBatchResult,
    TefasBatchSuccess,
)
from tefas_prediction_fixtures import make_prediction_model_suite


def test_format_tefas_prediction_suite_batch_text_table() -> None:
    suite = make_prediction_model_suite("AAL")
    result = TefasBatchResult(
        successes=(TefasBatchSuccess("AAL", suite),),
        failures=(TefasBatchFailure("BAD", "TefasTransportError", "timeout"),),
    )

    text = format_tefas_prediction_suite_batch(result)

    assert "batch_total=2" in text
    assert "batch_succeeded=1" in text
    assert "batch_failed=1" in text
    assert "fund,status,prediction_date,target_date,models,error_type,error" in text
    assert "AAL,success,2026-08-02,2026-08-03" in text
    assert "BAD,failure,,,,TefasTransportError,timeout" in text


def test_serialize_tefas_prediction_suite_batch_json() -> None:
    suite = make_prediction_model_suite("AAL")
    result = TefasBatchResult(
        successes=(TefasBatchSuccess("AAL", suite),),
        failures=(TefasBatchFailure("BAD", "TefasTransportError", "timeout"),),
    )

    serialized = serialize_tefas_prediction_suite_batch(result)
    payload = json.loads(serialized.decode("utf-8"))

    assert payload["schema_version"] == "navlens-tefas-prediction-model-suite-batch-v1"
    assert payload["total_count"] == 2
    assert payload["succeeded_count"] == 1
    assert payload["failed_count"] == 1
    assert len(payload["successes"]) == 1
    assert payload["successes"][0]["schema_version"] == "navlens-prediction-model-suite-v1"
    assert len(payload["successes"][0]["predictions"]) == len(PredictionModelKind)
    assert payload["successes"][0] == json.loads(serialize_prediction_model_suite(suite))
    assert payload["failures"][0]["fund_id"] == "BAD"
    assert payload["failures"][0]["error_type"] == "TefasTransportError"
