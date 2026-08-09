"""Scope and homogeneity tests for historical reconciliation evaluation."""

from datetime import UTC, datetime

import pytest
from navlens import MarketDate, ReturnPeriod
from navlens.reconciliation.historical import (
    HistoricalFxReconciliationDataset,
    HistoricalReconciliationDataset,
    HistoricalReconciliationEvaluationScope,
    HistoricalReconciliationKind,
    InvalidHistoricalReconciliationEvaluationScopeError,
    MissingHoldingsSkip,
    MixedHistoricalReconciliationScopeError,
    SkippedFxReconciliationRecord,
    evaluate_historical_reconciliation_dataset,
)
from tests.historical_fx_reconciliation_fixtures import make_fx_request
from tests.historical_reconciliation_evaluation_fixtures import (
    build_two_period_fx_dataset,
    build_two_period_legacy_dataset,
    make_skipped_legacy_record,
)


def test_empty_datasets_have_no_scope() -> None:
    legacy = evaluate_historical_reconciliation_dataset(
        HistoricalReconciliationDataset(outcomes=())
    )
    fx_aware = evaluate_historical_reconciliation_dataset(
        HistoricalFxReconciliationDataset(outcomes=())
    )

    assert legacy.scope is None
    assert fx_aware.scope is None


def test_derives_legacy_scope_from_successful_outcomes() -> None:
    evaluation = evaluate_historical_reconciliation_dataset(build_two_period_legacy_dataset())

    assert evaluation.scope == HistoricalReconciliationEvaluationScope(
        kind=HistoricalReconciliationKind.LEGACY,
        fund_id="TEST_FUND",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        fund_price_source_id="src_f",
        fx_source_id=None,
    )


def test_derives_fx_scope_from_successful_outcomes() -> None:
    evaluation = evaluate_historical_reconciliation_dataset(build_two_period_fx_dataset())

    assert evaluation.scope == HistoricalReconciliationEvaluationScope(
        kind=HistoricalReconciliationKind.FX_AWARE,
        fund_id="TEST_FUND",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        fund_price_source_id="src_f",
        fx_source_id="src_fx",
    )


def test_all_skipped_dataset_still_derives_scope() -> None:
    record = make_skipped_legacy_record(MissingHoldingsSkip(), 1, 2)

    evaluation = evaluate_historical_reconciliation_dataset(
        HistoricalReconciliationDataset(outcomes=(record,))
    )

    assert evaluation.metrics is None
    assert evaluation.scope is not None
    assert evaluation.scope.fund_id == "TEST_FUND"


def test_mixed_success_and_skip_preserve_the_established_scope() -> None:
    successful = build_two_period_legacy_dataset()
    skipped = make_skipped_legacy_record(MissingHoldingsSkip(), 3, 4)
    outcomes = successful.outcomes + (skipped,)
    dataset = HistoricalReconciliationDataset(outcomes=outcomes)

    evaluation = evaluate_historical_reconciliation_dataset(dataset)

    assert evaluation.scope is not None
    assert evaluation.scope.fund_id == "TEST_FUND"
    assert dataset.outcomes == outcomes
    for expected, actual in zip(outcomes, dataset.outcomes, strict=True):
        assert expected is actual


@pytest.mark.parametrize(
    ("field_name", "override_name", "expected", "actual"),
    [
        ("fund_id", "fund_id", "TEST_FUND", "OTHER_FUND"),
        ("holdings_source_id", "holdings_source_id", "src_h", "other_h"),
        ("security_price_source_id", "security_price_source_id", "src_p", "other_p"),
        ("fund_price_source_id", "fund_price_source_id", "src_f", "other_f"),
    ],
)
def test_rejects_mixed_legacy_scope_fields(
    field_name: str,
    override_name: str,
    expected: str,
    actual: str,
) -> None:
    first = make_skipped_legacy_record(MissingHoldingsSkip(), 1, 2)
    overrides = {override_name: actual}
    second = make_skipped_legacy_record(
        MissingHoldingsSkip(),
        2,
        3,
        **overrides,  # type: ignore[arg-type]
    )

    with pytest.raises(MixedHistoricalReconciliationScopeError) as exc_info:
        evaluate_historical_reconciliation_dataset(
            HistoricalReconciliationDataset(outcomes=(first, second))
        )

    error = exc_info.value
    assert error.field_name == field_name
    assert error.expected == expected
    assert error.actual == actual
    assert error.period == second.request.period
    assert "2026-01-02 -> 2026-01-03" in str(error)


def test_rejects_mixed_fx_source_ids() -> None:
    timestamp = datetime(2026, 1, 3, 10, tzinfo=UTC)
    period_one = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    period_two = ReturnPeriod(MarketDate(2026, 1, 2), MarketDate(2026, 1, 3))
    first = SkippedFxReconciliationRecord(
        request=make_fx_request(
            MarketDate(2026, 1, 2), timestamp, period_one, fx_source_id="fx_one"
        ),
        reason=MissingHoldingsSkip(),
    )
    second = SkippedFxReconciliationRecord(
        request=make_fx_request(
            MarketDate(2026, 1, 3), timestamp, period_two, fx_source_id="fx_two"
        ),
        reason=MissingHoldingsSkip(),
    )

    with pytest.raises(MixedHistoricalReconciliationScopeError) as exc_info:
        evaluate_historical_reconciliation_dataset(
            HistoricalFxReconciliationDataset(outcomes=(first, second))
        )

    assert exc_info.value.field_name == "fx_source_id"
    assert exc_info.value.expected == "fx_one"
    assert exc_info.value.actual == "fx_two"


def test_rejects_legacy_outcome_in_fx_dataset() -> None:
    legacy = make_skipped_legacy_record(MissingHoldingsSkip(), 1, 2)
    dataset = HistoricalFxReconciliationDataset(
        outcomes=(legacy,)  # type: ignore[arg-type]
    )

    with pytest.raises(MixedHistoricalReconciliationScopeError) as exc_info:
        evaluate_historical_reconciliation_dataset(dataset)

    assert exc_info.value.field_name == "kind"
    assert exc_info.value.expected == "fx_aware"
    assert exc_info.value.actual == "legacy"


def test_rejects_fx_outcome_in_legacy_dataset() -> None:
    timestamp = datetime(2026, 1, 2, 10, tzinfo=UTC)
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    fx_aware = SkippedFxReconciliationRecord(
        request=make_fx_request(MarketDate(2026, 1, 2), timestamp, period),
        reason=MissingHoldingsSkip(),
    )
    dataset = HistoricalReconciliationDataset(
        outcomes=(fx_aware,)  # type: ignore[arg-type]
    )

    with pytest.raises(MixedHistoricalReconciliationScopeError) as exc_info:
        evaluate_historical_reconciliation_dataset(dataset)

    assert exc_info.value.field_name == "kind"
    assert exc_info.value.expected == "legacy"
    assert exc_info.value.actual == "fx_aware"


def test_periods_and_prediction_timestamps_may_differ() -> None:
    evaluation = evaluate_historical_reconciliation_dataset(build_two_period_legacy_dataset())

    assert evaluation.evaluated_period_count == 2
    assert evaluation.scope is not None


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("fund_id", " "),
        ("holdings_source_id", ""),
        ("security_price_source_id", None),
        ("fund_price_source_id", 1),
    ],
)
def test_scope_rejects_invalid_identifiers(field_name: str, value: object) -> None:
    arguments: dict[str, object] = {
        "kind": HistoricalReconciliationKind.LEGACY,
        "fund_id": "TEST_FUND",
        "holdings_source_id": "src_h",
        "security_price_source_id": "src_p",
        "fund_price_source_id": "src_f",
        "fx_source_id": None,
    }
    arguments[field_name] = value

    with pytest.raises(
        InvalidHistoricalReconciliationEvaluationScopeError,
        match=f"{field_name} must be a non-empty string",
    ):
        HistoricalReconciliationEvaluationScope(**arguments)  # type: ignore[arg-type]


def test_scope_rejects_invalid_kind_and_fx_source_relationships() -> None:
    base = {
        "fund_id": "TEST_FUND",
        "holdings_source_id": "src_h",
        "security_price_source_id": "src_p",
        "fund_price_source_id": "src_f",
    }
    with pytest.raises(InvalidHistoricalReconciliationEvaluationScopeError, match="kind must be"):
        HistoricalReconciliationEvaluationScope(
            kind="legacy",  # type: ignore[arg-type]
            fx_source_id=None,
            **base,
        )
    with pytest.raises(
        InvalidHistoricalReconciliationEvaluationScopeError,
        match="fx_source_id must be None for legacy scope",
    ):
        HistoricalReconciliationEvaluationScope(
            kind=HistoricalReconciliationKind.LEGACY,
            fx_source_id="src_fx",
            **base,
        )


@pytest.mark.parametrize("fx_source_id", [None, " ", 1])
def test_fx_scope_rejects_invalid_fx_source_id(fx_source_id: object) -> None:
    with pytest.raises(
        InvalidHistoricalReconciliationEvaluationScopeError,
        match="fx_source_id must be a non-empty string for FX-aware scope",
    ):
        HistoricalReconciliationEvaluationScope(
            kind=HistoricalReconciliationKind.FX_AWARE,
            fund_id="TEST_FUND",
            holdings_source_id="src_h",
            security_price_source_id="src_p",
            fund_price_source_id="src_f",
            fx_source_id=fx_source_id,  # type: ignore[arg-type]
        )


def test_scope_validation_does_not_normalize_identifiers() -> None:
    scope = HistoricalReconciliationEvaluationScope(
        kind=HistoricalReconciliationKind.LEGACY,
        fund_id=" TEST_FUND ",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        fund_price_source_id="src_f",
        fx_source_id=None,
    )

    assert scope.fund_id == " TEST_FUND "
