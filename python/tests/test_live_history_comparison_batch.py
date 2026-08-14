import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from navlens import BacktestMetrics, MarketDate, NavlensValidationError
from navlens.prediction.errors import (
    InvalidLivePredictionHistoryComparisonError,
    InvalidLivePredictionHistoryError,
    PredictionArtifactError,
)
from navlens.prediction.live_history_comparison_batch import (
    LivePredictionHistoryComparisonBatchFailure,
    LivePredictionHistoryComparisonBatchResult,
    LivePredictionHistoryComparisonBatchSuccess,
    LivePredictionHistoryComparisonScopeFailureReason,
    _map_scope_failure_reason,
    compare_live_prediction_history_batches,
)
from navlens.prediction.live_history_comparison_batch_output import (
    serialize_live_prediction_history_comparison_batch,
)
from prediction_artifact_fixtures import (
    evaluation_artifact_payload,
    write_evaluation_artifact,
    write_evaluation_batch_artifact,
)


def test_batch_preserves_interleaved_outcome_order_across_successes_and_failures(
    tmp_path: Path,
) -> None:
    # Scope 1 (AAL:tefas): 1 model (will fail with INVALID_COMPARISON)
    # Scope 2 (YAK:tefas): 2 models (will succeed)
    # Scope 3 (TI1:tefas): 1 model (will fail with INVALID_COMPARISON)
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge"),
            evaluation_artifact_payload(fund_id="YAK", model_name="ridge"),
            evaluation_artifact_payload(fund_id="YAK", model_name="linear"),
            evaluation_artifact_payload(fund_id="TI1", model_name="last-return"),
        ],
    )

    result = compare_live_prediction_history_batches([day1])

    assert result.total_count == 3
    assert result.succeeded_count == 1
    assert result.failed_count == 2
    assert [(item.fund_id, item.source_id, type(item).__name__) for item in result.outcomes] == [
        ("AAL", "tefas", "LivePredictionHistoryComparisonBatchFailure"),
        ("YAK", "tefas", "LivePredictionHistoryComparisonBatchSuccess"),
        ("TI1", "tefas", "LivePredictionHistoryComparisonBatchFailure"),
    ]
    assert result.outcomes[0].reason_code == (
        LivePredictionHistoryComparisonScopeFailureReason.INVALID_COMPARISON
    )
    assert result.outcomes[2].reason_code == (
        LivePredictionHistoryComparisonScopeFailureReason.INVALID_COMPARISON
    )
    payload = json.loads(serialize_live_prediction_history_comparison_batch(result))
    assert [item["status"] for item in payload["outcomes"]] == [
        "failure",
        "success",
        "failure",
    ]


def test_batch_derived_properties_and_immutability(tmp_path: Path) -> None:
    path = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge"),
            evaluation_artifact_payload(fund_id="AAL", model_name="linear"),
        ],
    )

    result = compare_live_prediction_history_batches([path])

    assert len(result.outcomes) == 1
    assert len(result.successes) == 1
    assert len(result.failures) == 0
    assert result.total_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0

    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.outcomes = ()  # type: ignore[misc]


def test_contract_invariants_post_init(tmp_path: Path) -> None:
    path = write_evaluation_batch_artifact(
        tmp_path / "eval.json",
        [
            evaluation_artifact_payload(model_name="ridge"),
            evaluation_artifact_payload(model_name="linear"),
        ],
    )
    comparison = compare_live_prediction_history_batches([path]).successes[0].comparison

    with pytest.raises(ValueError, match="non-empty string"):
        LivePredictionHistoryComparisonBatchSuccess("", "tefas", comparison)

    with pytest.raises(ValueError, match="match comparison scope"):
        LivePredictionHistoryComparisonBatchSuccess("OTHER", "tefas", comparison)

    with pytest.raises(ValueError, match="reason_code must be"):
        LivePredictionHistoryComparisonBatchFailure(
            "AAL",
            "tefas",
            "invalid_history",
            "Error",
            "msg",  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="outcomes must be a non-empty tuple"):
        LivePredictionHistoryComparisonBatchResult(())


def test_reason_code_mapping_for_expected_exceptions() -> None:
    err_hist = InvalidLivePredictionHistoryError("empty history")
    err_comp = InvalidLivePredictionHistoryComparisonError("mismatched dates")
    err_native = NavlensValidationError("invalid native date")

    assert (
        _map_scope_failure_reason(err_hist)
        == LivePredictionHistoryComparisonScopeFailureReason.INVALID_HISTORY
    )
    assert (
        _map_scope_failure_reason(err_comp)
        == LivePredictionHistoryComparisonScopeFailureReason.INVALID_COMPARISON
    )
    assert (
        _map_scope_failure_reason(err_native)
        == LivePredictionHistoryComparisonScopeFailureReason.NATIVE_VALIDATION
    )


def test_unexpected_programming_errors_escape_scope_isolation(monkeypatch, tmp_path: Path) -> None:
    path = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge"),
            evaluation_artifact_payload(fund_id="AAL", model_name="linear"),
        ],
    )

    def _boom(*_args, **_kwargs):
        raise TypeError("unexpected programming error")

    monkeypatch.setattr(
        "navlens.prediction.live_history_comparison_batch.compare_live_prediction_histories",
        _boom,
    )

    with pytest.raises(TypeError, match="unexpected programming error"):
        compare_live_prediction_history_batches([path])


def test_global_input_failure_on_corrupt_file_or_empty_paths(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("not json", encoding="utf-8")

    with pytest.raises(PredictionArtifactError):
        compare_live_prediction_history_batches([corrupt])

    with pytest.raises(InvalidLivePredictionHistoryComparisonError, match="empty"):
        compare_live_prediction_history_batches([])


def test_multiple_funds_and_three_models_per_fund_succeed(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge"),
            evaluation_artifact_payload(fund_id="AAL", model_name="linear"),
            evaluation_artifact_payload(fund_id="AAL", model_name="last-return"),
            evaluation_artifact_payload(fund_id="YAK", model_name="ridge"),
            evaluation_artifact_payload(fund_id="YAK", model_name="linear"),
            evaluation_artifact_payload(fund_id="YAK", model_name="last-return"),
        ],
    )

    result = compare_live_prediction_history_batches([day1])

    assert result.total_count == 2
    assert result.succeeded_count == 2
    assert result.failed_count == 0
    assert result.successes[0].fund_id == "AAL"
    assert result.successes[1].fund_id == "YAK"
    for success in result.successes:
        assert len(success.comparison.histories) == 3


def test_scope_and_model_first_seen_ordering_determinism(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="YAK", model_name="linear"),
            evaluation_artifact_payload(fund_id="YAK", model_name="ridge"),
            evaluation_artifact_payload(fund_id="AAL", model_name="last-return"),
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge"),
        ],
    )

    result = compare_live_prediction_history_batches([day1])

    assert [s.fund_id for s in result.successes] == ["YAK", "AAL"]
    yak_models = [
        h.artifacts[0].prediction_artifact.prediction.model.name
        for h in result.successes[0].comparison.histories
    ]
    aal_models = [
        h.artifacts[0].prediction_artifact.prediction.model.name
        for h in result.successes[1].comparison.histories
    ]
    assert yak_models == ["linear", "ridge"]
    assert aal_models == ["last-return", "ridge"]


def test_single_pass_generator_consumption(tmp_path: Path) -> None:
    path = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge"),
            evaluation_artifact_payload(fund_id="AAL", model_name="linear"),
        ],
    )

    generator = (p for p in [path])
    result = compare_live_prediction_history_batches(generator)

    assert result.succeeded_count == 1


def test_different_source_ids_form_separate_scopes(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", source_id="tefas", model_name="ridge"),
            evaluation_artifact_payload(fund_id="AAL", source_id="tefas", model_name="linear"),
            evaluation_artifact_payload(fund_id="AAL", source_id="csv", model_name="ridge"),
            evaluation_artifact_payload(fund_id="AAL", source_id="csv", model_name="linear"),
        ],
    )

    result = compare_live_prediction_history_batches([day1])

    assert result.total_count == 2
    assert [(s.fund_id, s.source_id) for s in result.successes] == [
        ("AAL", "tefas"),
        ("AAL", "csv"),
    ]


def test_different_model_versions_remain_separate_identities(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge", model_version="v1"),
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge", model_version="v2"),
        ],
    )

    result = compare_live_prediction_history_batches([day1])

    assert result.succeeded_count == 1
    versions = [
        h.artifacts[0].prediction_artifact.prediction.model.version
        for h in result.successes[0].comparison.histories
    ]
    assert versions == ["v1", "v2"]


def test_different_feature_set_versions_remain_separate_identities(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(model_name="ridge", feature_schema_version="returns-v1"),
            evaluation_artifact_payload(model_name="ridge", feature_schema_version="returns-v2"),
        ],
    )

    result = compare_live_prediction_history_batches([day1])

    assert result.succeeded_count == 1
    feature_sets = [
        history.artifacts[0].prediction_artifact.prediction.model.feature_set_version
        for history in result.successes[0].comparison.histories
    ]
    assert feature_sets == ["returns-v1", "returns-v2"]


def test_single_and_batch_artifacts_preserve_period_order(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(model_name="ridge"),
            evaluation_artifact_payload(model_name="linear"),
        ],
    )
    ridge_day2 = write_evaluation_artifact(
        tmp_path / "ridge-day2.json",
        model_name="ridge",
        prediction_date="2026-07-21",
        target_date="2026-07-22",
        last_observation_date="2026-07-21",
        prediction_timestamp="2026-07-21T12:00:00+00:00",
        evaluated_at="2026-07-22T12:00:00+00:00",
    )
    linear_day2 = write_evaluation_artifact(
        tmp_path / "linear-day2.json",
        model_name="linear",
        prediction_date="2026-07-21",
        target_date="2026-07-22",
        last_observation_date="2026-07-21",
        prediction_timestamp="2026-07-21T12:00:00+00:00",
        evaluated_at="2026-07-22T12:00:00+00:00",
    )

    result = compare_live_prediction_history_batches([day1, ridge_day2, linear_day2])

    histories = result.successes[0].comparison.histories
    assert all(len(history.artifacts) == 2 for history in histories)
    assert [item.prediction_artifact.prediction_date for item in histories[0].artifacts] == [
        MarketDate(2026, 7, 20),
        MarketDate(2026, 7, 21),
    ]


def test_preserves_native_rust_backtest_metrics(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge"),
            evaluation_artifact_payload(fund_id="AAL", model_name="linear"),
        ],
    )

    result = compare_live_prediction_history_batches([day1])

    metrics = result.successes[0].comparison.histories[0].metrics
    assert isinstance(metrics, BacktestMetrics)
    assert metrics.sample_count == 1


def test_inputs_and_loaded_artifacts_are_not_mutated(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge"),
            evaluation_artifact_payload(fund_id="AAL", model_name="linear"),
        ],
    )
    original_bytes = day1.read_bytes()

    result = compare_live_prediction_history_batches([day1])

    assert day1.read_bytes() == original_bytes
    artifact = result.successes[0].comparison.histories[0].artifacts[0]
    with pytest.raises((FrozenInstanceError, AttributeError)):
        artifact.realized_return_decimal = 0.999
