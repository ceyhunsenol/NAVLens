from datetime import date

import pytest
from navlens.prediction.tefas_batch_args import parse_tefas_prediction_batch_arguments


def test_maps_multiple_funds_and_shared_prediction_options() -> None:
    arguments = parse_tefas_prediction_batch_arguments(
        [
            "aal",
            "PHE",
            "--days",
            "90",
            "--auto-target-date",
            "--lookback",
            "7",
            "--max-price-age-days",
            "6",
        ],
        today=date(2026, 8, 14),
    )

    assert [item.request.normalized_fund_code for item in arguments.acquisitions] == [
        "AAL",
        "PHE",
    ]
    assert str(arguments.options.prediction_date) == "2026-08-14"
    assert str(arguments.options.target_date) == "2026-08-17"
    assert arguments.options.model.lookback == 7
    assert arguments.options.freshness.maximum_age_calendar_days == 6


def test_batch_rejects_duplicate_normalized_fund_codes() -> None:
    with pytest.raises(SystemExit) as exit_info:
        parse_tefas_prediction_batch_arguments(
            ["aal", "AAL", "--auto-target-date"],
            today=date(2026, 8, 12),
        )

    assert exit_info.value.code == 2
