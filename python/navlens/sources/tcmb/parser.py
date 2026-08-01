"""Parsing of TCMB daily rates XML payloads into raw provider records."""

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

from .errors import TcmbXmlParseError
from .records import TcmbCurrencyRecord, TcmbDailyRatesDocument


def parse_tcmb_daily_rates_xml(payload: bytes) -> TcmbDailyRatesDocument:
    """Parse raw bytes of a TCMB daily rates XML payload into a TcmbDailyRatesDocument."""
    if not isinstance(payload, bytes):
        raise TcmbXmlParseError("invalid payload type: payload must be bytes")

    if not payload or not payload.strip():
        raise TcmbXmlParseError("empty payload: XML payload cannot be empty")

    try:
        root = ET.fromstring(payload)
    except ParseError as error:
        raise TcmbXmlParseError(f"malformed XML: {error}") from error

    date_text = root.get("Tarih") or root.get("Date")
    if not date_text or not date_text.strip():
        raise TcmbXmlParseError(
            "missing document date: root element has no Tarih or Date attribute"
        )

    date_text = date_text.strip()

    records: list[TcmbCurrencyRecord] = []
    seen_codes: set[str] = set()

    for elem in root.findall("Currency"):
        code = elem.get("CurrencyCode") or elem.get("Kod")
        if not code or not code.strip():
            raise TcmbXmlParseError("missing currency code in Currency element")

        code = code.strip()
        if code in seen_codes:
            raise TcmbXmlParseError(f"duplicate currency code: {code!r}")
        seen_codes.add(code)

        unit_elem = elem.find("Unit")
        if unit_elem is None or unit_elem.text is None or not unit_elem.text.strip():
            raise TcmbXmlParseError(f"missing Unit for currency {code!r}")
        unit_text = unit_elem.text.strip()

        forex_buying = _extract_optional_text(elem, "ForexBuying")
        forex_selling = _extract_optional_text(elem, "ForexSelling")
        banknote_buying = _extract_optional_text(elem, "BanknoteBuying")
        banknote_selling = _extract_optional_text(elem, "BanknoteSelling")

        records.append(
            TcmbCurrencyRecord(
                currency_code=code,
                unit_text=unit_text,
                forex_buying_text=forex_buying,
                forex_selling_text=forex_selling,
                banknote_buying_text=banknote_buying,
                banknote_selling_text=banknote_selling,
            )
        )

    if not records:
        raise TcmbXmlParseError("no currency records found in document")

    return TcmbDailyRatesDocument(date_text=date_text, currencies=tuple(records))


def _extract_optional_text(elem: ET.Element, tag: str) -> str | None:
    sub = elem.find(tag)
    if sub is None or sub.text is None or not sub.text.strip():
        return None
    return sub.text.strip()
