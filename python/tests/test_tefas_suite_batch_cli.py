import json
from pathlib import Path

from navlens.prediction.options import PredictionModelKind
from navlens.prediction.tefas_suite_batch_cli import main
from tefas_prediction_fixtures import make_tefas_prediction_acquisition


def test_cli_all_funds_succeed_exit_code_zero(monkeypatch, tmp_path: Path) -> None:
    def _fake_acquire(self, request, _as_of, _acquired_at):
        return make_tefas_prediction_acquisition(request.normalized_fund_code)

    monkeypatch.setattr("navlens.sources.tefas.AcquireTefasPrices.acquire", _fake_acquire)

    output = tmp_path / "suite-batch.json"
    exit_code = main(
        [
            "AAL",
            "PHE",
            "--as-of",
            "2026-08-02",
            "--end",
            "2026-08-02",
            "--days",
            "14",
            "--auto-target-date",
            "--output-format",
            "json",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_bytes())
    assert payload["schema_version"] == "navlens-tefas-prediction-model-suite-batch-v1"
    assert payload["succeeded_count"] == 2
    assert payload["failed_count"] == 0
    assert len(payload["successes"]) == 2
    for success in payload["successes"]:
        assert len(success["predictions"]) == len(PredictionModelKind)


def test_cli_partial_success_exit_code_two(monkeypatch, tmp_path: Path) -> None:
    def _fake_acquire(self, request, _as_of, _acquired_at):
        fund = request.normalized_fund_code
        if fund == "BAD":
            raise ValueError("bad fund code")
        return make_tefas_prediction_acquisition(fund)

    monkeypatch.setattr("navlens.sources.tefas.AcquireTefasPrices.acquire", _fake_acquire)

    output = tmp_path / "suite-batch.json"
    exit_code = main(
        [
            "AAL",
            "BAD",
            "--as-of",
            "2026-08-02",
            "--end",
            "2026-08-02",
            "--days",
            "14",
            "--auto-target-date",
            "--output-format",
            "json",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 2
    payload = json.loads(output.read_bytes())
    assert payload["succeeded_count"] == 1
    assert payload["failed_count"] == 1


def test_cli_all_funds_fail_exit_code_one(monkeypatch, tmp_path: Path) -> None:
    def _fail_acquire(self, request, _as_of, _acquired_at):
        raise ValueError(f"cannot acquire {request.normalized_fund_code}")

    monkeypatch.setattr("navlens.sources.tefas.AcquireTefasPrices.acquire", _fail_acquire)
    output = tmp_path / "suite-batch.json"

    exit_code = main(
        [
            "AAL",
            "PHE",
            "--as-of",
            "2026-08-02",
            "--end",
            "2026-08-02",
            "--days",
            "14",
            "--auto-target-date",
            "--output-format",
            "json",
            "--output",
            str(output),
        ]
    )

    payload = json.loads(output.read_bytes())
    assert exit_code == 1
    assert payload["succeeded_count"] == 0
    assert payload["failed_count"] == 2


def test_cli_refuses_overwrite_existing_file(monkeypatch, capsys, tmp_path: Path) -> None:
    def _fake_acquire(self, request, _as_of, _acquired_at):
        return make_tefas_prediction_acquisition(request.normalized_fund_code)

    monkeypatch.setattr("navlens.sources.tefas.AcquireTefasPrices.acquire", _fake_acquire)
    output = tmp_path / "existing.json"
    output.write_text("existing", encoding="utf-8")

    exit_code = main(
        [
            "AAL",
            "--as-of",
            "2026-08-02",
            "--end",
            "2026-08-02",
            "--days",
            "14",
            "--auto-target-date",
            "--output",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "error:" in captured.err
    assert output.read_text(encoding="utf-8") == "existing"
