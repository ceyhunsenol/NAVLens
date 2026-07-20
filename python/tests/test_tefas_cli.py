from datetime import date
from pathlib import Path

import pytest
from navlens.sources.tefas import cli
from navlens.sources.tefas.acquisition import TefasAcquisitionResult
from navlens.sources.tefas.cli_arguments import parse_cli_arguments
from navlens.sources.tefas.cli_output import format_acquisition_result
from navlens.sources.tefas.errors import TefasTransportError
from navlens.sources.tefas.records import TefasPriceRecord


def test_defaults_to_thirty_calendar_days() -> None:
    arguments = parse_cli_arguments(["aal"], today=date(2026, 7, 20))

    assert arguments.request.fund_code == "aal"
    assert arguments.request.start_date == date(2026, 6, 21)
    assert arguments.request.end_date == date(2026, 7, 20)
    assert arguments.as_of == date(2026, 7, 20)
    assert arguments.raw_root == Path("data/raw/tefas")


def test_accepts_explicit_interval_and_storage_root(tmp_path) -> None:
    arguments = parse_cli_arguments(
        [
            "AAL",
            "--start",
            "2026-07-01",
            "--end",
            "2026-07-18",
            "--as-of",
            "2026-07-20",
            "--raw-root",
            str(tmp_path),
        ],
        today=date(2026, 7, 20),
    )

    assert arguments.request.start_date == date(2026, 7, 1)
    assert arguments.request.end_date == date(2026, 7, 18)
    assert arguments.raw_root == tmp_path


def test_rejects_future_end_date() -> None:
    with pytest.raises(SystemExit) as exit_info:
        parse_cli_arguments(
            ["AAL", "--end", "2026-07-21", "--as-of", "2026-07-20"],
            today=date(2026, 7, 20),
        )

    assert exit_info.value.code == 2


def test_formats_metadata_and_price_rows() -> None:
    arguments = parse_cli_arguments(["AAL", "--days", "1"], today=date(2026, 7, 20))
    result = TefasAcquisitionResult(
        records=(TefasPriceRecord(date(2026, 7, 20), "AAL", 1.25),),
        payload_path=Path("data/raw/tefas/payload.json"),
        from_cache=True,
    )

    output = format_acquisition_result(result, arguments.request)

    assert "fund=AAL" in output
    assert "records=1" in output
    assert "cache=hit" in output
    assert output.endswith("2026-07-20,1.25")


def test_main_prints_acquired_records(monkeypatch, capsys, tmp_path) -> None:
    class FakeAcquisition:
        def __init__(self, _client, raw_root) -> None:
            assert raw_root == tmp_path

        def acquire(self, request, _as_of, acquired_at) -> TefasAcquisitionResult:
            assert acquired_at.utcoffset() is not None
            record = TefasPriceRecord(request.end_date, request.normalized_fund_code, 1.25)
            return TefasAcquisitionResult((record,), tmp_path / "payload.json", False)

    monkeypatch.setattr(cli, "AcquireTefasPrices", FakeAcquisition)

    exit_code = cli.main(
        [
            "AAL",
            "--days",
            "1",
            "--end",
            "2026-07-20",
            "--as-of",
            "2026-07-20",
            "--raw-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert "cache=miss" in capsys.readouterr().out


def test_main_reports_source_failure(monkeypatch, capsys) -> None:
    class FailingAcquisition:
        def __init__(self, _client, _raw_root) -> None:
            pass

        def acquire(self, _request, _as_of, _acquired_at):
            raise TefasTransportError("provider unavailable")

    monkeypatch.setattr(cli, "AcquireTefasPrices", FailingAcquisition)

    exit_code = cli.main(["AAL", "--days", "1", "--end", "2026-07-20", "--as-of", "2026-07-20"])

    assert exit_code == 1
    assert capsys.readouterr().err == "error: provider unavailable\n"
