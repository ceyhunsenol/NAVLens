"""Fixture builders shared by historical FX reconciliation tests."""

from datetime import datetime

from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    CurrencyPair,
    FxRate,
    FxRateKind,
    FxRateObservation,
    FxReturnPolicy,
    HoldingPosition,
    MarketDate,
    PriceAdjustment,
    PriceCurrencyPolicy,
    PriceObservation,
    ReturnPeriod,
    SecurityPriceObservation,
    UnitPrice,
)
from navlens.alignment import PointInTimeAlignmentRequest
from navlens.datasets import (
    FundUnitPriceSnapshot,
    FxRateSnapshot,
    HoldingSnapshot,
    SecurityPriceSnapshot,
)
from navlens.reconciliation.historical import HistoricalFxReconciliationRequest


def make_fx_alignment_req(date: MarketDate, tz: datetime) -> PointInTimeAlignmentRequest:
    return PointInTimeAlignmentRequest(
        fund_id="TEST_FUND",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        prediction_timestamp=tz,
        policy=AlignmentPolicy(
            CurrencyCode("TRY"),
            PriceAdjustment("unadjusted"),
            date,
            minimum_observations=2,
            max_staleness_calendar_days=5,
        ).with_price_currency_policy(PriceCurrencyPolicy("permit_foreign")),
    )


def make_fx_request(
    date: MarketDate,
    tz: datetime,
    period: ReturnPeriod,
    *,
    fund_price_source_id: str = "src_f",
    fx_source_id: str = "src_fx",
) -> HistoricalFxReconciliationRequest:
    alignment_req = make_fx_alignment_req(date, tz)
    return HistoricalFxReconciliationRequest(
        alignment_request=alignment_req,
        period=period,
        fx_source_id=fx_source_id,
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 5),
        fund_price_source_id=fund_price_source_id,
    )


def make_holding_snap(date: MarketDate, published_at: datetime) -> HoldingSnapshot:
    return HoldingSnapshot(
        fund_id="TEST_FUND",
        effective_date=date,
        published_at=published_at,
        ingested_at=published_at,
        source_id="src_h",
        positions=(HoldingPosition("US_ASSET", AssetClass("equity"), 1.0),),
    )


def make_security_price_snap(
    date: MarketDate, price: float, available_at: datetime
) -> SecurityPriceSnapshot:
    return SecurityPriceSnapshot(
        observation=SecurityPriceObservation(
            "US_ASSET",
            date,
            UnitPrice(price),
            CurrencyCode("USD"),
            PriceAdjustment("unadjusted"),
        ),
        available_at=available_at,
        ingested_at=available_at,
        source_id="src_p",
    )


def make_fx_rate_snap(date: MarketDate, rate: float, available_at: datetime) -> FxRateSnapshot:
    return FxRateSnapshot(
        observation=FxRateObservation(
            pair=CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY")),
            market_date=date,
            rate=FxRate(rate),
            kind=FxRateKind("non_cash_buying"),
        ),
        available_at=available_at,
        ingested_at=available_at,
        source_id="src_fx",
    )


def make_fund_price_snap(
    date: MarketDate, price: float, available_at: datetime
) -> FundUnitPriceSnapshot:
    return FundUnitPriceSnapshot(
        fund_id="TEST_FUND",
        observation=PriceObservation(
            date,
            UnitPrice(price),
        ),
        available_at=available_at,
        ingested_at=available_at,
        source_id="src_f",
    )
