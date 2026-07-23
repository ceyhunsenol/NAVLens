"""Deterministic text formatting for return contribution results."""

from .formatting import format_alignment_result
from .return_contribution import PointInTimeReturnContributionResult


def format_return_contribution_result(result: PointInTimeReturnContributionResult) -> str:
    """Format a PointInTimeReturnContributionResult into a human-readable text report."""
    alignment_text = format_alignment_result(result.alignment_result)

    contrib = result.contribution_result
    period = contrib.period
    obs = contrib.observed_contribution

    lines = [
        alignment_text,
        "",
        "Return Contribution Report",
        "==========================",
        f"Target Period: {period.period_start_date} to {period.period_end_date}",
        f"Price Coverage: {contrib.price_coverage:.6f}",
        f"Return Coverage: {obs.return_coverage:.6f}",
        f"Observed Contribution: {obs.observed_contribution:.6f}",
        f"Has Full Coverage: {obs.has_full_coverage}",
        "",
        "Component Contributions:",
    ]

    if contrib.component_contributions:
        for comp in contrib.component_contributions:
            lines.append(
                f"  - {comp.holding.instrument_id} "
                f"(weight: {comp.holding.fund_total_weight:.6f}, "
                f"market return: {comp.contribution.market_return:.6f}, "
                f"weighted contribution: {comp.contribution.weighted_contribution:.6f})"
            )
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("Price Gaps:")
    if contrib.price_gaps:
        for gap in contrib.price_gaps:
            lines.append(
                f"  - {gap.holding.instrument_id} "
                f"(weight: {gap.holding.fund_total_weight:.6f}, "
                f"reason: {gap.reason.kind})"
            )
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("Return Gaps:")
    if contrib.return_gaps:
        for gap in contrib.return_gaps:
            lines.append(
                f"  - {gap.holding.instrument_id} "
                f"(weight: {gap.holding.fund_total_weight:.6f}, "
                f"reason: {gap.reason.kind})"
            )
    else:
        lines.append("  (none)")

    return "\n".join(lines)
