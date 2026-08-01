"""Mapping of TCMB provider records to canonical Rust-backed FX rate observations."""

from decimal import Decimal, InvalidOperation

from navlens import (
    CurrencyCode,
    CurrencyPair,
    FxRate,
    FxRateKind,
    FxRateObservation,
    MarketDate,
)

from .errors import TcmbMappingError
from .records import TcmbCurrencyRecord, TcmbDailyRatesDocument

_RATE_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("forex_buying_text", "ForexBuying", "non_cash_buying"),
    ("forex_selling_text", "ForexSelling", "non_cash_selling"),
    ("banknote_buying_text", "BanknoteBuying", "cash_buying"),
    ("banknote_selling_text", "BanknoteSelling", "cash_selling"),
)


def map_tcmb_daily_rates(
    document: TcmbDailyRatesDocument,
) -> tuple[FxRateObservation, ...]:
    """Map a TcmbDailyRatesDocument into a tuple of canonical FxRateObservation objects."""
    if not isinstance(document, TcmbDailyRatesDocument):
        raise TcmbMappingError(
            f"input must be a TcmbDailyRatesDocument instance; got {type(document).__name__}"
        )

    market_date = _parse_date_text(document.date_text)
    try_currency = _create_try_currency()

    observations: list[FxRateObservation] = []
    for record in document.currencies:
        _map_currency_record(record, market_date, try_currency, observations)

    if not observations:
        raise TcmbMappingError("document produced no FX rate observations")

    return tuple(observations)


def _parse_date_text(date_text: str) -> MarketDate:
    if not isinstance(date_text, str) or not date_text.strip():
        raise TcmbMappingError("document date must be a non-empty string")
    date_text = date_text.strip()

    if "." in date_text:
        parts = date_text.split(".")
        if len(parts) == 3:
            try:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                return MarketDate(year, month, day)
            except ValueError as error:
                raise TcmbMappingError(f"invalid market date {date_text!r}: {error}") from error
    elif "/" in date_text:
        parts = date_text.split("/")
        if len(parts) == 3:
            try:
                month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                return MarketDate(year, month, day)
            except ValueError as error:
                raise TcmbMappingError(f"invalid market date {date_text!r}: {error}") from error

    raise TcmbMappingError(f"unsupported or malformed date format {date_text!r}")


def _create_try_currency() -> CurrencyCode:
    try:
        return CurrencyCode("TRY")
    except (TypeError, ValueError) as error:
        raise TcmbMappingError(f"cannot create TRY currency code: {error}") from error


def _map_currency_record(
    record: TcmbCurrencyRecord,
    market_date: MarketDate,
    try_currency: CurrencyCode,
    out_observations: list[FxRateObservation],
) -> None:
    code_text = record.currency_code
    try:
        base_currency = CurrencyCode(code_text)
    except (TypeError, ValueError) as error:
        raise TcmbMappingError(
            f"invalid currency code {code_text!r} for currency {code_text!r}: {error}"
        ) from error

    try:
        pair = CurrencyPair(base_currency, try_currency)
    except (TypeError, ValueError) as error:
        raise TcmbMappingError(
            f"invalid currency pair for currency {code_text!r}: {error}"
        ) from error

    unit_decimal = _parse_positive_decimal(record.unit_text, "Unit", code_text)

    for field_spec in _RATE_FIELDS:
        observation = _map_rate_observation(
            record,
            field_spec,
            pair,
            market_date,
            unit_decimal,
        )
        if observation is not None:
            out_observations.append(observation)


def _map_rate_observation(
    record: TcmbCurrencyRecord,
    field_spec: tuple[str, str, str],
    pair: CurrencyPair,
    market_date: MarketDate,
    unit: Decimal,
) -> FxRateObservation | None:
    field_attr, provider_field, kind_name = field_spec
    rate_text = getattr(record, field_attr)
    if rate_text is None:
        return None

    rate = _parse_positive_decimal(rate_text, provider_field, record.currency_code)
    try:
        normalized_rate = float(rate / unit)
        return FxRateObservation(
            pair,
            market_date,
            FxRate(normalized_rate),
            FxRateKind(kind_name),
        )
    except (ArithmeticError, TypeError, ValueError) as error:
        raise TcmbMappingError(
            f"invalid normalized value for field {provider_field} "
            f"in currency {record.currency_code!r}: {error}"
        ) from error


def _parse_positive_decimal(text: str, field_name: str, code: str) -> Decimal:
    if not isinstance(text, str) or not text.strip():
        raise TcmbMappingError(
            f"field {field_name} must be non-blank numeric text in currency {code!r}"
        )
    try:
        value = Decimal(text)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise TcmbMappingError(
            f"invalid numeric value {text!r} for field {field_name} in currency {code!r}: {error}"
        ) from error
    if not value.is_finite() or value <= 0:
        raise TcmbMappingError(
            f"field {field_name} must be finite and strictly positive, got {text!r} "
            f"in currency {code!r}"
        )
    return value
