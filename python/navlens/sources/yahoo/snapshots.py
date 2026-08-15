"""Mapping of Yahoo provider records to canonical security-price snapshots."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from navlens._native import (
    CurrencyCode,
    MarketDate,
    PriceAdjustment,
    SecurityPriceObservation,
    UnitPrice,
)
from navlens.datasets.security_price_snapshots import SecurityPriceSnapshot

from .errors import YahooSecurityPricePayloadError
from .records import YahooChartDocument
from .symbol_mapping import YahooSymbolMapping

YAHOO_SOURCE_ID = "yahoo_finance_experimental"


def materialize_yahoo_security_price_snapshots(
    document: YahooChartDocument,
    mapping: YahooSymbolMapping,
    retrieved_at: datetime,
) -> tuple[SecurityPriceSnapshot, ...]:
    """Map raw closes as unadjusted prices available only at retrieval time."""
    if document.provider_symbol.upper() != mapping.normalized_provider_symbol:
        raise YahooSecurityPricePayloadError("Yahoo response symbol does not match request mapping")
    market_timezone = _load_timezone(document.exchange_timezone_name)
    currency = _map_currency(document.currency)
    return tuple(
        _snapshot(bar.timestamp, bar.close, mapping, currency, market_timezone, retrieved_at)
        for bar in document.closes
    )


def _snapshot(
    timestamp: int,
    close: float,
    mapping: YahooSymbolMapping,
    currency: CurrencyCode,
    market_timezone: ZoneInfo,
    retrieved_at: datetime,
) -> SecurityPriceSnapshot:
    local_date = _market_date(timestamp, market_timezone)
    observation = SecurityPriceObservation(
        mapping.normalized_instrument_id,
        MarketDate(local_date.year, local_date.month, local_date.day),
        UnitPrice(close),
        currency,
        PriceAdjustment("unadjusted"),
    )
    return SecurityPriceSnapshot(
        observation=observation,
        available_at=retrieved_at,
        ingested_at=retrieved_at,
        source_id=YAHOO_SOURCE_ID,
    )


def _market_date(timestamp: int, market_timezone: ZoneInfo) -> date:
    try:
        return datetime.fromtimestamp(timestamp, UTC).astimezone(market_timezone).date()
    except (OSError, OverflowError, ValueError) as error:
        raise YahooSecurityPricePayloadError(
            "Yahoo timestamp is outside the supported range"
        ) from error


def _load_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as error:
        raise YahooSecurityPricePayloadError(f"unknown Yahoo exchange timezone {name!r}") from error


def _map_currency(value: str) -> CurrencyCode:
    try:
        return CurrencyCode(value)
    except ValueError as error:
        raise YahooSecurityPricePayloadError(f"invalid Yahoo currency {value!r}") from error
