from datetime import date

import pytest
from navlens.prediction.tefas_suite_cli_args import (
    parse_tefas_prediction_suite_arguments,
)


def test_maps_shared_suite_configuration_without_model_selector() -> None:
    arguments = parse_tefas_prediction_suite_arguments(
        [
            "AAL",
            "--days",
            "90",
            "--auto-target-date",
            "--lookback",
            "7",
            "--minimum-training-returns",
            "12",
            "--model-version",
            "suite-v2",
        ],
        today=date(2026, 8, 12),
    )

    assert arguments.acquisition.request.normalized_fund_code == "AAL"
    assert arguments.options.lookback == 7
    assert arguments.options.minimum_training_returns == 12
    assert arguments.options.model_version == "suite-v2"


def test_rejects_single_model_option() -> None:
    with pytest.raises(SystemExit):
        parse_tefas_prediction_suite_arguments(
            ["AAL", "--auto-target-date", "--model", "linear"],
            today=date(2026, 8, 12),
        )
