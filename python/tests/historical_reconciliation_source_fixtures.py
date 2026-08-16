"""Domain fixtures and test fake for historical reconciliation tests."""

from datetime import UTC, datetime

from navlens import (
    AlignmentPolicy,
    AssetClass,
    CurrencyCode,
    HoldingPosition,
    MarketDate,
    PriceAdjustment,
    PriceObservation,
    ReturnPeriod,
    SecurityPriceObservation,
    UnitPrice,
)
from navlens.alignment import PointInTimeAlignmentRequest
from navlens.datasets import (
    FundUnitPriceSnapshot,
    HoldingSnapshot,
    SecurityPriceQuery,
    SecurityPriceSnapshot,
)
from navlens.reconciliation.historical import HistoricalReconciliationRequest


class FakeRecordingSecurityPriceSource:
    """Recording test fake implementing the SecurityPriceSource protocol."""

    def __init__(
        self,
        source_id: str = "src_p",
        data: dict[str, tuple[SecurityPriceSnapshot, ...]] | None = None,
        errors: dict[str, Exception] | None = None,
    ) -> None:
        self._source_id = source_id
        self._data = data or {}
        self._errors = errors or {}
        self.queries: list[SecurityPriceQuery] = []

    @property
    def source_id(self) -> str:
        return self._source_id

    def fetch_security_prices(
        self,
        query: SecurityPriceQuery,
    ) -> tuple[SecurityPriceSnapshot, ...]:
        self.queries.append(query)
        if query.instrument_id in self._errors:
            raise self._errors[query.instrument_id]
        return self._data.get(query.instrument_id, ())


def make_alignment_policy(
    pricing_as_of_date: MarketDate,
    *,
    currency: str = "TRY",
    adjustment: str = "unadjusted",
    minimum_observations: int = 2,
    max_staleness_calendar_days: int = 5,
) -> AlignmentPolicy:
    return AlignmentPolicy(
        CurrencyCode(currency),
        PriceAdjustment(adjustment),
        pricing_as_of_date,
        minimum_observations,
        max_staleness_calendar_days,
    )


def make_alignment_request(
    pricing_as_of_date: MarketDate,
    prediction_timestamp: datetime,
    *,
    fund_id: str = "TEST_FUND",
    holdings_source_id: str = "src_h",
    security_price_source_id: str = "src_p",
) -> PointInTimeAlignmentRequest:
    return PointInTimeAlignmentRequest(
        fund_id=fund_id,
        holdings_source_id=holdings_source_id,
        security_price_source_id=security_price_source_id,
        prediction_timestamp=prediction_timestamp,
        policy=make_alignment_policy(pricing_as_of_date),
    )


def make_historical_request(
    start_date: MarketDate,
    end_date: MarketDate,
    prediction_timestamp: datetime,
    *,
    fund_id: str = "TEST_FUND",
    holdings_source_id: str = "src_h",
    security_price_source_id: str = "src_p",
    fund_price_source_id: str = "src_f",
) -> HistoricalReconciliationRequest:
    return HistoricalReconciliationRequest(
        alignment_request=make_alignment_request(
            end_date,
            prediction_timestamp,
            fund_id=fund_id,
            holdings_source_id=holdings_source_id,
            security_price_source_id=security_price_source_id,
        ),
        period=ReturnPeriod(start_date, end_date),
        fund_price_source_id=fund_price_source_id,
    )


def make_holding_snapshot(
    effective_date: MarketDate,
    published_at: datetime,
    positions: tuple[HoldingPosition, ...],
    *,
    fund_id: str = "TEST_FUND",
    source_id: str = "src_h",
) -> HoldingSnapshot:
    return HoldingSnapshot(
        fund_id=fund_id,
        effective_date=effective_date,
        published_at=published_at,
        ingested_at=published_at,
        source_id=source_id,
        positions=positions,
    )


def make_security_price_snapshot(
    instrument_id: str,
    market_date: MarketDate,
    price: float,
    available_at: datetime,
    *,
    source_id: str = "src_p",
    currency: str = "TRY",
    adjustment: str = "unadjusted",
) -> SecurityPriceSnapshot:
    return SecurityPriceSnapshot(
        observation=SecurityPriceObservation(
            instrument_id,
            market_date,
            UnitPrice(price),
            CurrencyCode(currency),
            PriceAdjustment(adjustment),
        ),
        available_at=available_at,
        ingested_at=available_at,
        source_id=source_id,
    )


def make_fund_unit_price_snapshot(
    market_date: MarketDate,
    price: float,
    available_at: datetime,
    *,
    fund_id: str = "TEST_FUND",
    source_id: str = "src_f",
) -> FundUnitPriceSnapshot:
    return FundUnitPriceSnapshot(
        fund_id=fund_id,
        observation=PriceObservation(
            market_date,
            UnitPrice(price),
        ),
        available_at=available_at,
        ingested_at=available_at,
        source_id=source_id,
    )


def make_equity_position(instrument_id: str, weight: float) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("equity"), weight)


def make_etf_position(instrument_id: str, weight: float) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("exchange_traded_fund"), weight)


def make_cash_position(instrument_id: str, weight: float) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("cash"), weight)


def make_repo_position(instrument_id: str, weight: float) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("repo"), weight)


def make_deposit_position(instrument_id: str, weight: float) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("deposit"), weight)


def make_derivative_position(instrument_id: str, weight: float) -> HoldingPosition:
    return HoldingPosition(instrument_id, AssetClass("derivative"), weight)


def make_utc_timestamp(year: int, month: int, day: int, hour: int = 10) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)
