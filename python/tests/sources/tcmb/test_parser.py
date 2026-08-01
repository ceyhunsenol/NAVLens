import pytest
from navlens.sources.tcmb import (
    TcmbCurrencyRecord,
    TcmbDailyRatesDocument,
    TcmbXmlParseError,
    parse_tcmb_daily_rates_xml,
)


def test_one_valid_currency() -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="15.01.2026" Date="01/15/2026">
    <Currency CrossOrder="0" CurrencyCode="USD">
        <Unit>1</Unit>
        <Isim>ABD DOLARI</Isim>
        <ForexBuying>35.2500</ForexBuying>
        <ForexSelling>35.3000</ForexSelling>
        <BanknoteBuying>35.2000</BanknoteBuying>
        <BanknoteSelling>35.3500</BanknoteSelling>
    </Currency>
</Tarih_Date>"""

    doc = parse_tcmb_daily_rates_xml(xml)

    assert isinstance(doc, TcmbDailyRatesDocument)
    assert doc.date_text == "15.01.2026"
    assert len(doc.currencies) == 1

    curr = doc.currencies[0]
    assert isinstance(curr, TcmbCurrencyRecord)
    assert curr.currency_code == "USD"
    assert curr.unit_text == "1"
    assert curr.forex_buying_text == "35.2500"
    assert curr.forex_selling_text == "35.3000"
    assert curr.banknote_buying_text == "35.2000"
    assert curr.banknote_selling_text == "35.3500"


def test_multiple_currencies_preserves_order() -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="15.01.2026">
    <Currency CurrencyCode="USD">
        <Unit>1</Unit>
        <ForexBuying>35.25</ForexBuying>
    </Currency>
    <Currency CurrencyCode="EUR">
        <Unit>1</Unit>
        <ForexBuying>38.10</ForexBuying>
    </Currency>
    <Currency CurrencyCode="JPY">
        <Unit>100</Unit>
        <ForexBuying>23.50</ForexBuying>
    </Currency>
</Tarih_Date>"""

    doc = parse_tcmb_daily_rates_xml(xml)

    codes = [c.currency_code for c in doc.currencies]
    assert codes == ["USD", "EUR", "JPY"]


def test_unit_text_preserved_without_normalization() -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="15.01.2026">
    <Currency CurrencyCode="JPY">
        <Unit>100</Unit>
        <ForexBuying>23.50</ForexBuying>
    </Currency>
</Tarih_Date>"""

    doc = parse_tcmb_daily_rates_xml(xml)

    curr = doc.currencies[0]
    assert curr.unit_text == "100"
    assert isinstance(curr.unit_text, str)


def test_missing_and_blank_optional_rate_fields_become_none() -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="15.01.2026">
    <Currency CurrencyCode="XDR">
        <Unit>1</Unit>
        <ForexBuying>47.10</ForexBuying>
        <ForexSelling>   </ForexSelling>
    </Currency>
</Tarih_Date>"""

    doc = parse_tcmb_daily_rates_xml(xml)

    curr = doc.currencies[0]
    assert curr.forex_buying_text == "47.10"
    assert curr.forex_selling_text is None
    assert curr.banknote_buying_text is None
    assert curr.banknote_selling_text is None


def test_trims_whitespace_and_handles_utf8() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="  15.01.2026  ">
    <Currency CurrencyCode="  USD  ">
        <Unit>  1  </Unit>
        <Isim>TÜRK LİRASI DEĞERİ</Isim>
        <ForexBuying>  35.2500  </ForexBuying>
    </Currency>
</Tarih_Date>""".encode()

    doc = parse_tcmb_daily_rates_xml(xml)

    assert doc.date_text == "15.01.2026"
    curr = doc.currencies[0]
    assert curr.currency_code == "USD"
    assert curr.unit_text == "1"
    assert curr.forex_buying_text == "35.2500"


def test_rejects_invalid_payload_type() -> None:
    with pytest.raises(TcmbXmlParseError, match="invalid payload type"):
        parse_tcmb_daily_rates_xml("not bytes")  # type: ignore[arg-type]


def test_rejects_empty_payload() -> None:
    with pytest.raises(TcmbXmlParseError, match="empty payload"):
        parse_tcmb_daily_rates_xml(b"   ")


def test_rejects_malformed_xml_and_chains_cause() -> None:
    xml = b"<Tarih_Date><Currency></Tarih_Date>"
    with pytest.raises(TcmbXmlParseError, match="malformed XML") as exc_info:
        parse_tcmb_daily_rates_xml(xml)

    assert exc_info.value.__cause__ is not None


def test_rejects_missing_document_date() -> None:
    xml = b"""<Tarih_Date>
    <Currency CurrencyCode="USD"><Unit>1</Unit></Currency>
</Tarih_Date>"""
    with pytest.raises(TcmbXmlParseError, match="missing document date"):
        parse_tcmb_daily_rates_xml(xml)


def test_rejects_missing_currency_code() -> None:
    xml = b"""<Tarih_Date Tarih="15.01.2026">
    <Currency><Unit>1</Unit></Currency>
</Tarih_Date>"""
    with pytest.raises(TcmbXmlParseError, match="missing currency code"):
        parse_tcmb_daily_rates_xml(xml)


def test_rejects_missing_unit() -> None:
    xml = b"""<Tarih_Date Tarih="15.01.2026">
    <Currency CurrencyCode="USD"></Currency>
</Tarih_Date>"""
    with pytest.raises(TcmbXmlParseError, match="missing Unit"):
        parse_tcmb_daily_rates_xml(xml)


def test_rejects_duplicate_currency_code() -> None:
    xml = b"""<Tarih_Date Tarih="15.01.2026">
    <Currency CurrencyCode="USD"><Unit>1</Unit></Currency>
    <Currency CurrencyCode="USD"><Unit>1</Unit></Currency>
</Tarih_Date>"""
    with pytest.raises(TcmbXmlParseError, match="duplicate currency code"):
        parse_tcmb_daily_rates_xml(xml)


def test_rejects_document_with_no_currencies() -> None:
    xml = b"""<Tarih_Date Tarih="15.01.2026">
</Tarih_Date>"""
    with pytest.raises(TcmbXmlParseError, match="no currency records"):
        parse_tcmb_daily_rates_xml(xml)


def test_parser_output_contains_strings_and_none_only() -> None:
    xml = b"""<Tarih_Date Tarih="15.01.2026">
    <Currency CurrencyCode="USD">
        <Unit>100</Unit>
        <ForexBuying>35.25</ForexBuying>
    </Currency>
</Tarih_Date>"""

    doc = parse_tcmb_daily_rates_xml(xml)
    curr = doc.currencies[0]

    assert type(doc.date_text) is str
    assert type(curr.currency_code) is str
    assert type(curr.unit_text) is str
    assert type(curr.forex_buying_text) is str
    assert curr.forex_selling_text is None
    assert curr.banknote_buying_text is None
    assert curr.banknote_selling_text is None

    assert not isinstance(curr.unit_text, (int, float))
    assert not isinstance(curr.forex_buying_text, float)
