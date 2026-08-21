"""TCMB-backed workflow orchestration for historical FX reconciliation evaluation."""

from datetime import UTC, datetime

from navlens.sources import (
    CsvSecurityPriceSource,
    read_fund_unit_prices_csv,
    read_holdings_snapshots,
)
from navlens.sources.tcmb import TcmbResponseClient
from navlens.sources.tcmb.composition import (
    Clock,
    TcmbSourceSettings,
    build_tcmb_fx_rate_source,
    build_tcmb_market_calendar,
    create_tcmb_acquisition_context_factory,
)

from .historical.evaluation import (
    HistoricalReconciliationEvaluation,
    evaluate_historical_reconciliation_dataset,
)
from .historical.fx_schedule_csv import (
    read_historical_fx_reconciliation_requests_csv,
)
from .historical.fx_source_builder import (
    build_historical_fx_reconciliation_dataset_from_sources,
)
from .historical_fx_tcmb_cli_args import HistoricalFxTcmbCliArguments

__all__ = [
    "Clock",
    "create_tcmb_acquisition_context_factory",
    "evaluate_historical_fx_reconciliation_from_tcmb",
]


def _system_utc_clock() -> datetime:
    return datetime.now(UTC)


def evaluate_historical_fx_reconciliation_from_tcmb(
    arguments: HistoricalFxTcmbCliArguments,
    *,
    client: TcmbResponseClient | None = None,
    clock: Clock = _system_utc_clock,
) -> HistoricalReconciliationEvaluation:
    """Read CSV sources, construct TCMB FX source, build dataset, and evaluate."""
    if not isinstance(arguments, HistoricalFxTcmbCliArguments):
        target_type = type(arguments).__name__
        raise TypeError(
            f"arguments must be a HistoricalFxTcmbCliArguments instance, got {target_type}"
        )

    security_price_source = CsvSecurityPriceSource(
        arguments.base_arguments.security_prices_csv,
        source_id=arguments.config.base.security_price_source_id,
    )
    calendar = build_tcmb_market_calendar(arguments.closed_dates)
    settings = TcmbSourceSettings(
        cache_root=arguments.tcmb_cache_root,
        cache_policy=arguments.tcmb_cache_policy,
        http_timeout_seconds=arguments.tcmb_http_timeout_seconds,
    )
    fx_rate_source = build_tcmb_fx_rate_source(
        settings=settings,
        calendar=calendar,
        client=client,
        clock=clock,
    )

    requests = read_historical_fx_reconciliation_requests_csv(
        arguments.base_arguments.schedule_csv,
        arguments.config,
    )
    holdings = read_holdings_snapshots(arguments.base_arguments.holdings_csv)
    fund_prices = read_fund_unit_prices_csv(arguments.base_arguments.fund_unit_prices_csv)

    dataset = build_historical_fx_reconciliation_dataset_from_sources(
        requests=requests,
        holdings_snapshots=holdings,
        security_price_source=security_price_source,
        fx_rate_source=fx_rate_source,
        fund_price_snapshots=fund_prices,
        price_history_start_date=arguments.price_history_start_date,
    )

    return evaluate_historical_reconciliation_dataset(dataset)
