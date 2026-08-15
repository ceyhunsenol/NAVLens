from datetime import date, datetime

import pytest
from navlens.sources.yahoo import (
    YahooSecurityPriceRequest,
    YahooSecurityPriceRequestError,
    YahooSymbolMapping,
)


def test_builds_exact_symbol_mapping_and_inclusive_request() -> None:
    mapping = YahooSymbolMapping("SYNTH", "synth.is")
    request = YahooSecurityPriceRequest(mapping, date(2026, 7, 20), date(2026, 7, 21))

    assert mapping.normalized_instrument_id == "SYNTH"
    assert mapping.normalized_provider_symbol == "SYNTH.IS"
    assert request.start_date == date(2026, 7, 20)
    assert request.end_date == date(2026, 7, 21)


@pytest.mark.parametrize("instrument_id", ["", "   ", 3])
def test_rejects_invalid_instrument_identifiers(instrument_id: object) -> None:
    with pytest.raises(YahooSecurityPriceRequestError, match="instrument_id"):
        YahooSymbolMapping(instrument_id, "SYNTH.IS")  # type: ignore[arg-type]


@pytest.mark.parametrize("provider_symbol", ["", "   ", 3])
def test_rejects_invalid_provider_symbols(provider_symbol: object) -> None:
    with pytest.raises(YahooSecurityPriceRequestError, match="provider_symbol"):
        YahooSymbolMapping("SYNTH", provider_symbol)  # type: ignore[arg-type]


def test_rejects_reversed_or_non_date_intervals() -> None:
    mapping = YahooSymbolMapping("SYNTH", "SYNTH.IS")
    with pytest.raises(YahooSecurityPriceRequestError, match="must not be after"):
        YahooSecurityPriceRequest(mapping, date(2026, 7, 22), date(2026, 7, 21))
    with pytest.raises(YahooSecurityPriceRequestError, match="must be dates"):
        YahooSecurityPriceRequest(  # type: ignore[arg-type]
            mapping,
            datetime(2026, 7, 20),
            date(2026, 7, 21),
        )
