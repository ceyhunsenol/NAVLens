"""CSV workflow orchestration for historical FX-aware reconciliation evaluation."""

from navlens.sources import (
    read_fund_unit_prices_csv,
    read_fx_rates_csv,
    read_holdings_snapshots,
    read_security_prices_csv,
)

from .historical.evaluation import (
    HistoricalReconciliationEvaluation,
    evaluate_historical_reconciliation_dataset,
)
from .historical.fx_builder import build_historical_fx_reconciliation_dataset
from .historical.fx_schedule_csv import (
    read_historical_fx_reconciliation_requests_csv,
)
from .historical_fx_cli_args import HistoricalFxReconciliationCliArguments


def evaluate_historical_fx_reconciliation_from_csv(
    arguments: HistoricalFxReconciliationCliArguments,
) -> HistoricalReconciliationEvaluation:
    """Read CSV sources, build dataset, and evaluate historical FX reconciliation."""
    if not isinstance(arguments, HistoricalFxReconciliationCliArguments):
        target_type = type(arguments).__name__
        raise TypeError(
            "arguments must be a HistoricalFxReconciliationCliArguments instance, "
            f"got {target_type}"
        )

    requests = read_historical_fx_reconciliation_requests_csv(
        arguments.base_arguments.schedule_csv, arguments.config
    )
    holdings = read_holdings_snapshots(arguments.base_arguments.holdings_csv)
    security_prices = read_security_prices_csv(arguments.base_arguments.security_prices_csv)
    fx_rates = read_fx_rates_csv(arguments.fx_rates_csv)
    fund_prices = read_fund_unit_prices_csv(arguments.base_arguments.fund_unit_prices_csv)

    dataset = build_historical_fx_reconciliation_dataset(
        requests, holdings, security_prices, fx_rates, fund_prices
    )

    return evaluate_historical_reconciliation_dataset(dataset)
