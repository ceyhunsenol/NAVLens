import pytest
from navlens import (
    CurrencyCode,
    CurrencyPair,
    FxRate,
    FxRateKind,
    FxRateObservation,
    MarketDate,
)
from navlens.sources.tcmb import (
    TcmbCurrencyRecord,
    TcmbDailyRatesDocument,
    TcmbMappingError,
    map_tcmb_daily_rates,
)


def _make_rec(
    code: str = "USD",
    unit: str = "1",
    fb: str | None = "35.25",
    fs: str | None = "35.30",
    bb: str | None = "35.20",
    bs: str | None = "35.35",
) -> TcmbCurrencyRecord:
    return TcmbCurrencyRecord(
        currency_code=code,
        unit_text=unit,
        forex_buying_text=fb,
        forex_selling_text=fs,
        banknote_buying_text=bb,
        banknote_selling_text=bs,
    )


def test_tarih_dd_mm_yyyy_mapping() -> None:
    doc = TcmbDailyRatesDocument(
        date_text="15.01.2026",
        currencies=(_make_rec(fb="35.25", fs=None, bb=None, bs=None),),
    )

    obs = map_tcmb_daily_rates(doc)

    assert len(obs) == 1
    assert obs[0].market_date == MarketDate(2026, 1, 15)


def test_date_mm_dd_yyyy_fallback_mapping() -> None:
    doc = TcmbDailyRatesDocument(
        date_text="01/15/2026",
        currencies=(_make_rec(fb="35.25", fs=None, bb=None, bs=None),),
    )

    obs = map_tcmb_daily_rates(doc)

    assert len(obs) == 1
    assert obs[0].market_date == MarketDate(2026, 1, 15)


def test_canonical_foreign_try_direction_and_unit_1() -> None:
    doc = TcmbDailyRatesDocument(
        date_text="15.01.2026",
        currencies=(_make_rec(code="USD", unit="1", fb="35.25", fs=None, bb=None, bs=None),),
    )

    obs = map_tcmb_daily_rates(doc)

    assert len(obs) == 1
    o = obs[0]
    assert isinstance(o, FxRateObservation)
    assert o.pair == CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    assert o.rate == FxRate(35.25)
    assert o.kind == FxRateKind("non_cash_buying")


def test_unit_100_normalization() -> None:
    doc = TcmbDailyRatesDocument(
        date_text="15.01.2026",
        currencies=(_make_rec(code="JPY", unit="100", fb="23.50", fs=None, bb=None, bs=None),),
    )

    obs = map_tcmb_daily_rates(doc)

    assert len(obs) == 1
    o = obs[0]
    assert o.pair == CurrencyPair(CurrencyCode("JPY"), CurrencyCode("TRY"))
    assert o.rate == FxRate(0.235)


def test_all_four_field_to_kind_mappings_and_deterministic_order() -> None:
    doc = TcmbDailyRatesDocument(
        date_text="15.01.2026",
        currencies=(
            _make_rec(
                code="USD",
                unit="1",
                fb="35.25",
                fs="35.30",
                bb="35.20",
                bs="35.35",
            ),
        ),
    )

    obs = map_tcmb_daily_rates(doc)

    assert len(obs) == 4
    kinds = [o.kind for o in obs]
    rates = [o.rate for o in obs]

    assert kinds == [
        FxRateKind("non_cash_buying"),
        FxRateKind("non_cash_selling"),
        FxRateKind("cash_buying"),
        FxRateKind("cash_selling"),
    ]
    assert rates == [FxRate(35.25), FxRate(35.30), FxRate(35.20), FxRate(35.35)]


def test_missing_optional_fields_producing_no_observation() -> None:
    doc = TcmbDailyRatesDocument(
        date_text="15.01.2026",
        currencies=(_make_rec(code="XDR", unit="1", fb="47.10", fs=None, bb=None, bs=None),),
    )

    obs = map_tcmb_daily_rates(doc)

    assert len(obs) == 1
    assert obs[0].kind == FxRateKind("non_cash_buying")


def test_multiple_currencies_preserves_order() -> None:
    rec_usd = _make_rec(code="USD", fb="35.25", fs=None, bb=None, bs=None)
    rec_eur = _make_rec(code="EUR", fb="38.10", fs=None, bb=None, bs=None)
    rec_jpy = _make_rec(code="JPY", unit="100", fb="23.50", fs=None, bb=None, bs=None)

    doc = TcmbDailyRatesDocument(
        date_text="15.01.2026",
        currencies=(rec_usd, rec_eur, rec_jpy),
    )

    obs = map_tcmb_daily_rates(doc)

    assert len(obs) == 3
    bases = [o.pair.base_currency for o in obs]
    assert bases == [CurrencyCode("USD"), CurrencyCode("EUR"), CurrencyCode("JPY")]


def test_rejects_non_document_input() -> None:
    with pytest.raises(TcmbMappingError, match="input must be a TcmbDailyRatesDocument"):
        map_tcmb_daily_rates("not a document")  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_date", ["2026-01-15", "31.02.2026", "15/15/2026", "bad_date"])
def test_rejects_malformed_and_impossible_dates(bad_date: str) -> None:
    doc = TcmbDailyRatesDocument(
        date_text=bad_date,
        currencies=(_make_rec(fb="35.25"),),
    )

    with pytest.raises(TcmbMappingError, match="date"):
        map_tcmb_daily_rates(doc)


def test_rejects_invalid_currency_code() -> None:
    doc = TcmbDailyRatesDocument(
        date_text="15.01.2026",
        currencies=(_make_rec(code="usd", fb="35.25"),),
    )

    with pytest.raises(TcmbMappingError, match="usd") as exc_info:
        map_tcmb_daily_rates(doc)

    assert exc_info.value.__cause__ is not None


def test_rejects_try_try_pair() -> None:
    doc = TcmbDailyRatesDocument(
        date_text="15.01.2026",
        currencies=(_make_rec(code="TRY", fb="1.00"),),
    )

    with pytest.raises(TcmbMappingError, match="TRY") as exc_info:
        map_tcmb_daily_rates(doc)

    assert exc_info.value.__cause__ is not None


@pytest.mark.parametrize("bad_unit", ["", "   ", "abc", "0", "-1", "nan", "inf", "-inf"])
def test_rejects_invalid_zero_negative_nan_infinite_unit(bad_unit: str) -> None:
    doc = TcmbDailyRatesDocument(
        date_text="15.01.2026",
        currencies=(_make_rec(code="USD", unit=bad_unit, fb="35.25"),),
    )

    with pytest.raises(TcmbMappingError, match="USD") as exc_info:
        map_tcmb_daily_rates(doc)

    assert "Unit" in str(exc_info.value) or "unit" in str(exc_info.value)


@pytest.mark.parametrize("bad_rate", ["", "   ", "abc", "0", "-35.25", "nan", "inf", "-inf"])
def test_rejects_invalid_zero_negative_nan_infinite_rate(bad_rate: str) -> None:
    doc = TcmbDailyRatesDocument(
        date_text="15.01.2026",
        currencies=(_make_rec(code="USD", unit="1", fb=bad_rate),),
    )

    with pytest.raises(TcmbMappingError, match="USD") as exc_info:
        map_tcmb_daily_rates(doc)

    assert "ForexBuying" in str(exc_info.value)


def test_wraps_normalization_overflow_with_provider_context() -> None:
    doc = TcmbDailyRatesDocument(
        date_text="15.01.2026",
        currencies=(_make_rec(code="USD", unit="1e-999999999", fb="1e999999999"),),
    )

    with pytest.raises(TcmbMappingError, match="ForexBuying") as exc_info:
        map_tcmb_daily_rates(doc)

    assert "USD" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_document_producing_no_observations_raises_error() -> None:
    doc = TcmbDailyRatesDocument(
        date_text="15.01.2026",
        currencies=(_make_rec(code="USD", fb=None, fs=None, bb=None, bs=None),),
    )

    with pytest.raises(TcmbMappingError, match="no FX rate observations"):
        map_tcmb_daily_rates(doc)


def test_proof_no_snapshot_or_availability_invented() -> None:
    doc = TcmbDailyRatesDocument(
        date_text="15.01.2026",
        currencies=(_make_rec(code="USD", fb="35.25", fs=None, bb=None, bs=None),),
    )

    obs = map_tcmb_daily_rates(doc)
    o = obs[0]

    assert isinstance(o, FxRateObservation)
    assert not hasattr(o, "available_at")
    assert not hasattr(o, "ingested_at")
    assert not hasattr(o, "source_id")
