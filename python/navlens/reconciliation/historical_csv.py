"""CSV workflow orchestration for historical fund-return reconciliation dataset evaluation."""

from navlens.sources import (
    read_fund_unit_prices_csv,
    read_holdings_snapshots,
    read_security_prices_csv,
)

from .historical.builder import build_historical_reconciliation_dataset
from .historical.evaluation import (
    HistoricalReconciliationEvaluation,
    evaluate_historical_reconciliation_dataset,
)
from .historical.schedule_csv import read_historical_reconciliation_requests_csv
from .historical_cli_args import HistoricalReconciliationCliArguments


def evaluate_historical_reconciliation_from_csv(
    arguments: HistoricalReconciliationCliArguments,
) -> HistoricalReconciliationEvaluation:
    """Read CSV sources, build dataset, and evaluate historical reconciliation."""
    if not isinstance(arguments, HistoricalReconciliationCliArguments):
        target_type = type(arguments).__name__
        raise TypeError(
            f"arguments must be a HistoricalReconciliationCliArguments instance, got {target_type}"
        )

    requests = read_historical_reconciliation_requests_csv(arguments.schedule_csv, arguments.config)
    holdings = read_holdings_snapshots(arguments.holdings_csv)
    security_prices = read_security_prices_csv(arguments.security_prices_csv)
    fund_prices = read_fund_unit_prices_csv(arguments.fund_unit_prices_csv)

    dataset = build_historical_reconciliation_dataset(
        requests, holdings, security_prices, fund_prices
    )

    return evaluate_historical_reconciliation_dataset(dataset)
