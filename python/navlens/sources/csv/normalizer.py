"""Mapping from CSV records to validated Rust price contracts."""

from collections.abc import Sequence

from navlens import MarketDate, PriceObservation, UnitPrice

from .records import CsvPriceRecord


def to_price_observations(records: Sequence[CsvPriceRecord]) -> list[PriceObservation]:
    return [
        PriceObservation(
            MarketDate(record.market_date.year, record.market_date.month, record.market_date.day),
            UnitPrice(record.unit_price),
        )
        for record in records
    ]
