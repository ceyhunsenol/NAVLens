from datetime import date

import pytest
from navlens.prediction.tefas_batch_args import parse_tefas_prediction_batch_arguments
from navlens.prediction.tefas_suite_batch_args import (
    parse_tefas_prediction_suite_batch_arguments,
)
from navlens.prediction.tefas_suite_cli_args import (
    parse_tefas_prediction_suite_arguments,
)


def test_only_one_fund_codes_positional_exists() -> None:
    arguments = parse_tefas_prediction_suite_batch_arguments(
        ["AAL", "PHE", "TLY", "--days", "10", "--auto-target-date"],
        today=date(2026, 7, 20),
    )
    assert len(arguments.acquisitions) == 3
    assert [a.request.fund_code for a in arguments.acquisitions] == ["AAL", "PHE", "TLY"]


def test_multiple_funds_parse_correctly_with_shared_prediction_options() -> None:
    arguments = parse_tefas_prediction_suite_batch_arguments(
        [
            "AAL",
            "PHE",
            "--auto-target-date",
            "--lookback",
            "7",
            "--confidence-level",
            "0.95",
            "--model-version",
            "v2",
            "--output-format",
            "json",
        ],
        today=date(2026, 7, 20),
    )
    assert len(arguments.acquisitions) == 2
    assert arguments.suite_options.lookback == 7
    assert arguments.suite_options.confidence_level == 0.95
    assert arguments.suite_options.model_version == "v2"
    assert arguments.output_format == "json"


def test_model_option_is_rejected() -> None:
    with pytest.raises(SystemExit):
        parse_tefas_prediction_suite_batch_arguments(
            ["AAL", "PHE", "--auto-target-date", "--model", "linear"],
            today=date(2026, 7, 20),
        )


def test_duplicate_normalized_funds_are_rejected() -> None:
    with pytest.raises(SystemExit):
        parse_tefas_prediction_suite_batch_arguments(
            ["AAL", "aal", "--auto-target-date"],
            today=date(2026, 7, 20),
        )


def test_single_suite_and_ordinary_batch_parsings_remain_unchanged() -> None:
    single = parse_tefas_prediction_suite_arguments(
        ["AAL", "--auto-target-date", "--lookback", "5"],
        today=date(2026, 7, 20),
    )
    assert single.acquisition.request.fund_code == "AAL"
    assert single.options.lookback == 5

    batch = parse_tefas_prediction_batch_arguments(
        ["AAL", "PHE", "--auto-target-date", "--model", "linear"],
        today=date(2026, 7, 20),
    )
    assert len(batch.acquisitions) == 2
    assert batch.options.model.model_kind.value == "linear"
