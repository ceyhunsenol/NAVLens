"""TCMB-backed workflow orchestration for historical FX reconciliation evaluation."""

from collections.abc import Callable
from datetime import UTC, date, datetime

from navlens import MarketCalendar, MarketDate, SessionKind, SessionOverride
from navlens.sources import (
    CsvSecurityPriceSource,
    read_fund_unit_prices_csv,
    read_holdings_snapshots,
)
from navlens.sources.tcmb import (
    TcmbAcquisitionContext,
    TcmbAcquisitionContextFactory,
    TcmbCachePolicy,
    TcmbFxRateSource,
    TcmbHttpClient,
    TcmbOrchestrationSnapshotLoader,
    TcmbResponseClient,
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

Clock = Callable[[], datetime]


def _system_utc_clock() -> datetime:
    return datetime.now(UTC)


def create_tcmb_acquisition_context_factory(
    calendar: MarketCalendar,
    client: TcmbResponseClient,
    clock: Clock = _system_utc_clock,
) -> TcmbAcquisitionContextFactory:
    """Create a factory that produces a fresh TcmbAcquisitionContext per market date."""

    def factory(market_date: MarketDate) -> TcmbAcquisitionContext:
        return TcmbAcquisitionContext(
            client=client,
            calendar=calendar,
            retrieved_at=clock(),
        )

    return factory


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
    calendar = _build_market_calendar(arguments.closed_dates)
    fx_rate_source = _build_tcmb_fx_rate_source(
        arguments=arguments,
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


def _build_tcmb_fx_rate_source(
    arguments: HistoricalFxTcmbCliArguments,
    calendar: MarketCalendar,
    client: TcmbResponseClient | None,
    clock: Clock,
) -> TcmbFxRateSource:
    context_factory: TcmbAcquisitionContextFactory | None = None
    if arguments.tcmb_cache_policy is not TcmbCachePolicy.cache_only:
        http_client = (
            client
            if client is not None
            else TcmbHttpClient(timeout_seconds=arguments.tcmb_http_timeout_seconds)
        )
        context_factory = create_tcmb_acquisition_context_factory(
            calendar=calendar,
            client=http_client,
            clock=clock,
        )

    loader = TcmbOrchestrationSnapshotLoader(
        root=arguments.tcmb_cache_root,
        policy=arguments.tcmb_cache_policy,
        acquisition_context_factory=context_factory,
    )
    return TcmbFxRateSource(calendar, loader)


def _build_market_calendar(closed_dates: tuple[date, ...]) -> MarketCalendar:
    overrides = [
        SessionOverride(MarketDate(value.year, value.month, value.day), SessionKind("closed"))
        for value in closed_dates
    ]
    return MarketCalendar(overrides)
