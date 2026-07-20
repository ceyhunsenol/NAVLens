from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from navlens.evaluation import LinearBaselineWalkForward
from navlens.evaluation.manifests import build_tefas_run_manifest, store_run_manifest
from navlens.evaluation.tefas_backtest import evaluate_tefas_acquisition
from navlens.evaluation.tefas_batch import (
    BatchFundFailure,
    BatchFundSuccess,
    TefasBatchResult,
    batch_exit_code,
    run_tefas_batch,
)
from navlens.evaluation.tefas_batch_output import format_tefas_batch_result
from navlens.evaluation.tefas_execution import CompletedTefasBacktest
from navlens.sources.tefas import (
    TefasAcquisitionResult,
    TefasPriceRecord,
    TefasPriceRequest,
    TefasTransportError,
)
from navlens.sources.tefas.cli_arguments import TefasCliArguments


class RecordingExecutor:
    def __init__(self, completed: CompletedTefasBacktest) -> None:
        self.completed = completed
        self.calls: list[str] = []

    def execute(self, arguments: TefasCliArguments) -> CompletedTefasBacktest:
        fund_code = arguments.request.normalized_fund_code
        self.calls.append(fund_code)
        if fund_code == "BAD":
            raise TefasTransportError("provider unavailable")
        return self.completed


def test_continues_after_expected_fund_failure(tmp_path: Path) -> None:
    executor = RecordingExecutor(_completed_backtest(tmp_path))

    result = run_tefas_batch(
        (_arguments("AAL", tmp_path), _arguments("BAD", tmp_path)),
        executor,
    )

    assert executor.calls == ["AAL", "BAD"]
    assert [item.fund_code for item in result.successes] == ["AAL"]
    assert [item.fund_code for item in result.failures] == ["BAD"]
    assert result.failures[0].error_type == "TefasTransportError"
    assert batch_exit_code(result) == 2


def test_formats_model_rows_and_csv_safe_failures(tmp_path: Path) -> None:
    completed = _completed_backtest(tmp_path)
    result = TefasBatchResult(
        successes=(BatchFundSuccess("AAL", completed),),
        failures=(BatchFundFailure("BAD", "ValueError", "bad, payload"),),
    )

    output = format_tefas_batch_result(result)

    assert "batch_total=2" in output
    assert "batch_succeeded=1" in output
    assert output.count("AAL,success") == 3
    assert 'BAD,failure,,,,,,,ValueError,"bad, payload"' in output


def test_rejects_empty_batch() -> None:
    with pytest.raises(ValueError, match="at least one fund"):
        run_tefas_batch((), RecordingExecutor.__new__(RecordingExecutor))


def test_exit_codes_distinguish_complete_success_and_failure() -> None:
    failure = BatchFundFailure("BAD", "ValueError", "invalid")

    assert batch_exit_code(TefasBatchResult((), (failure,))) == 1


def _arguments(fund_code: str, root: Path) -> TefasCliArguments:
    request = TefasPriceRequest(fund_code, date(2026, 7, 8), date(2026, 7, 20))
    return TefasCliArguments(request, date(2026, 7, 20), root)


def _completed_backtest(tmp_path: Path) -> CompletedTefasBacktest:
    source_path = tmp_path / "payload.json"
    source_path.write_text('{"data": []}', encoding="utf-8")
    acquisition = TefasAcquisitionResult(_price_records(), source_path, True)
    estimator = LinearBaselineWalkForward(lookback=2, model_version="0.1.0")
    result = evaluate_tefas_acquisition(acquisition, estimator)
    request = TefasPriceRequest("AAL", date(2026, 7, 8), date(2026, 7, 20))
    manifest = build_tefas_run_manifest(
        result,
        request,
        date(2026, 7, 20),
        datetime(2026, 7, 20, 12, 30, tzinfo=UTC),
    )
    stored = store_run_manifest(manifest, tmp_path / "runs")
    return CompletedTefasBacktest(result, stored)


def _price_records() -> tuple[TefasPriceRecord, ...]:
    first_date = date(2026, 7, 8)
    prices = (100.0, 101.0, 100.5, 102.0, 101.0, 103.0, 104.0, 103.0, 105.0)
    return tuple(
        TefasPriceRecord(first_date + timedelta(days=offset), "AAL", price)
        for offset, price in enumerate(prices)
    )
