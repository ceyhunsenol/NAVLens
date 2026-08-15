"""Integration test verifying substitutability of SecurityPriceSource adapters."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

from navlens import MarketDate
from navlens.datasets import (
    SecurityPriceQuery,
    SecurityPriceSnapshot,
    SecurityPriceSource,
    select_security_price_snapshots,
)
from navlens.sources import CsvSecurityPriceSource
from navlens.sources.yahoo import (
    YahooChartHttpResponse,
    YahooSecurityPriceRequest,
    YahooSecurityPriceSource,
    YahooSecurityPriceSourceAdapter,
    YahooSymbolMapping,
)

SAMPLE_CSV = "\n".join(
    [
        "source_id,instrument_id,market_date,price,currency,adjustment,available_at,ingested_at",
        "test_source,TRY_GARAN,2026-07-20,10.0,TRY,unadjusted,2026-07-20T18:00:00Z,2026-07-20T18:05:00Z",
        "test_source,TRY_GARAN,2026-07-21,10.5,TRY,unadjusted,2026-07-21T18:00:00Z,2026-07-21T18:05:00Z",
        "",
    ]
)


def _sample_yahoo_payload() -> bytes:
    return json.dumps(
        {
            "chart": {
                "error": None,
                "result": [
                    {
                        "meta": {
                            "symbol": "GARAN.IS",
                            "currency": "TRY",
                            "exchangeTimezoneName": "Europe/Istanbul",
                        },
                        "timestamp": [1784514600, 1784601000],  # 2026-07-20 and 2026-07-21
                        "indicators": {"quote": [{"close": [10.0, 10.5]}]},
                    }
                ],
            }
        }
    ).encode("utf-8")


class MockYahooClient:
    def __init__(self, response: YahooChartHttpResponse) -> None:
        self._response = response

    def fetch_chart_response(self, request: YahooSecurityPriceRequest) -> YahooChartHttpResponse:
        return self._response


def _consumer_workflow(
    source: SecurityPriceSource,
    instrument_id: str,
    start_date: date,
    end_date: date,
    at_timestamp: datetime,
    pricing_as_of_date: MarketDate,
) -> tuple[SecurityPriceSnapshot, ...]:
    """Example consumer retrieving candidates and selecting point-in-time observations."""
    query = SecurityPriceQuery(
        instrument_id=instrument_id,
        start_date=start_date,
        end_date=end_date,
    )
    candidates = source.fetch_security_prices(query)
    return select_security_price_snapshots(
        candidates,
        source_id=source.source_id,
        instrument_id=instrument_id,
        at_timestamp=at_timestamp,
        pricing_as_of_date=pricing_as_of_date,
    )


def test_csv_and_yahoo_sources_are_substitutable(tmp_path: Path) -> None:
    # 1. Prepare CSV source
    csv_file = tmp_path / "prices.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    csv_source = CsvSecurityPriceSource(csv_file, source_id="test_source")

    # 2. Prepare Yahoo source adapter
    retrieved_at = datetime(2026, 7, 23, 12, tzinfo=UTC)
    resp = YahooChartHttpResponse(
        body=_sample_yahoo_payload(),
        source_url="https://example.invalid/chart/GARAN.IS",
        retrieved_at=retrieved_at,
    )
    yahoo_source = YahooSecurityPriceSource(client=MockYahooClient(resp))
    yahoo_adapter = YahooSecurityPriceSourceAdapter(
        source=yahoo_source,
        mappings=[YahooSymbolMapping("TRY_GARAN", "GARAN.IS")],
    )

    # 3. Execute consumer workflow through CSV source
    csv_selected = _consumer_workflow(
        source=csv_source,
        instrument_id="TRY_GARAN",
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 21),
        at_timestamp=datetime(2026, 7, 25, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 7, 21),
    )

    # 4. Execute consumer workflow through Yahoo adapter
    yahoo_selected = _consumer_workflow(
        source=yahoo_adapter,
        instrument_id="TRY_GARAN",
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 21),
        at_timestamp=datetime(2026, 7, 25, 0, 0, tzinfo=UTC),
        pricing_as_of_date=MarketDate(2026, 7, 21),
    )

    # Both produced 2 valid point-in-time snapshots with identical observation prices and dates
    assert len(csv_selected) == 2
    assert len(yahoo_selected) == 2
    assert [s.observation.price.value for s in csv_selected] == [10.0, 10.5]
    assert [s.observation.price.value for s in yahoo_selected] == [10.0, 10.5]
    assert [s.observation.market_date for s in csv_selected] == [
        s.observation.market_date for s in yahoo_selected
    ]
