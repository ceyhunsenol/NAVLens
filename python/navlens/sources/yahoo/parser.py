"""Strict parsing of Yahoo Finance chart response payloads."""

import json
import math
from typing import cast

from .errors import YahooSecurityPricePayloadError
from .records import YahooChartDocument, YahooDailyClose


def parse_yahoo_chart_response(body: bytes) -> YahooChartDocument:
    """Parse one chart response while discarding bars without a close value."""
    payload = _decode_object(body)
    chart = _required_object(payload, "chart")
    if chart.get("error") is not None:
        raise YahooSecurityPricePayloadError("Yahoo chart response contains a provider error")
    result = chart.get("result")
    if not isinstance(result, list) or len(result) != 1 or not isinstance(result[0], dict):
        raise YahooSecurityPricePayloadError("Yahoo chart result must contain exactly one object")
    return _parse_result(cast(dict[str, object], result[0]))


def _decode_object(body: bytes) -> dict[str, object]:
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise YahooSecurityPricePayloadError("Yahoo response is not valid JSON") from error
    if not isinstance(payload, dict):
        raise YahooSecurityPricePayloadError("Yahoo response root must be an object")
    return cast(dict[str, object], payload)


def _parse_result(result: dict[str, object]) -> YahooChartDocument:
    meta = _required_object(result, "meta")
    timestamps = _required_list(result, "timestamp")
    indicators = _required_object(result, "indicators")
    quotes = _required_list(indicators, "quote")
    if len(quotes) != 1 or not isinstance(quotes[0], dict):
        raise YahooSecurityPricePayloadError("Yahoo quote must contain exactly one object")
    closes = _required_list(cast(dict[str, object], quotes[0]), "close")
    return YahooChartDocument(
        provider_symbol=_required_text(meta, "symbol"),
        currency=_required_text(meta, "currency"),
        exchange_timezone_name=_required_text(meta, "exchangeTimezoneName"),
        closes=_parse_closes(timestamps, closes),
    )


def _parse_closes(timestamps: list[object], closes: list[object]) -> tuple[YahooDailyClose, ...]:
    if len(timestamps) != len(closes):
        raise YahooSecurityPricePayloadError("Yahoo timestamp and close lengths differ")
    parsed = []
    for timestamp, close in zip(timestamps, closes, strict=True):
        if close is None:
            continue
        if (
            type(timestamp) is not int
            or isinstance(close, bool)
            or not isinstance(close, int | float)
        ):
            raise YahooSecurityPricePayloadError("Yahoo bar contains an invalid timestamp or close")
        close_value = float(close)
        if not math.isfinite(close_value) or close_value <= 0:
            raise YahooSecurityPricePayloadError("Yahoo close must be a finite positive number")
        parsed.append(YahooDailyClose(timestamp=timestamp, close=close_value))
    return tuple(parsed)


def _required_object(value: dict[str, object], field: str) -> dict[str, object]:
    item = value.get(field)
    if not isinstance(item, dict):
        raise YahooSecurityPricePayloadError(f"Yahoo {field} must be an object")
    return cast(dict[str, object], item)


def _required_list(value: dict[str, object], field: str) -> list[object]:
    item = value.get(field)
    if not isinstance(item, list):
        raise YahooSecurityPricePayloadError(f"Yahoo {field} must be a list")
    return cast(list[object], item)


def _required_text(value: dict[str, object], field: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise YahooSecurityPricePayloadError(f"Yahoo {field} must be a non-empty string")
    return item.strip()
