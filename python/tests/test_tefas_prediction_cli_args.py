from datetime import date

import pytest
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
            "--minimum-training-returns",
            "12",
            "--confidence-level",
            "0.95",
            "--model-version",
            "baseline-v2",
            "--output-format",
            "json",
        ],
        today=date(2026, 8, 12),
    )

    assert arguments.acquisition.request.normalized_fund_code == "AAL"
    assert str(arguments.prediction_date) == "2026-08-12"
    assert str(arguments.target_date) == "2026-08-13"
    assert arguments.model.lookback == 7
    assert arguments.model.minimum_training_returns == 12
    assert arguments.model.confidence_level == 0.95
    assert arguments.model.model_version == "baseline-v2"
    assert arguments.output_format == "json"


def test_rejects_target_on_prediction_date() -> None:
    with pytest.raises(SystemExit):
        parse_tefas_prediction_arguments(
            ["AAL", "--target-date", "2026-08-12"],
            today=date(2026, 8, 12),
        )
