"""Deterministic text formatting for point-in-time alignment results."""

from .result import PointInTimeAlignmentResult


def format_alignment_result(result: PointInTimeAlignmentResult) -> str:
    """Format a PointInTimeAlignmentResult into a human-readable text report."""
    req = result.request
    hs = result.holdings_snapshot
    rep = result.report

    lines = [
        "Point-in-Time Alignment Report",
        "=============================",
        f"Fund ID: {req.fund_id}",
        f"Prediction Timestamp: {req.prediction_timestamp.isoformat()}",
        "",
        "Selected Holdings Snapshot Provenance:",
        f"  Effective Date: {hs.effective_date}",
        f"  Published At: {hs.published_at.isoformat()}",
        f"  Ingested At: {hs.ingested_at.isoformat()}",
        f"  Source ID: {hs.source_id}",
        "",
        f"Selected Price Snapshots Count: {len(result.selected_price_snapshots)}",
        "",
        "Coverage Weights:",
        f"  Declared Weight: {rep.declared_weight:.6f}",
        f"  Covered Weight: {rep.covered_weight:.6f}",
        f"  Uncovered Listed Weight: {rep.uncovered_listed_weight:.6f}",
        f"  Unrepresented Weight: {rep.unrepresented_weight:.6f}",
        f"  Total Uncovered Weight: {rep.total_uncovered_weight:.6f}",
        f"  Coverage Ratio: {rep.coverage_ratio:.6f}",
        "",
        "Covered Holdings:",
    ]

    if rep.covered:
        for item in rep.covered:
            lines.append(f"  - {item.holding.instrument_id}")
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("Uncovered Holdings:")
    if rep.uncovered_listed:
        for item in rep.uncovered_listed:
            lines.append(
                f"  - {item.holding.instrument_id} (weight: {item.holding.fund_total_weight:.6f}, "
                f"reason: {item.reason.kind})"
            )
    else:
        lines.append("  (none)")

    return "\n".join(lines)
