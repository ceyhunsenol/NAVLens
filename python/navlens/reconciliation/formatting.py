"""Deterministic text formatting for fund-return reconciliation results."""

from navlens import FundReturnReconciliationResult
from navlens.alignment import (
    format_fx_return_contribution_result,
    format_return_contribution_result,
)
from navlens.datasets import FundUnitPriceSnapshot

from .fx_result import PointInTimeFxFundReturnReconciliationResult
from .result import PointInTimeFundReturnReconciliationResult


def format_point_in_time_fund_return_reconciliation_result(
    result: PointInTimeFundReturnReconciliationResult,
) -> str:
    """Format a PointInTimeFundReturnReconciliationResult into a human-readable text report."""
    base_report = format_return_contribution_result(result.contribution)
    return _format_full_reconciliation_report(
        base_report=base_report,
        fund_price_source_id=result.fund_price_source_id,
        start_snapshot=result.start_snapshot,
        end_snapshot=result.end_snapshot,
        reconciliation_result=result.reconciliation_result,
    )


def format_point_in_time_fx_adjusted_fund_return_reconciliation_result(
    result: PointInTimeFxFundReturnReconciliationResult,
) -> str:
    """Format a PointInTimeFxFundReturnReconciliationResult into a human-readable text report."""
    base_report = format_fx_return_contribution_result(result.contribution)
    return _format_full_reconciliation_report(
        base_report=base_report,
        fund_price_source_id=result.fund_price_source_id,
        start_snapshot=result.start_snapshot,
        end_snapshot=result.end_snapshot,
        reconciliation_result=result.reconciliation_result,
    )


def _format_full_reconciliation_report(
    *,
    base_report: str,
    fund_price_source_id: str,
    start_snapshot: FundUnitPriceSnapshot,
    end_snapshot: FundUnitPriceSnapshot,
    reconciliation_result: FundReturnReconciliationResult,
) -> str:
    reconciliation = reconciliation_result.reconciliation
    period = reconciliation_result.period

    lines = [
        base_report,
        "",
        "Fund Return Reconciliation",
        "==========================",
        f"Exact Period: {period.period_start_date} to {period.period_end_date}",
        f"Fund Price Source ID: {fund_price_source_id}",
        "",
        "Start Snapshot:",
        f"  Market Date: {start_snapshot.observation.date}",
        f"  Unit Price: {start_snapshot.observation.unit_price.value:.6f}",
        f"  Available At: {start_snapshot.available_at.isoformat()}",
        f"  Ingested At: {start_snapshot.ingested_at.isoformat()}",
        "",
        "End Snapshot:",
        f"  Market Date: {end_snapshot.observation.date}",
        f"  Unit Price: {end_snapshot.observation.unit_price.value:.6f}",
        f"  Available At: {end_snapshot.available_at.isoformat()}",
        f"  Ingested At: {end_snapshot.ingested_at.isoformat()}",
        "",
        f"Published Fund Return (Decimal): {reconciliation.published_fund_return:.6f}",
        f"Observed Portfolio Contribution (Decimal): "
        f"{reconciliation.observed_portfolio_contribution.observed_contribution:.6f}",
        f"Return Coverage (Ratio): "
        f"{reconciliation.observed_portfolio_contribution.return_coverage:.6f}",
        f"Reconciliation Residual (Decimal): {reconciliation.reconciliation_residual:.6f}",
    ]

    if not reconciliation.observed_portfolio_contribution.has_full_coverage:
        lines.extend(
            [
                "",
                "WARNING: The observed portfolio contribution is incomplete "
                "(return coverage < 1.0).",
                "The reconciliation residual includes unobserved portfolio weight and must not be",
                "interpreted as a prediction error or alpha.",
            ]
        )

    return "\n".join(lines)
