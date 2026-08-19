"""Tests for provider-neutral FX rate source contracts and error hierarchy."""

from datetime import date, datetime

import pytest
from navlens import CurrencyCode, CurrencyPair, FxRateKind
from navlens.datasets import (
    FxRateCorruptedSourceDataError,
    FxRateQuery,
    FxRateQueryError,
    FxRateSourceError,
    FxRateSourceUnavailableError,
    FxRateUnmappedPairError,
    FxRateUnsupportedKindError,
)


def test_valid_fx_rate_query() -> None:
    pair = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")
    query = FxRateQuery(
        pair=pair,
        kind=kind,
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 22),
    )
    assert query.pair == pair
    assert query.kind == kind
    assert query.start_date == date(2026, 7, 20)
    assert query.end_date == date(2026, 7, 22)


def test_query_is_frozen() -> None:
    pair = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")
    query = FxRateQuery(
        pair=pair,
        kind=kind,
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 22),
    )
    with pytest.raises(AttributeError):
        query.start_date = date(2026, 7, 21)  # type: ignore[misc]


@pytest.mark.parametrize("invalid_pair", ["USDTRY", "USD/TRY", ("USD", "TRY"), 123, None, True])
def test_query_rejects_invalid_pair_types(invalid_pair: object) -> None:
    kind = FxRateKind("non_cash_buying")
    with pytest.raises(FxRateQueryError, match="pair must be a CurrencyPair instance"):
        FxRateQuery(
            pair=invalid_pair,  # type: ignore[arg-type]
            kind=kind,
            start_date=date(2026, 7, 20),
            end_date=date(2026, 7, 22),
        )


@pytest.mark.parametrize("invalid_kind", ["NonCashBuying", "buying", 1, None, True])
def test_query_rejects_invalid_kind_types(invalid_kind: object) -> None:
    pair = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    with pytest.raises(FxRateQueryError, match="kind must be an FxRateKind instance"):
        FxRateQuery(
            pair=pair,
            kind=invalid_kind,  # type: ignore[arg-type]
            start_date=date(2026, 7, 20),
            end_date=date(2026, 7, 22),
        )


def test_query_rejects_datetime_instances() -> None:
    pair = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")
    dt = datetime(2026, 7, 20, 12, 0)
    with pytest.raises(FxRateQueryError, match="start_date must be an exact date instance"):
        FxRateQuery(
            pair=pair,
            kind=kind,
            start_date=dt,  # type: ignore[arg-type]
            end_date=date(2026, 7, 22),
        )
    with pytest.raises(FxRateQueryError, match="end_date must be an exact date instance"):
        FxRateQuery(
            pair=pair,
            kind=kind,
            start_date=date(2026, 7, 20),
            end_date=dt,  # type: ignore[arg-type]
        )


def test_query_rejects_bool_and_date_subclasses() -> None:
    pair = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")

    class CustomDate(date):
        pass

    custom_d = CustomDate(2026, 7, 20)
    with pytest.raises(FxRateQueryError, match="start_date must be an exact date instance"):
        FxRateQuery(
            pair=pair,
            kind=kind,
            start_date=custom_d,  # type: ignore[arg-type]
            end_date=date(2026, 7, 22),
        )
    with pytest.raises(FxRateQueryError, match="start_date must be an exact date instance"):
        FxRateQuery(
            pair=pair,
            kind=kind,
            start_date=True,  # type: ignore[arg-type]
            end_date=date(2026, 7, 22),
        )
    with pytest.raises(FxRateQueryError, match="end_date must be an exact date instance"):
        FxRateQuery(
            pair=pair,
            kind=kind,
            start_date=date(2026, 7, 20),
            end_date=False,  # type: ignore[arg-type]
        )


def test_query_rejects_inverted_dates() -> None:
    pair = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))
    kind = FxRateKind("non_cash_buying")
    with pytest.raises(FxRateQueryError, match="on or before"):
        FxRateQuery(
            pair=pair,
            kind=kind,
            start_date=date(2026, 7, 25),
            end_date=date(2026, 7, 20),
        )


def test_error_hierarchy_single_inheritance() -> None:
    assert issubclass(FxRateQueryError, ValueError)
    assert not issubclass(FxRateQueryError, RuntimeError)

    assert issubclass(FxRateSourceError, RuntimeError)
    assert not issubclass(FxRateSourceError, ValueError)

    assert issubclass(FxRateUnmappedPairError, FxRateSourceError)
    assert issubclass(FxRateUnsupportedKindError, FxRateSourceError)
    assert issubclass(FxRateSourceUnavailableError, FxRateSourceError)
    assert issubclass(FxRateCorruptedSourceDataError, FxRateSourceError)

    # Verify distinct single-inheritance subtyping across leaf errors
    assert not issubclass(FxRateUnmappedPairError, KeyError)
    assert not issubclass(FxRateUnsupportedKindError, FxRateUnmappedPairError)
    assert not issubclass(FxRateUnmappedPairError, FxRateUnsupportedKindError)
    assert not issubclass(FxRateSourceUnavailableError, FxRateCorruptedSourceDataError)
    assert not issubclass(FxRateCorruptedSourceDataError, FxRateSourceUnavailableError)
    assert not issubclass(FxRateSourceUnavailableError, FxRateUnsupportedKindError)
    assert not issubclass(FxRateCorruptedSourceDataError, FxRateUnsupportedKindError)
