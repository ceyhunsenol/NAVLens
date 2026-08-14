from datetime import UTC, date, datetime
from pathlib import Path

from navlens import MarketDate
from navlens.prediction.freshness import FundUnitPriceFreshnessPolicy
from navlens.prediction.model_suite import PredictionModelSuiteOptions
from navlens.prediction.options import PredictionModelKind
from navlens.prediction.tefas_suite_batch_execution import ExecuteTefasPredictionSuite
from navlens.sources.tefas import TefasAcquisitionResult, TefasPriceRequest, TefasTransportError
from navlens.sources.tefas.batch import run_tefas_batch
from navlens.sources.tefas.cli_arguments import TefasCliArguments
from tefas_prediction_fixtures import make_tefas_prediction_acquisition


def _arguments(fund_code: str, tmp_path: Path) -> TefasCliArguments:
    request = TefasPriceRequest(fund_code, date(2026, 7, 8), date(2026, 8, 2))
    return TefasCliArguments(request, date(2026, 8, 2), tmp_path)


class FakeAcquisitionClient:
    def __init__(self) -> None:
        self.acquired_funds: list[str] = []
        self.acquired_timestamps: list[datetime] = []

    def acquire(self, request, as_of: date, acquired_at: datetime) -> TefasAcquisitionResult:
        fund = request.normalized_fund_code
        self.acquired_funds.append(fund)
        self.acquired_timestamps.append(acquired_at)
        if fund == "BAD":
            raise TefasTransportError("provider unavailable")
        return make_tefas_prediction_acquisition(fund)


def test_executes_suite_batch_with_shared_timestamp_and_single_acquisition(
    tmp_path: Path,
) -> None:
    client = FakeAcquisitionClient()
    acquired_at = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
    executor = ExecuteTefasPredictionSuite(
        client,  # type: ignore[arg-type]
        acquired_at,
        MarketDate(2026, 8, 2),
        MarketDate(2026, 8, 3),
        PredictionModelSuiteOptions(),
        FundUnitPriceFreshnessPolicy(),
    )

    assert hasattr(executor, "execute")
    assert callable(executor.execute)

    args_aal = _arguments("AAL", tmp_path)
    args_phe = _arguments("PHE", tmp_path)

    result = run_tefas_batch((args_aal, args_phe), executor)

    assert client.acquired_funds == ["AAL", "PHE"]
    assert client.acquired_timestamps == [acquired_at, acquired_at]
    assert len(result.successes) == 2
    assert len(result.failures) == 0
    for success in result.successes:
        assert len(success.completed.predictions) == len(PredictionModelKind)
        first = success.completed.predictions[0]
        assert all(
            item.prediction_timestamp == acquired_at for item in success.completed.predictions
        )
        assert all(
            item.selected_snapshots == first.selected_snapshots
            for item in success.completed.predictions
        )


def test_isolates_per_fund_failure_without_dropping_other_suites(
    tmp_path: Path,
) -> None:
    client = FakeAcquisitionClient()
    acquired_at = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
    executor = ExecuteTefasPredictionSuite(
        client,  # type: ignore[arg-type]
        acquired_at,
        MarketDate(2026, 8, 2),
        MarketDate(2026, 8, 3),
        PredictionModelSuiteOptions(),
        FundUnitPriceFreshnessPolicy(),
    )

    args_aal = _arguments("AAL", tmp_path)
    args_bad = _arguments("BAD", tmp_path)

    result = run_tefas_batch((args_aal, args_bad), executor)

    assert len(result.successes) == 1
    assert result.successes[0].fund_code == "AAL"
    assert len(result.failures) == 1
    assert result.failures[0].fund_code == "BAD"
    assert result.failures[0].error_type == "TefasTransportError"
