from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from navlens import BacktestMetrics, MarketDate
from navlens.prediction.errors import (
    InvalidLivePredictionHistoryComparisonError,
    InvalidPredictionArtifactError,
)
from navlens.prediction.live_history_comparison import compare_live_prediction_histories
from navlens.prediction.live_history_grouping import load_grouped_live_prediction_histories
from prediction_artifact_fixtures import (
    evaluation_artifact_payload,
    write_evaluation_artifact,
    write_evaluation_batch_artifact,
)


def test_automatic_mode_groups_three_models_from_multiple_daily_batches(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1-batch.json",
        [
            evaluation_artifact_payload(
                model_name="ridge",
                predicted_return_decimal=0.01,
                prediction_date="2026-07-20",
                target_date="2026-07-21",
                last_observation_date="2026-07-20",
                realized_return_decimal=0.02,
            ),
            evaluation_artifact_payload(
                model_name="linear",
                predicted_return_decimal=0.015,
                prediction_date="2026-07-20",
                target_date="2026-07-21",
                last_observation_date="2026-07-20",
                realized_return_decimal=0.02,
            ),
            evaluation_artifact_payload(
                model_name="last-return",
                predicted_return_decimal=0.0,
                prediction_date="2026-07-20",
                target_date="2026-07-21",
                last_observation_date="2026-07-20",
                realized_return_decimal=0.02,
            ),
        ],
    )
    day2 = write_evaluation_batch_artifact(
        tmp_path / "day2-batch.json",
        [
            evaluation_artifact_payload(
                model_name="ridge",
                predicted_return_decimal=-0.005,
                prediction_date="2026-07-21",
                target_date="2026-07-22",
                last_observation_date="2026-07-21",
                prediction_timestamp="2026-07-21T12:00:00+00:00",
                evaluated_at="2026-07-22T12:00:00+00:00",
                realized_return_decimal=-0.01,
            ),
            evaluation_artifact_payload(
                model_name="linear",
                predicted_return_decimal=-0.008,
                prediction_date="2026-07-21",
                target_date="2026-07-22",
                last_observation_date="2026-07-21",
                prediction_timestamp="2026-07-21T12:00:00+00:00",
                evaluated_at="2026-07-22T12:00:00+00:00",
                realized_return_decimal=-0.01,
            ),
            evaluation_artifact_payload(
                model_name="last-return",
                predicted_return_decimal=0.0,
                prediction_date="2026-07-21",
                target_date="2026-07-22",
                last_observation_date="2026-07-21",
                prediction_timestamp="2026-07-21T12:00:00+00:00",
                evaluated_at="2026-07-22T12:00:00+00:00",
                realized_return_decimal=-0.01,
            ),
        ],
    )

    histories = load_grouped_live_prediction_histories([day1, day2])

    assert len(histories) == 3
    model_names = [h.artifacts[0].prediction_artifact.prediction.model.name for h in histories]
    assert model_names == ["ridge", "linear", "last-return"]
    for h in histories:
        assert len(h.artifacts) == 2
        assert isinstance(h.metrics, BacktestMetrics)
        assert h.metrics.sample_count == 2


def test_model_group_order_is_deterministic_and_first_seen(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(model_name="linear"),
            evaluation_artifact_payload(model_name="ridge"),
            evaluation_artifact_payload(model_name="last-return"),
        ],
    )

    histories = load_grouped_live_prediction_histories([day1])

    names = [h.artifacts[0].prediction_artifact.prediction.model.name for h in histories]
    assert names == ["linear", "ridge", "last-return"]


def test_period_order_inside_each_model_is_preserved(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(
                model_name="ridge",
                prediction_date="2026-07-20",
                target_date="2026-07-21",
            )
        ],
    )
    day2 = write_evaluation_batch_artifact(
        tmp_path / "day2.json",
        [
            evaluation_artifact_payload(
                model_name="ridge",
                prediction_date="2026-07-21",
                target_date="2026-07-22",
                last_observation_date="2026-07-21",
                prediction_timestamp="2026-07-21T12:00:00+00:00",
                evaluated_at="2026-07-22T12:00:00+00:00",
            )
        ],
    )

    histories = load_grouped_live_prediction_histories([day1, day2])

    ridge_artifacts = histories[0].artifacts
    date1 = ridge_artifacts[0].prediction_artifact.prediction_date
    date2 = ridge_artifacts[1].prediction_artifact.prediction_date
    assert date1 == MarketDate(2026, 7, 20)
    assert date2 == MarketDate(2026, 7, 21)


def test_resulting_metrics_originate_from_rust_backed_path(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(
                model_name="ridge",
                predicted_return_decimal=0.01,
                realized_return_decimal=0.03,
            )
        ],
    )

    histories = load_grouped_live_prediction_histories([day1])

    metrics = histories[0].metrics
    assert isinstance(metrics, BacktestMetrics)
    assert metrics.mean_absolute_error == pytest.approx(0.02)


def test_generator_path_iterable_is_consumed_once(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [evaluation_artifact_payload(model_name="ridge")],
    )

    generator = (path for path in [day1])
    histories = load_grouped_live_prediction_histories(generator)

    assert len(histories) == 1
    assert histories[0].artifacts[0].prediction_artifact.prediction.model.name == "ridge"


def test_single_evaluation_and_batch_artifacts_can_be_mixed(tmp_path: Path) -> None:
    batch_path = write_evaluation_batch_artifact(
        tmp_path / "batch.json",
        [
            evaluation_artifact_payload(model_name="ridge", predicted_return_decimal=0.01),
            evaluation_artifact_payload(model_name="linear", predicted_return_decimal=0.015),
        ],
    )
    single_ridge = write_evaluation_artifact(
        tmp_path / "single-ridge.json",
        model_name="ridge",
        prediction_date="2026-07-21",
        target_date="2026-07-22",
        last_observation_date="2026-07-21",
        prediction_timestamp="2026-07-21T12:00:00+00:00",
        evaluated_at="2026-07-22T12:00:00+00:00",
    )
    single_linear = write_evaluation_artifact(
        tmp_path / "single-linear.json",
        model_name="linear",
        prediction_date="2026-07-21",
        target_date="2026-07-22",
        last_observation_date="2026-07-21",
        prediction_timestamp="2026-07-21T12:00:00+00:00",
        evaluated_at="2026-07-22T12:00:00+00:00",
    )

    histories = load_grouped_live_prediction_histories([batch_path, single_ridge, single_linear])

    assert len(histories) == 2
    assert len(histories[0].artifacts) == 2
    assert len(histories[1].artifacts) == 2


def test_missing_model_on_one_period_is_rejected_by_fair_comparison(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(model_name="ridge"),
            evaluation_artifact_payload(model_name="linear"),
        ],
    )
    day2 = write_evaluation_batch_artifact(
        tmp_path / "day2.json",
        [
            evaluation_artifact_payload(
                model_name="ridge",
                prediction_date="2026-07-21",
                target_date="2026-07-22",
                last_observation_date="2026-07-21",
                prediction_timestamp="2026-07-21T12:00:00+00:00",
                evaluated_at="2026-07-22T12:00:00+00:00",
            )
        ],
    )

    histories = load_grouped_live_prediction_histories([day1, day2])

    with pytest.raises(InvalidLivePredictionHistoryComparisonError, match="identical prediction"):
        compare_live_prediction_histories(histories)


def test_different_realized_returns_rejected_by_comparison(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(model_name="ridge", realized_return_decimal=0.02),
            evaluation_artifact_payload(model_name="linear", realized_return_decimal=0.03),
        ],
    )

    histories = load_grouped_live_prediction_histories([day1])

    with pytest.raises(InvalidLivePredictionHistoryComparisonError, match="realized"):
        compare_live_prediction_histories(histories)


def test_different_confidence_levels_rejected_by_comparison(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(model_name="ridge", confidence_level=0.90),
            evaluation_artifact_payload(model_name="linear", confidence_level=0.95),
        ],
    )

    histories = load_grouped_live_prediction_histories([day1])

    with pytest.raises(InvalidLivePredictionHistoryComparisonError, match="confidence"):
        compare_live_prediction_histories(histories)


def test_different_fund_or_source_rejected_by_comparison(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(model_name="ridge", fund_id="AAL"),
            evaluation_artifact_payload(model_name="linear", fund_id="YAK"),
        ],
    )

    histories = load_grouped_live_prediction_histories([day1])

    with pytest.raises(InvalidLivePredictionHistoryComparisonError, match="fund and source"):
        compare_live_prediction_histories(histories)


def test_different_model_versions_remain_separate_identities(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(model_name="ridge", model_version="v1"),
            evaluation_artifact_payload(model_name="ridge", model_version="v2"),
        ],
    )

    histories = load_grouped_live_prediction_histories([day1])

    assert len(histories) == 2
    versions = [h.artifacts[0].prediction_artifact.prediction.model.version for h in histories]
    assert versions == ["v1", "v2"]


def test_different_feature_set_versions_remain_separate_identities(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(model_name="ridge", feature_schema_version="returns-v1"),
            evaluation_artifact_payload(model_name="ridge", feature_schema_version="returns-v2"),
        ],
    )

    histories = load_grouped_live_prediction_histories([day1])

    assert len(histories) == 2
    feature_sets = [
        history.artifacts[0].prediction_artifact.prediction.model.feature_set_version
        for history in histories
    ]
    assert feature_sets == ["returns-v1", "returns-v2"]


def test_empty_paths_iterable_fails_with_typed_error() -> None:
    with pytest.raises(InvalidLivePredictionHistoryComparisonError, match="empty"):
        load_grouped_live_prediction_histories([])


def test_invalid_artifact_json_fails_with_typed_error(tmp_path: Path) -> None:
    bad_file = tmp_path / "corrupt.json"
    bad_file.write_text("not json", encoding="utf-8")

    with pytest.raises(InvalidPredictionArtifactError):
        load_grouped_live_prediction_histories([bad_file])


def test_input_files_and_loaded_artifacts_are_not_mutated(tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [evaluation_artifact_payload(model_name="ridge")],
    )
    original_bytes = day1.read_bytes()

    histories = load_grouped_live_prediction_histories([day1])

    assert day1.read_bytes() == original_bytes
    artifact = histories[0].artifacts[0]
    with pytest.raises((FrozenInstanceError, AttributeError)):
        artifact.realized_return_decimal = 0.999
