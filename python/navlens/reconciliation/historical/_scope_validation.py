"""Private outcome-to-scope mapping and homogeneity validation."""

from typing import TypeAlias

from navlens import ReturnPeriod

from .errors import MixedHistoricalReconciliationScopeError, UnknownOutcomeError
from .fx_outcome import HistoricalFxReconciliationRecord, SkippedFxReconciliationRecord
from .outcome import HistoricalReconciliationRecord, SkippedReconciliationRecord
from .scope import HistoricalReconciliationEvaluationScope, HistoricalReconciliationKind

SupportedHistoricalOutcome: TypeAlias = (
    HistoricalReconciliationRecord
    | HistoricalFxReconciliationRecord
    | SkippedReconciliationRecord
    | SkippedFxReconciliationRecord
)


def require_supported_outcome(outcome: object) -> SupportedHistoricalOutcome:
    """Return a typed outcome or reject an unsupported runtime type."""
    if not isinstance(
        outcome,
        (
            HistoricalReconciliationRecord,
            HistoricalFxReconciliationRecord,
            SkippedReconciliationRecord,
            SkippedFxReconciliationRecord,
        ),
    ):
        raise UnknownOutcomeError(f"Unsupported outcome type: {type(outcome).__name__}")
    return outcome


def derive_outcome_scope(
    outcome: SupportedHistoricalOutcome,
    expected_kind: HistoricalReconciliationKind,
) -> HistoricalReconciliationEvaluationScope:
    """Derive typed provenance after enforcing the container's dataset kind."""
    actual_kind = _outcome_kind(outcome)
    if actual_kind != expected_kind:
        raise MixedHistoricalReconciliationScopeError(
            field_name="kind",
            expected=expected_kind.value,
            actual=actual_kind.value,
            period=outcome.request.period,
        )

    request = outcome.request
    return HistoricalReconciliationEvaluationScope(
        kind=actual_kind,
        fund_id=request.alignment_request.fund_id,
        holdings_source_id=request.alignment_request.holdings_source_id,
        security_price_source_id=request.alignment_request.security_price_source_id,
        fund_price_source_id=request.fund_price_source_id,
        fx_source_id=(
            request.fx_source_id if actual_kind == HistoricalReconciliationKind.FX_AWARE else None
        ),
    )


def validate_matching_scope(
    expected: HistoricalReconciliationEvaluationScope,
    actual: HistoricalReconciliationEvaluationScope,
    period: ReturnPeriod,
) -> None:
    """Reject the first exact scope-field mismatch in canonical field order."""
    for field_name in (
        "kind",
        "fund_id",
        "holdings_source_id",
        "security_price_source_id",
        "fund_price_source_id",
        "fx_source_id",
    ):
        expected_value = getattr(expected, field_name)
        actual_value = getattr(actual, field_name)
        if expected_value != actual_value:
            raise MixedHistoricalReconciliationScopeError(
                field_name=field_name,
                expected=_stable_value(expected_value),
                actual=_stable_value(actual_value),
                period=period,
            )


def _outcome_kind(outcome: SupportedHistoricalOutcome) -> HistoricalReconciliationKind:
    if isinstance(outcome, (HistoricalReconciliationRecord, SkippedReconciliationRecord)):
        return HistoricalReconciliationKind.LEGACY
    return HistoricalReconciliationKind.FX_AWARE


def _stable_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, HistoricalReconciliationKind):
        return value.value
    return str(value)
