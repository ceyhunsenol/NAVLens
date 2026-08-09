"""Tests for historical reconciliation evaluation output writer."""

import io

import pytest
from navlens.reconciliation.historical import (
    evaluate_historical_reconciliation_dataset,
    format_historical_reconciliation_evaluation,
    serialize_historical_reconciliation_evaluation,
)
from navlens.reconciliation.historical_cli_output import (
    write_historical_reconciliation_evaluation,
)
from tests.historical_reconciliation_evaluation_fixtures import (
    build_two_period_legacy_dataset,
)


def test_write_output_text_format() -> None:
    eval_obj = evaluate_historical_reconciliation_dataset(build_two_period_legacy_dataset())
    text_stream = io.StringIO()
    binary_stream = io.BytesIO()

    write_historical_reconciliation_evaluation(
        eval_obj,
        "text",
        text_stream=text_stream,
        binary_stream=binary_stream,
    )

    expected_text = format_historical_reconciliation_evaluation(eval_obj) + "\n"
    assert text_stream.getvalue() == expected_text
    assert binary_stream.getvalue() == b""


def test_write_output_json_format() -> None:
    eval_obj = evaluate_historical_reconciliation_dataset(build_two_period_legacy_dataset())
    text_stream = io.StringIO()
    binary_stream = io.BytesIO()

    write_historical_reconciliation_evaluation(
        eval_obj,
        "json",
        text_stream=text_stream,
        binary_stream=binary_stream,
    )

    expected_bytes = serialize_historical_reconciliation_evaluation(eval_obj)
    assert binary_stream.getvalue() == expected_bytes
    assert text_stream.getvalue() == ""


def test_write_output_rejects_unsupported_format() -> None:
    eval_obj = evaluate_historical_reconciliation_dataset(build_two_period_legacy_dataset())
    text_stream = io.StringIO()
    binary_stream = io.BytesIO()

    with pytest.raises(ValueError, match="unsupported output format: 'xml'"):
        write_historical_reconciliation_evaluation(
            eval_obj,
            "xml",
            text_stream=text_stream,
            binary_stream=binary_stream,
        )
