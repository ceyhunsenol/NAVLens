import json
from pathlib import Path

from navlens.prediction.live_history_comparison_batch_cli import main
from prediction_artifact_fixtures import (
    evaluation_artifact_payload,
    write_evaluation_batch_artifact,
)


def test_cli_all_scopes_succeed_returns_exit_code_zero(capsys, tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge"),
            evaluation_artifact_payload(fund_id="AAL", model_name="linear"),
        ],
    )
    output = tmp_path / "output.json"

    exit_code = main([str(day1), "--output-format", "json", "--output", str(output)])

    captured = capsys.readouterr()
    payload = json.loads(output.read_bytes())
    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""
    assert payload["schema_version"] == "navlens-live-prediction-history-comparison-batch-v1"
    assert payload["succeeded_count"] == 1
    assert payload["failed_count"] == 0
    assert payload["outcomes"][0]["status"] == "success"
    assert payload["outcomes"][0]["fund_id"] == "AAL"


def test_cli_partial_success_returns_exit_code_two(capsys, tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge"),
            evaluation_artifact_payload(fund_id="AAL", model_name="linear"),
            evaluation_artifact_payload(fund_id="YAK", model_name="ridge"),  # 1 model -> fails
        ],
    )
    output = tmp_path / "output.json"

    exit_code = main([str(day1), "--output-format", "json", "--output", str(output)])

    captured = capsys.readouterr()
    payload = json.loads(output.read_bytes())
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == ""
    assert payload["total_count"] == 2
    assert payload["succeeded_count"] == 1
    assert payload["failed_count"] == 1
    assert [o["status"] for o in payload["outcomes"]] == ["success", "failure"]
    assert payload["outcomes"][1]["reason_code"] == "invalid_comparison"


def test_cli_all_scopes_fail_returns_exit_code_one(capsys, tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge"),  # 1 model -> fails
            evaluation_artifact_payload(fund_id="YAK", model_name="linear"),  # 1 model -> fails
        ],
    )
    output = tmp_path / "output.json"

    exit_code = main([str(day1), "--output-format", "json", "--output", str(output)])

    captured = capsys.readouterr()
    payload = json.loads(output.read_bytes())
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == ""
    assert payload["succeeded_count"] == 0
    assert payload["failed_count"] == 2


def test_cli_global_input_failure_returns_exit_code_one(capsys, tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("not json", encoding="utf-8")

    exit_code = main([str(corrupt)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "error:" in captured.err


def test_cli_text_output_format(capsys, tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge"),
            evaluation_artifact_payload(fund_id="AAL", model_name="linear"),
        ],
    )

    exit_code = main([str(day1), "--output-format", "text"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "batch_total=1" in captured.out
    assert "batch_succeeded=1" in captured.out
    assert "--- Scope AAL:tefas [success] ---" in captured.out


def test_cli_refuses_to_overwrite_existing_output(capsys, tmp_path: Path) -> None:
    day1 = write_evaluation_batch_artifact(
        tmp_path / "day1.json",
        [
            evaluation_artifact_payload(fund_id="AAL", model_name="ridge"),
            evaluation_artifact_payload(fund_id="AAL", model_name="linear"),
        ],
    )
    output = tmp_path / "output.json"
    arguments = [str(day1), "--output-format", "json", "--output", str(output)]

    assert main(arguments) == 0
    original_bytes = output.read_bytes()
    assert main(arguments) == 1

    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert output.read_bytes() == original_bytes
