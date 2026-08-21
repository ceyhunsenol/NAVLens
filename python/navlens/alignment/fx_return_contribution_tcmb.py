"""TCMB-backed workflow orchestration for FX-adjusted point-in-time return contribution."""

from datetime import UTC, datetime

from navlens.sources import CsvSecurityPriceSource, read_holdings_snapshots
from navlens.sources.tcmb import TCMB_SOURCE_ID, TcmbResponseClient
from navlens.sources.tcmb.composition import (
    Clock,
    build_tcmb_fx_rate_source,
    build_tcmb_market_calendar,
)

from .fx_orchestration import (
    calculate_point_in_time_fx_adjusted_return_contribution_from_source,
)
from .fx_request import PointInTimeFxReturnContributionRequest
from .fx_result import PointInTimeFxAdjustedReturnContributionResult
from .fx_return_contribution_tcmb_cli_args import FxReturnContributionTcmbCliArguments
from .point_in_time import align_point_in_time_from_source


def _system_utc_clock() -> datetime:
    return datetime.now(UTC)


def calculate_fx_return_contribution_from_tcmb(
    arguments: FxReturnContributionTcmbCliArguments,
    *,
    client: TcmbResponseClient | None = None,
    clock: Clock = _system_utc_clock,
) -> PointInTimeFxAdjustedReturnContributionResult:
    """Calculate point-in-time FX-adjusted return contribution from provider-neutral sources."""
    if not isinstance(arguments, FxReturnContributionTcmbCliArguments):
        target_type = type(arguments).__name__
        raise TypeError(
            f"arguments must be an FxReturnContributionTcmbCliArguments instance, got {target_type}"
        )

    align_args = arguments.alignment_args
    holdings = read_holdings_snapshots(align_args.holdings_csv)
    security_price_source = CsvSecurityPriceSource(
        align_args.security_prices_csv,
        source_id=align_args.request.security_price_source_id,
    )

    alignment_result = align_point_in_time_from_source(
        align_args.request,
        holdings,
        security_price_source,
        arguments.price_history_start_date,
    )

    calendar = build_tcmb_market_calendar(arguments.closed_dates)
    fx_rate_source = build_tcmb_fx_rate_source(
        settings=arguments.tcmb_source_settings,
        calendar=calendar,
        client=client,
        clock=clock,
    )

    fx_request = PointInTimeFxReturnContributionRequest(
        alignment_result=alignment_result,
        target_period=arguments.target_period,
        fx_source_id=TCMB_SOURCE_ID,
        fx_policy=arguments.fx_policy,
    )

    return calculate_point_in_time_fx_adjusted_return_contribution_from_source(
        fx_request,
        fx_rate_source,
    )
