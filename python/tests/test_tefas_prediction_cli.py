from datetime import date, timedelta
from pathlib import Path

from navlens.prediction import tefas_cli
from navlens.sources.tefas import TefasAcquisitionResult, TefasPriceRecord


class _FakeAcquisition:
    def acquire(self, request, as_of, acquired_at):
        start = date(2026, 7, 20)
        records = tuple(
            TefasPriceRecord(
                start + timedelta(days=index),
                request.normalized_fund_code,
                1 + index * 0.01,
            )
            for index in range(14)
        )
        return TefasAcquisitionResult(records, Path("raw.json"), False)


def test_main_acquires_and_predicts_without_an_intermediate_csv(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        tefas_cli,
        "AcquireTefasPrices",
        lambda client, raw_root: _FakeAcquisition(),
    )

    exit_code = tefas_cli.main(
        [
            "AAL",
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
        ]
    )

    output = capsys.readouterr()
    assert exit_code == 0, output.err
    assert output.err == ""
    assert "Fund ID: AAL" in output.out
    assert "Source ID: tefas" in output.out
    assert "Target Date: 2026-08-13" in output.out


def test_main_atomically_writes_json_output(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(
        tefas_cli,
        "AcquireTefasPrices",
        lambda client, raw_root: _FakeAcquisition(),
    )
    output_path = tmp_path / "reports" / "aal.json"

    exit_code = tefas_cli.main(
        [
            "AAL",
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
            "json",
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""
    assert output_path.read_bytes().endswith(b"\n")
    assert b'"fund_id": "AAL"' in output_path.read_bytes()
