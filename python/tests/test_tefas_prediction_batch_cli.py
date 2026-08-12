import json
from datetime import date, timedelta
from pathlib import Path

from navlens.prediction import tefas_batch_cli
from navlens.sources.tefas import (
    TefasAcquisitionResult,
    TefasPriceRecord,
    TefasTransportError,
)


class _FakeAcquisition:
    def acquire(self, request, as_of, acquired_at):
        if request.normalized_fund_code == "BAD":
            raise TefasTransportError("provider unavailable")
        records = tuple(
            TefasPriceRecord(
                date(2026, 7, 20) + timedelta(days=index),
                request.normalized_fund_code,
                1 + index * 0.01,
            )
            for index in range(14)
        )
        return TefasAcquisitionResult(records, Path("raw.json"), False)


def test_batch_continues_after_one_fund_fails(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        tefas_batch_cli,
        "AcquireTefasPrices",
        lambda client, raw_root: _FakeAcquisition(),
    )

    exit_code = tefas_batch_cli.main(_arguments("text"))

    output = capsys.readouterr()
    assert exit_code == 2
    assert "batch_total=2" in output.out
    assert "AAL,success" in output.out
    assert "BAD,failure" in output.out
    assert "TefasTransportError" in output.out


def test_batch_json_uses_versioned_schema(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        tefas_batch_cli,
        "AcquireTefasPrices",
        lambda client, raw_root: _FakeAcquisition(),
    )

    exit_code = tefas_batch_cli.main(_arguments("json"))

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["schema_version"] == "navlens-tefas-prediction-batch-v1"
    assert payload["total_count"] == 2
    assert payload["successes"][0]["fund_id"] == "AAL"
    assert payload["failures"][0]["fund_id"] == "BAD"


def test_batch_writes_json_output_file(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(
        tefas_batch_cli,
        "AcquireTefasPrices",
        lambda client, raw_root: _FakeAcquisition(),
    )
    output_path = tmp_path / "batch.json"

    exit_code = tefas_batch_cli.main([*_arguments("json"), "--output", str(output_path)])

    captured = capsys.readouterr()
    payload = json.loads(output_path.read_bytes())
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == ""
    assert payload["total_count"] == 2


def _arguments(output_format: str) -> list[str]:
    return [
        "AAL",
        "BAD",
        "--end",
        "2026-08-02",
        "--as-of",
        "2026-08-12",
        "--days",
        "14",
        "--target-date",
        "2026-08-13",
        "--max-price-age-days",
        "10",
        "--output-format",
        output_format,
    ]
