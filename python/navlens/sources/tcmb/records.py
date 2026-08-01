"""Immutable provider records parsed from TCMB daily rates XML payloads."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TcmbCurrencyRecord:
    """Represent raw currency rate fields extracted from a TCMB Currency element."""

    currency_code: str
    unit_text: str
    forex_buying_text: str | None
    forex_selling_text: str | None
    banknote_buying_text: str | None
    banknote_selling_text: str | None


@dataclass(frozen=True, slots=True)
class TcmbDailyRatesDocument:
    """Represent raw document-level date and currency records from a TCMB XML payload."""

    date_text: str
    currencies: tuple[TcmbCurrencyRecord, ...]
