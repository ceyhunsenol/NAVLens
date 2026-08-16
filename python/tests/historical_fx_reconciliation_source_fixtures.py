"""Domain fixtures and helpers for source-backed historical FX reconciliation tests."""

from datetime import datetime

from navlens import (
    AlignmentPolicy,
    CurrencyCode,
    CurrencyPair,
    FxRate,
    FxRateKind,
    FxRateObservation,
    FxReturnPolicy,
    MarketDate,
    PriceAdjustment,
    PriceCurrencyPolicy,
    ReturnPeriod,
)
from navlens.alignment import PointInTimeAlignmentRequest
from navlens.datasets import FxRateSnapshot
from navlens.reconciliation.historical import HistoricalFxReconciliationRequest
from tests.historical_reconciliation_source_fixtures import (
    FakeRecordingSecurityPriceSource,
    make_cash_position,
    make_deposit_position,
    make_derivative_position,
    make_equity_position,
    make_etf_position,
    make_fund_unit_price_snapshot,
    make_holding_snapshot,
    make_repo_position,
    make_security_price_snapshot,
    make_utc_timestamp,
)

__all__ = [
    "FakeRecordingSecurityPriceSource",
    "make_cash_position",
    "make_deposit_position",
    "make_derivative_position",
    "make_equity_position",
    "make_etf_position",
    "make_fund_unit_price_snapshot",
    "make_fx_alignment_policy",
    "make_fx_alignment_request",
    "make_fx_historical_request",
    "make_fx_rate_snapshot",
    "make_holding_snapshot",
    "make_repo_position",
    "make_security_price_snapshot",
    "make_utc_timestamp",
]


def make_fx_alignment_policy(
    pricing_as_of_date: MarketDate,
    *,
    fund_base_currency: str = "TRY",
    adjustment: str = "unadjusted",
    minimum_observations: int = 2,
    max_staleness_calendar_days: int = 5,
) -> AlignmentPolicy:
    return AlignmentPolicy(
        CurrencyCode(fund_base_currency),
        PriceAdjustment(adjustment),
        pricing_as_of_date,
        minimum_observations,
        max_staleness_calendar_days,
    ).with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))


def make_fx_alignment_request(
    pricing_as_of_date: MarketDate,
    prediction_timestamp: datetime,
    *,
    fund_id: str = "TEST_FUND",
    holdings_source_id: str = "src_h",
    security_price_source_id: str = "src_p",
    policy: AlignmentPolicy | None = None,
) -> PointInTimeAlignmentRequest:
    return PointInTimeAlignmentRequest(
        fund_id=fund_id,
        holdings_source_id=holdings_source_id,
        security_price_source_id=security_price_source_id,
        prediction_timestamp=prediction_timestamp,
        policy=policy or make_fx_alignment_policy(pricing_as_of_date),
    )


def make_fx_historical_request(
    start_date: MarketDate,
    end_date: MarketDate,
    prediction_timestamp: datetime,
    *,
    fund_id: str = "TEST_FUND",
    holdings_source_id: str = "src_h",
    security_price_source_id: str = "src_p",
    fx_source_id: str = "src_fx",
    fund_price_source_id: str = "src_f",
    policy: AlignmentPolicy | None = None,
    fx_policy: FxReturnPolicy | None = None,
) -> HistoricalFxReconciliationRequest:
    return HistoricalFxReconciliationRequest(
        alignment_request=make_fx_alignment_request(
            end_date,
            prediction_timestamp,
            fund_id=fund_id,
            holdings_source_id=holdings_source_id,
            security_price_source_id=security_price_source_id,
            policy=policy,
        ),
        period=ReturnPeriod(start_date, end_date),
        fx_source_id=fx_source_id,
        fx_policy=fx_policy or FxReturnPolicy(FxRateKind("non_cash_buying"), 5),
        fund_price_source_id=fund_price_source_id,
    )


def make_fx_rate_snapshot(
    base_currency: str,
    quote_currency: str,
    market_date: MarketDate,
    rate: float,
    available_at: datetime,
    *,
    kind: str = "non_cash_buying",
    source_id: str = "src_fx",
) -> FxRateSnapshot:
    return FxRateSnapshot(
        observation=FxRateObservation(
            pair=CurrencyPair(CurrencyCode(base_currency), CurrencyCode(quote_currency)),
            market_date=market_date,
            rate=FxRate(rate),
            kind=FxRateKind(kind),
        ),
        available_at=available_at,
        ingested_at=available_at,
        source_id=source_id,
    )
