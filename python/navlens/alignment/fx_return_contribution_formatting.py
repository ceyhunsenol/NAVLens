"""Deterministic text formatting for FX-adjusted return contribution results."""

from .formatting import format_alignment_result
from .fx_result import PointInTimeFxAdjustedReturnContributionResult


def format_fx_return_contribution_result(
    result: PointInTimeFxAdjustedReturnContributionResult,
) -> str:
    """Format a PointInTimeFxAdjustedReturnContributionResult into a human-readable text report."""
    alignment_text = format_alignment_result(result.request.alignment_result)

    req = result.request
    align_req = req.alignment_result.request
    contrib = result.contribution_result
    period = contrib.period
    obs = contrib.observed_contribution

    lines = [
        alignment_text,
        "",
        "FX-Adjusted Return Contribution Report",
        "======================================",
        f"Target Period: {period.period_start_date} to {period.period_end_date}",
        f"Holdings Source ID: {align_req.holdings_source_id}",
        f"Security Price Source ID: {align_req.security_price_source_id}",
        f"FX Source ID: {req.fx_source_id}",
        f"Required FX Rate Kind: {req.fx_policy.required_fx_rate_kind.name}",
        f"Max FX Staleness Calendar Days: {req.fx_policy.max_fx_staleness_calendar_days}",
        f"Price Coverage: {contrib.price_coverage:.6f}",
        f"Return Coverage: {obs.return_coverage:.6f}",
        f"Observed Contribution: {obs.observed_contribution:.6f}",
        f"Has Full Coverage: {obs.has_full_coverage}",
        "",
        "Component Contributions:",
    ]

    if contrib.component_contributions:
        for comp in contrib.component_contributions:
            sec_ret = comp.security_period_return.return_decimal
            eff_ret = comp.effective_base_currency_return
            weight = comp.holding.fund_total_weight
            weighted_contrib = comp.contribution.weighted_contribution

            if comp.currency_adjustment.is_not_required:
                fx_str = "not_required"
            elif comp.currency_adjustment.is_applied:
                ev = comp.currency_adjustment.applied_evidence
                p_code = ev.required_pair.base_currency.code
                q_code = ev.required_pair.quote_currency.code
                st_d = ev.start.observation.market_date
                st_s = ev.start.staleness_calendar_days
                en_d = ev.end.observation.market_date
                en_s = ev.end.staleness_calendar_days
                fx_str = (
                    f"{ev.fx_return:.6f} ({p_code}/{q_code} {ev.required_kind.name}, "
                    f"start: {st_d} [stale: {st_s}d], end: {en_d} [stale: {en_s}d])"
                )
            else:
                fx_str = "unknown"

            lines.append(
                f"  - {comp.holding.instrument_id} "
                f"(weight: {weight:.6f}, "
                f"security return: {sec_ret:.6f}, "
                f"fx return: {fx_str}, "
                f"effective return: {eff_ret:.6f}, "
                f"weighted contribution: {weighted_contrib:.6f})"
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
            reason = gap.reason
            kind = reason.kind
            details = ""

            if kind == "missing_direct_fx_candidate":
                pair_str = (
                    f"{reason.required_pair.base_currency.code}/"
                    f"{reason.required_pair.quote_currency.code}"
                )
                details = (
                    f" (required pair: {pair_str}, required kind: {reason.required_kind.name})"
                )
            elif kind == "fx_rate_kind_mismatch":
                pair_str = (
                    f"{reason.required_pair.base_currency.code}/"
                    f"{reason.required_pair.quote_currency.code}"
                )
                avail_kinds = ", ".join(k.name for k in reason.available_kinds)
                details = (
                    f" (required pair: {pair_str}, "
                    f"required kind: {reason.required_kind.name}, "
                    f"available kinds: [{avail_kinds}])"
                )
            elif kind == "missing_fx_start_observation":
                pair_str = (
                    f"{reason.required_pair.base_currency.code}/"
                    f"{reason.required_pair.quote_currency.code}"
                )
                details = (
                    f" (required pair: {pair_str}, "
                    f"required kind: {reason.required_kind.name}, "
                    f"requested date: {reason.requested_date})"
                )
            elif kind in ("stale_fx_start_observation", "stale_fx_end_observation"):
                ev = reason.boundary_evidence
                details = (
                    f" (requested date: {ev.requested_date}, "
                    f"actual date: {ev.observation.market_date}, "
                    f"staleness: {ev.staleness_calendar_days}d, "
                    f"max allowed: {reason.maximum_staleness_calendar_days}d)"
                )

            lines.append(
                f"  - {gap.holding.instrument_id} "
                f"(weight: {gap.holding.fund_total_weight:.6f}, "
                f"reason: {kind}{details})"
            )
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("Selected FX Snapshots Provenance:")
    if result.selected_fx_snapshots:
        for snap in result.selected_fx_snapshots:
            obs_snap = snap.observation
            pair_str = f"{obs_snap.pair.base_currency.code}/{obs_snap.pair.quote_currency.code}"
            rate_val = obs_snap.rate.quote_currency_per_one_base_currency
            lines.append(
                f"  - source_id: {snap.source_id}, "
                f"pair: {pair_str}, "
                f"kind: {obs_snap.kind.name}, "
                f"market_date: {obs_snap.market_date}, "
                f"rate: {rate_val:.6f}, "
                f"available_at: {snap.available_at.isoformat()}, "
                f"ingested_at: {snap.ingested_at.isoformat()}"
            )
    else:
        lines.append("  (none)")

    return "\n".join(lines)
