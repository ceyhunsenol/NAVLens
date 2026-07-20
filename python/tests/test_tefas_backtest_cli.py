from datetime import date, timedelta
from pathlib import Path

import pytest
from navlens.evaluation import tefas_cli
from navlens.evaluation.tefas_cli_arguments import parse_tefas_backtest_arguments
from navlens.sources.tefas import TefasAcquisitionResult, TefasPriceRecord


def test_maps_acquisition_and_estimator_arguments() -> None:
    arguments = parse_tefas_backtest_arguments(
        ["aal", "--days", "365", "--lookback", "5", "--confidence-level", "0.8"],
        today=date(2026, 7, 20),
    )

    assert arguments.acquisition.request.normalized_fund_code == "AAL"
    assert arguments.acquisition.request.start_date == date(2025, 7, 21)
    assert arguments.estimator.lookback == 5
    assert arguments.estimator.confidence_level == pytest.approx(0.8)


def test_rejects_baseline_training_window_below_minimum() -> None:
    with pytest.raises(SystemExit) as exit_info:
        parse_tefas_backtest_arguments(
            ["AAL", "--lookback", "3", "--minimum-training-returns", "5"],
            today=date(2026, 7, 20),
        )

    assert exit_info.value.code == 2


def test_main_runs_full_tefas_backtest_pipeline(monkeypatch, capsys, tmp_path: Path) -> None:
    class FakeAcquisition:
        def __init__(self, _client, raw_root) -> None:
            assert raw_root == tmp_path

        def acquire(self, request, _as_of, acquired_at) -> TefasAcquisitionResult:
            assert acquired_at.utcoffset() is not None
            return TefasAcquisitionResult(
                _price_records(request.normalized_fund_code),
                tmp_path / "payload.json",
                True,
            )

    monkeypatch.setattr(tefas_cli, "AcquireTefasPrices", FakeAcquisition)

    exit_code = tefas_cli.main(
        [
            "AAL",
            "--days",
            "12",
            "--end",
            "2026-07-20",
            "--as-of",
            "2026-07-20",
            "--raw-root",
            str(tmp_path),
            "--lookback",
            "2",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "fund=AAL" in output
    assert "predictions=3" in output
    assert "mae_decimal=" in output
    assert "direction_accuracy=" in output
    assert "comparison_model,mae_decimal,rmse_decimal" in output
    assert "linear-regression-baseline@0.1.0" in output
    assert "historical-mean-baseline@0.1.0" in output
    assert "last-return-baseline@0.1.0" in output
    assert "prediction_date,target_date,predicted_return_decimal" in output


def test_main_reports_insufficient_history(monkeypatch, capsys) -> None:
    class ShortAcquisition:
        def __init__(self, _client, _raw_root) -> None:
            pass

        def acquire(self, request, _as_of, _acquired_at) -> TefasAcquisitionResult:
            return TefasAcquisitionResult(
                _price_records(request.normalized_fund_code)[:4],
                Path("payload.json"),
                False,
            )

    monkeypatch.setattr(tefas_cli, "AcquireTefasPrices", ShortAcquisition)

    exit_code = tefas_cli.main(
        ["AAL", "--days", "12", "--end", "2026-07-20", "--as-of", "2026-07-20"]
    )

    assert exit_code == 1
    assert "at least" in capsys.readouterr().err


def _price_records(fund_code: str) -> tuple[TefasPriceRecord, ...]:
    first_date = date(2026, 7, 8)
    prices = (100.0, 101.0, 100.5, 102.0, 101.0, 103.0, 104.0, 103.0, 105.0)
    return tuple(
        TefasPriceRecord(first_date + timedelta(days=offset), fund_code, price)
        for offset, price in enumerate(prices)
    )
