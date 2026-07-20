from datetime import date
from pathlib import Path

import pytest
from navlens.evaluation.tefas_batch_arguments import parse_tefas_batch_arguments


def test_maps_multiple_funds_and_shared_options() -> None:
    arguments = parse_tefas_batch_arguments(
        [
            "aal",
            "YAY",
            "--days",
            "90",
            "--lookback",
            "4",
            "--run-root",
            "artifacts/runs",
        ],
        today=date(2026, 7, 20),
    )

    assert [item.request.normalized_fund_code for item in arguments.acquisitions] == ["AAL", "YAY"]
    assert all(item.request.start_date == date(2026, 4, 22) for item in arguments.acquisitions)
    assert arguments.estimator.lookback == 4
    assert arguments.run_root == Path("artifacts/runs")


def test_rejects_duplicate_normalized_fund_codes() -> None:
    with pytest.raises(SystemExit) as exit_info:
        parse_tefas_batch_arguments(
            ["aal", "AAL"],
            today=date(2026, 7, 20),
        )

    assert exit_info.value.code == 2
