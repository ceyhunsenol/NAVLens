from datetime import date
from pathlib import Path

import pytest
from navlens.prediction import PredictionModelKind
from navlens.prediction.tefas_cli_args import parse_tefas_prediction_arguments


def test_parses_acquisition_and_explicit_target_date() -> None:
    arguments = parse_tefas_prediction_arguments(
        [
            "AAL",
            "--days",
            "60",
            "--target-date",
            "2026-08-13",
            "--lookback",
            "7",
            "--model",
            "historical-mean",
            "--minimum-training-returns",
            "12",
            "--confidence-level",
            "0.95",
            "--model-version",
            "baseline-v2",
            "--max-price-age-days",
            "6",
            "--output-format",
            "json",
            "--output",
            "artifacts/prediction.json",
        ],
        today=date(2026, 8, 12),
    )

    assert arguments.acquisition.request.normalized_fund_code == "AAL"
    assert str(arguments.prediction_date) == "2026-08-12"
    assert str(arguments.target_date) == "2026-08-13"
    assert arguments.model.lookback == 7
    assert arguments.model.model_kind is PredictionModelKind.HISTORICAL_MEAN
    assert arguments.model.minimum_training_returns == 12
    assert arguments.model.confidence_level == 0.95
    assert arguments.model.model_version == "baseline-v2"
    assert arguments.freshness.maximum_age_calendar_days == 6
    assert arguments.output_format == "json"
    assert arguments.output_path == Path("artifacts/prediction.json")


def test_rejects_target_on_prediction_date() -> None:
    with pytest.raises(SystemExit):
        parse_tefas_prediction_arguments(
            ["AAL", "--target-date", "2026-08-12"],
            today=date(2026, 8, 12),
        )


def test_selects_next_weekday_automatically() -> None:
    arguments = parse_tefas_prediction_arguments(
        ["AAL", "--auto-target-date"],
        today=date(2026, 8, 12),
    )

    assert str(arguments.target_date) == "2026-08-13"


def test_automatic_target_skips_weekend() -> None:
    arguments = parse_tefas_prediction_arguments(
        ["AAL", "--auto-target-date"],
        today=date(2026, 8, 14),
    )

    assert str(arguments.target_date) == "2026-08-17"


def test_automatic_target_skips_declared_closure() -> None:
    arguments = parse_tefas_prediction_arguments(
        ["AAL", "--auto-target-date", "--closed-date", "2026-08-17"],
        today=date(2026, 8, 14),
    )

    assert str(arguments.target_date) == "2026-08-18"


@pytest.mark.parametrize(
    "arguments",
    [
        ["AAL"],
        [
            "AAL",
            "--target-date",
            "2026-08-13",
            "--auto-target-date",
        ],
        [
            "AAL",
            "--target-date",
            "2026-08-13",
            "--closed-date",
            "2026-08-14",
        ],
        [
            "AAL",
            "--auto-target-date",
            "--closed-date",
            "2026-08-14",
            "--closed-date",
            "2026-08-14",
        ],
    ],
)
def test_rejects_ambiguous_target_configuration(arguments: list[str]) -> None:
    with pytest.raises(SystemExit):
        parse_tefas_prediction_arguments(arguments, today=date(2026, 8, 12))
