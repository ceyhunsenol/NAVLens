from datetime import date
from pathlib import Path

import pytest
from navlens.sources.yahoo import (
    YahooSecurityPriceCacheError,
    YahooSecurityPriceRequest,
    YahooSymbolMapping,
)
from navlens.sources.yahoo.cache_identity import (
    YAHOO_CACHE_SCHEMA_VERSION,
    YahooCacheIdentity,
    YahooCachePaths,
    build_cache_paths,
)


def test_derives_deterministic_digest_for_equivalent_identities() -> None:
    identity1 = YahooCacheIdentity(
        provider="yahoo_finance_experimental",
        symbol="SYNTH.IS",
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 22),
        schema_version=1,
    )
    identity2 = YahooCacheIdentity(
        provider="yahoo_finance_experimental",
        symbol="SYNTH.IS",
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 22),
        schema_version=1,
    )

    assert identity1.digest() == identity2.digest()
    assert len(identity1.digest()) == 64


def test_builds_cache_paths_without_embedding_raw_provider_symbol(tmp_path: Path) -> None:
    request = YahooSecurityPriceRequest(
        YahooSymbolMapping("SYNTH", "SYNTH.IS"),
        date(2026, 7, 20),
        date(2026, 7, 22),
    )

    paths = build_cache_paths(tmp_path, request)

    assert paths.payload.parent == tmp_path
    assert paths.metadata.parent == tmp_path
    assert paths.payload.name.startswith("chart-2026-07-20-2026-07-22-")
    assert paths.payload.name.endswith(".json")
    assert paths.metadata.name == f"{paths.payload.name[:-5]}.metadata.json"
    # Verify symbol is not in the filename stem directly
    assert "SYNTH.IS" not in paths.payload.name


def test_preserves_request_immutability(tmp_path: Path) -> None:
    mapping = YahooSymbolMapping("SYNTH", "SYNTH.IS")
    start = date(2026, 7, 20)
    end = date(2026, 7, 22)
    request = YahooSecurityPriceRequest(mapping, start, end)

    build_cache_paths(tmp_path, request)

    assert request.mapping == mapping
    assert request.start_date == start
    assert request.end_date == end


@pytest.mark.parametrize(
    ("provider", "symbol", "start", "end", "version"),
    [
        ("", "SYNTH.IS", date(2026, 7, 20), date(2026, 7, 22), 1),
        ("yahoo", "", date(2026, 7, 20), date(2026, 7, 22), 1),
        ("yahoo", "SYNTH.IS", date(2026, 7, 23), date(2026, 7, 22), 1),
        ("yahoo", "SYNTH.IS", "2026-07-20", date(2026, 7, 22), 1),
        ("yahoo", "SYNTH.IS", date(2026, 7, 20), date(2026, 7, 22), 0),
        ("yahoo", "SYNTH.IS", date(2026, 7, 20), date(2026, 7, 22), True),
    ],
)
def test_rejects_invalid_cache_identity_parameters(
    provider: str,
    symbol: str,
    start: object,
    end: object,
    version: object,
) -> None:
    with pytest.raises(YahooSecurityPriceCacheError):
        YahooCacheIdentity(  # type: ignore[arg-type]
            provider=provider,
            symbol=symbol,
            start_date=start,
            end_date=end,
            schema_version=version,
        )


def test_rejects_invalid_path_types() -> None:
    with pytest.raises(YahooSecurityPriceCacheError):
        YahooCachePaths(payload="not_a_path", metadata=Path("meta.json"))  # type: ignore[arg-type]


def test_schema_version_constant() -> None:
    assert YAHOO_CACHE_SCHEMA_VERSION == 1
