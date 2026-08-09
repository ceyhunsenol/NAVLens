"""Scope and provenance contracts for historical reconciliation evaluation."""

from dataclasses import dataclass
from enum import StrEnum

from .errors import InvalidHistoricalReconciliationEvaluationScopeError


class HistoricalReconciliationKind(StrEnum):
    """Classification of historical reconciliation dataset kind."""

    LEGACY = "legacy"
    FX_AWARE = "fx_aware"


@dataclass(frozen=True, slots=True)
class HistoricalReconciliationEvaluationScope:
    """Provenance and dataset scope for an evaluated historical reconciliation dataset."""

    kind: HistoricalReconciliationKind
    fund_id: str
    holdings_source_id: str
    security_price_source_id: str
    fund_price_source_id: str
    fx_source_id: str | None

    def __post_init__(self) -> None:
        """Validate scope invariants upon construction."""
        if not isinstance(self.kind, HistoricalReconciliationKind):
            raise InvalidHistoricalReconciliationEvaluationScopeError(
                f"kind must be a HistoricalReconciliationKind enum, got {type(self.kind).__name__}"
            )

        for name, value in (
            ("fund_id", self.fund_id),
            ("holdings_source_id", self.holdings_source_id),
            ("security_price_source_id", self.security_price_source_id),
            ("fund_price_source_id", self.fund_price_source_id),
        ):
            _validate_identifier(name, value)

        if self.kind == HistoricalReconciliationKind.LEGACY:
            if self.fx_source_id is not None:
                raise InvalidHistoricalReconciliationEvaluationScopeError(
                    f"fx_source_id must be None for legacy scope, got {self.fx_source_id!r}"
                )
        elif self.kind == HistoricalReconciliationKind.FX_AWARE:
            if not isinstance(self.fx_source_id, str) or not self.fx_source_id.strip():
                raise InvalidHistoricalReconciliationEvaluationScopeError(
                    "fx_source_id must be a non-empty string for FX-aware scope, "
                    f"got {self.fx_source_id!r}"
                )


def _validate_identifier(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidHistoricalReconciliationEvaluationScopeError(
            f"{name} must be a non-empty string, got {value!r}"
        )
