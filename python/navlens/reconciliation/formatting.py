"""Deterministic text formatting for fund-return reconciliation results."""

from navlens.alignment.return_contribution_formatting import format_return_contribution_result

from .result import PointInTimeFundReturnReconciliationResult


def format_point_in_time_fund_return_reconciliation_result(
    result: PointInTimeFundReturnReconciliationResult,
) -> str:
    """Format a PointInTimeFundReturnReconciliationResult into a human-readable text report."""
    base_report = format_return_contribution_result(result.contribution)

    reconciliation = result.reconciliation_result.reconciliation
    period = result.reconciliation_result.period
    start_snap = result.start_snapshot
    end_snap = result.end_snapshot

    lines = [
        base_report,
        "",
        "Fund Return Reconciliation",
        "==========================",
        f"Exact Period: {period.period_start_date} to {period.period_end_date}",
        f"Fund Price Source ID: {result.fund_price_source_id}",
        "",
        "Start Snapshot:",
        f"  Market Date: {start_snap.observation.date}",
        f"  Unit Price: {start_snap.observation.unit_price.value:.6f}",
        f"  Available At: {start_snap.available_at.isoformat()}",
        f"  Ingested At: {start_snap.ingested_at.isoformat()}",
        "",
        "End Snapshot:",
        f"  Market Date: {end_snap.observation.date}",
        f"  Unit Price: {end_snap.observation.unit_price.value:.6f}",
        f"  Available At: {end_snap.available_at.isoformat()}",
        f"  Ingested At: {end_snap.ingested_at.isoformat()}",
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
